import logging
import uuid
import datetime

from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from ..core.db.service import BaseService
from ..core.dependencies import PaginationParams

from ..utils.processors.filters.decoder import FiltersDecoder
from ..utils.processors.filters.user import UserFilterProcessor

from ..utils.exceptions.http.base import (  # noqa: F401
    ObjectCreateException,
    ObjectUpdateException,
)
from ..utils.exceptions.http.user import (
    UserNotFoundByEmailException,
    UserNotFoundByIdException,
    UserInvalidPasswordException,
    UserInactiveException,
    UserIsNotAdminException,
    TokenNotFoundException,
    InvalidTokenTypeException,
    InvalidTokenException,
    InvalidTokenUserException,
    TokenExpiredException,
    InvalidCredentialsException,
    UserByEmailAlreadyExistsException,
)

from ..utils.token import generate_token

from .models import User, AuthToken
from .schemas import (
    UserCreate,
    AdminUserCreate,
    UserShow,
    UserAuth,
    UserListSchema,
    AuthTokenCreate,
    AuthTokenShow,
    JWTTokensSchema,
    TokenVerifyOrRefreshSchema,
    UserUpdateFromAdmin,
    UserUpdate,
    UserChangeEmail,
    UserPasswordReset,
    UserPasswordResetConfirm,
    UserPasswordChange,
)
from .enums import AuthTokenType
# ЗАКОМЕНТОВАНО: Celery tasks не працюють без worker
# from .tasks import (
#     send_registration_email,
#     send_email_change_confirmation_email,
#     send_password_reset_email,
# )
from .mixins import JWTTokensMixin


log = logging.getLogger(__name__)


class AuthTokenService(BaseService):
    async def get_show_scheme(self, obj: AuthToken) -> UserShow:
        return AuthTokenShow(
            id=obj.id,
            token=obj.token,
            token_type=obj.token_type,
            owner_email=obj.owner_email,
            owner_new_email=obj.owner_new_email,
            expires_at=obj.expires_at,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    async def create_auth_token(self, data: AuthTokenCreate) -> AuthTokenShow:
        try:
            token = generate_token()
            while await self.uow.auth_token.exists_by_token(token):
                token = generate_token()
            data.token = token
            token_id = await self.uow.auth_token.create(obj_in=data)
            token = await self.uow.auth_token.get_by_id(obj_id=token_id)
            return await self.get_show_scheme(token)
        except SQLAlchemyError as e:
            log.exception(e)
            raise ObjectCreateException("Auth token")


class UserService(JWTTokensMixin, BaseService):
    list_schema = UserListSchema
    filter_processor = UserFilterProcessor

    async def get_show_scheme(self, obj: User) -> UserShow:
        return UserShow(
            id=obj.id,
            email=obj.email,
            phone=obj.phone,
            full_name=obj.full_name,
            is_active=obj.is_active,
            is_admin=obj.is_admin,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    async def create_user(
        self,
        data: UserCreate | AdminUserCreate,
        send_confirmation_email: bool = False,
    ) -> UserShow:
        try:
            async with self.uow:
                if await self.uow.user.exists_by_email(data.email):
                    raise UserByEmailAlreadyExistsException(data.email)
                user = await self.uow.user.create(obj_in=data)
                await self.uow.add(user)
                if send_confirmation_email:
                    # Send confirmation email
                    token_data = await AuthTokenService(
                        self.uow
                    ).create_auth_token(
                        AuthTokenCreate(
                            token_type=AuthTokenType.REGISTRATION_CONFIRM,
                            owner_email=user.email,
                        )
                    )
                    # ЗАКОМЕНТОВАНО: Celery task
                    # send_registration_email.delay(token_data.model_dump_json())
                    log.info(f"Registration token created for {user.email}: {token_data.token}")
                await self.uow.commit()
                return await self.get_show_scheme(user)
        except SQLAlchemyError as e:
            log.exception(e)
            raise ObjectCreateException("User")

    async def confirm_registration(self, token: str) -> bool:
        try:
            async with self.uow:
                token_obj = await self.uow.auth_token.get_by_token(token)
                if not token_obj:
                    raise TokenNotFoundException(token)
                if token_obj.expires_at < datetime.datetime.now():
                    raise TokenExpiredException(token)
                if token_obj.token_type != AuthTokenType.REGISTRATION_CONFIRM:
                    raise InvalidTokenTypeException(
                        token, token_obj.token_type.value
                    )
                user = await self.uow.user.get_by_email(token_obj.owner_email)
                if not user:
                    raise UserNotFoundByEmailException(token_obj.owner_email)
                user.is_active = True
                await self.uow.add(user)
                await self.uow.auth_token.delete_by_id(obj_id=token_obj.id)
                await self.uow.commit()
                return True
        except SQLAlchemyError as e:
            log.exception(e)
            return False

    async def authenticate_user(
        self,
        data: UserAuth,
        as_admin: bool = False,
    ) -> JWTTokensSchema:
        try:
            async with self.uow:
                user = await self.uow.user.get_by_email(data.email)
                if not user:
                    raise UserNotFoundByEmailException(data.email)
                if not user.check_password(data.password):
                    raise UserInvalidPasswordException(data.email)
                if not user.is_active:
                    raise UserInactiveException(data.email)
                if as_admin and not user.is_admin:
                    raise UserIsNotAdminException(data.email)
                tokens = await self.generate_tokens_for_user(user.id, as_admin)
                return JWTTokensSchema(**tokens)
        except SQLAlchemyError as e:
            log.exception(e)
            raise UserNotFoundByEmailException(data.email)

    async def _user_id_from_jwt(
        self,
        token: str,
        check_bearer: bool = True,
    ) -> uuid.UUID | None:
        token_data = await self.get_jwt_token_data(token, check_bearer)
        if token_data:
            try:
                return token_data["sub"]
            except KeyError:
                return None

    async def verify_user_token(
        self,
        data: TokenVerifyOrRefreshSchema,
        as_admin: bool = False,
    ) -> bool:
        token_valid = await self.is_token_valid(
            data.token,
            as_admin=as_admin,
        )
        if not token_valid:
            return False
        user_id = await self._user_id_from_jwt(data.token, check_bearer=False)
        if not user_id:
            return False
        try:
            async with self.uow:
                user = await self.uow.user.get_by_id(obj_id=user_id)
                if not user:
                    return False
                if not user.is_active:
                    return False
                if as_admin and not user.is_admin:
                    return False
                return True
        except SQLAlchemyError as e:
            log.exception(e)
            return False

    async def get_user_access_from_refresh(
        self,
        data: TokenVerifyOrRefreshSchema,
        as_admin: bool = False,
    ):
        token_valid = await self.is_token_valid(
            data.token,
            check_refresh=True,
            as_admin=as_admin,
        )
        if not token_valid:
            raise InvalidTokenException(data.token)
        user_id = await self._user_id_from_jwt(data.token, check_bearer=False)
        if not user_id:
            raise InvalidTokenUserException(data.token)
        try:
            async with self.uow:
                user = await self.uow.user.get_by_id(obj_id=user_id)
                if not user:
                    raise UserNotFoundByIdException(user_id)
                if not user.is_active:
                    raise UserInactiveException(user.email)
                if as_admin and not user.is_admin:
                    raise UserIsNotAdminException(user.email)
                access_token = await self.generate_access_token(
                    user.id, as_admin
                )
                return JWTTokensSchema(
                    access_token=access_token,
                    token_type="bearer",
                )
        except SQLAlchemyError as e:
            log.exception(e)
            raise InvalidTokenException(data.token)

    async def update_user_from_admin(
        self,
        data: UserUpdateFromAdmin,
        user_id: uuid.UUID,
    ) -> UserShow:
        try:
            async with self.uow:
                return await self.update_obj(
                    self.uow.user,
                    data,
                    user_id,
                )
        except SQLAlchemyError as e:
            log.exception(e)
            raise ObjectUpdateException("User")

    async def get_user_list(
        self,
        pagination: Optional[PaginationParams] = None,
        filters_decoder: Optional[FiltersDecoder] = None,
    ) -> UserListSchema | list[UserShow]:
        try:
            async with self.uow:
                return await self.get_obj_list(
                    repo=self.uow.user,
                    pagination_params=pagination,
                    filters_decoder=filters_decoder,
                )
        except SQLAlchemyError as e:
            log.exception(e)
            raise ObjectCreateException("User")

    async def get_user_by_id(self, user_id: uuid.UUID) -> UserShow:
        try:
            async with self.uow:
                user = await self.uow.user.get_by_id(obj_id=user_id)
                if not user:
                    raise UserNotFoundByIdException(user_id)
                return await self.get_show_scheme(user)
        except SQLAlchemyError as e:
            log.exception(e)
            raise UserNotFoundByIdException(user_id)

    async def delete_user_by_id(self, user_id: uuid.UUID) -> bool:
        try:
            async with self.uow:
                user = await self.uow.user.get_by_id(obj_id=user_id)
                if not user:
                    return False
                await self.uow.user.delete_by_id(obj_id=user_id)
                await self.uow.commit()
                return True
        except SQLAlchemyError as e:
            log.exception(e)
            return False

    async def update_user(
        self,
        data: UserUpdate,
        authorization: str,
    ) -> UserShow:
        try:
            async with self.uow:
                if authorization:
                    user_id = await self._user_id_from_jwt(authorization)
                    if not user_id:
                        raise InvalidCredentialsException()
                    user = await self.uow.user.get_by_id(obj_id=user_id)
                    if not user:
                        raise UserNotFoundByIdException(user_id)
                    if not user.is_active:
                        raise UserInactiveException(user.email)
                    return await self.update_obj(
                        self.uow.user,
                        data,
                        user.id,
                    )
                else:
                    raise InvalidCredentialsException()
        except SQLAlchemyError as e:
            log.exception(e)
            raise ObjectUpdateException("User")

    async def get_user_profile(self, authorization: str) -> UserShow:
        try:
            async with self.uow:
                if authorization:
                    user_id = await self._user_id_from_jwt(authorization)
                    if not user_id:
                        raise InvalidCredentialsException()
                    user = await self.uow.user.get_by_id(obj_id=user_id)
                    if not user:
                        raise UserNotFoundByIdException(user_id)
                    if not user.is_active:
                        raise UserInactiveException(user.email)
                    return await self.get_show_scheme(user)
                else:
                    raise InvalidCredentialsException()
        except SQLAlchemyError as e:
            log.exception(e)
            raise UserNotFoundByIdException(user_id)

    async def user_change_email(
        self,
        data: UserChangeEmail,
        authorization: str,
    ) -> bool:
        try:
            async with self.uow:
                if authorization:
                    user_id = await self._user_id_from_jwt(authorization)
                    if not user_id:
                        raise InvalidCredentialsException()
                    user = await self.uow.user.get_by_id(obj_id=user_id)
                    if not user:
                        raise UserNotFoundByIdException(user_id)
                    if not user.is_active:
                        raise UserInactiveException(user.email)

                    if await self.uow.user.exists_by_email(data.new_email):
                        raise UserByEmailAlreadyExistsException(data.new_email)

                    # Send confirmation email
                    token_data = await AuthTokenService(
                        self.uow
                    ).create_auth_token(
                        AuthTokenCreate(
                            token_type=AuthTokenType.EMAIL_CHANGE_CONFIRM,
                            owner_email=user.email,
                            owner_new_email=data.new_email,
                        )
                    )
                    await self.uow.commit()
                    # ЗАКОМЕНТОВАНО: Celery task
                    # send_email_change_confirmation_email.delay(
                    #     token_data.model_dump_json()
                    # )
                    log.info(f"Email change token created for {user.email}: {token_data.token}")
                    return True
                else:
                    raise InvalidCredentialsException()
        except SQLAlchemyError as e:
            log.exception(e)
            raise ObjectUpdateException("User")

    async def confirm_email_change(self, token: str) -> bool:
        try:
            async with self.uow:
                token_obj = await self.uow.auth_token.get_by_token(token)
                if not token_obj:
                    raise TokenNotFoundException(token)
                if token_obj.expires_at < datetime.datetime.now():
                    raise TokenExpiredException(token)
                if token_obj.token_type != AuthTokenType.EMAIL_CHANGE_CONFIRM:
                    raise InvalidTokenTypeException(
                        token, token_obj.token_type.value
                    )
                user = await self.uow.user.get_by_email(token_obj.owner_email)
                if not user:
                    raise UserNotFoundByEmailException(token_obj.owner_email)
                user.email = token_obj.owner_new_email
                await self.uow.add(user)
                await self.uow.auth_token.delete_by_id(obj_id=token_obj.id)
                await self.uow.commit()
                return True
        except SQLAlchemyError as e:
            log.exception(e)
            return False

    async def user_password_reset(
        self,
        data: UserPasswordReset,
    ) -> bool:
        try:
            async with self.uow:
                user = await self.uow.user.get_by_email(data.email)
                if not user:
                    raise UserNotFoundByEmailException(data.email)

                # Send confirmation email
                token_data = await AuthTokenService(
                    self.uow
                ).create_auth_token(
                    AuthTokenCreate(
                        token_type=AuthTokenType.PASSWORD_RESET,
                        owner_email=user.email,
                    )
                )
                await self.uow.commit()
                # ЗАКОМЕНТОВАНО: Celery task
                # send_password_reset_email.delay(token_data.model_dump_json())
                log.info(f"Password reset token created for {user.email}: {token_data.token}")
                return True
        except SQLAlchemyError as e:
            log.exception(e)
            return False

    async def confirm_password_reset(
        self,
        token: str,
        data: UserPasswordResetConfirm,
    ) -> bool:
        try:
            async with self.uow:
                token_obj = await self.uow.auth_token.get_by_token(token)
                if not token_obj:
                    raise TokenNotFoundException(token)
                if token_obj.expires_at < datetime.datetime.now():
                    raise TokenExpiredException(token)
                if token_obj.token_type != AuthTokenType.PASSWORD_RESET:
                    raise InvalidTokenTypeException(
                        token, token_obj.token_type.value
                    )
                user = await self.uow.user.get_by_email(token_obj.owner_email)
                if not user:
                    raise UserNotFoundByEmailException(token_obj.owner_email)
                user.password = data.new_password
                await self.uow.add(user)
                await self.uow.auth_token.delete_by_id(obj_id=token_obj.id)
                await self.uow.commit()
                return True
        except SQLAlchemyError as e:
            log.exception(e)
            return False

    async def change_password(
        self,
        data: UserPasswordChange,
        authorization: str,
    ) -> bool:
        try:
            async with self.uow:
                if authorization:
                    user_id = await self._user_id_from_jwt(authorization)
                    if not user_id:
                        raise InvalidCredentialsException()
                    user = await self.uow.user.get_by_id(obj_id=user_id)
                    if not user:
                        raise UserNotFoundByIdException(user_id)
                    if not user.is_active:
                        raise UserInactiveException(user.email)
                    if not user.check_password(data.old_password):
                        raise UserInvalidPasswordException(user.email)
                    user.password = data.new_password
                    await self.uow.add(user)
                    await self.uow.commit()
                    return True
                else:
                    raise InvalidCredentialsException()
        except SQLAlchemyError as e:
            log.exception(e)
            return False