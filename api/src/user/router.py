import uuid

from fastapi import APIRouter, status

from ..core.db.dependencies import uowDEP
from ..core.dependencies import pagination_params

from ..utils.exceptions.user import UserByEmailAlreadyExistsException
from ..utils.exceptions.http.base import ObjectCreateException
from ..utils.processors.filters.dependencies import filters_decoder

from .service import UserService
from .schemas import (
    UserCreate,
    UserShow,
    UserAuth,
    JWTTokensSchema,
    TokenVerifyOrRefreshSchema,
    UserUpdateFromAdmin,
    UserListSchema,
    UserUpdate,
    UserChangeEmail,
    UserPasswordReset,
    UserPasswordResetConfirm,
    UserPasswordChange,
)
from .dependencies import authorization


router = APIRouter(
    prefix="/user",
    tags=["User"],
)


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserShow,
)
async def create_user(
    uow: uowDEP,
    data: UserCreate,
    send_confirmation_email: bool = False,
) -> UserShow:
    try:
        return await UserService(uow).create_user(
            data, send_confirmation_email
        )
    except UserByEmailAlreadyExistsException as e:
        raise ObjectCreateException(message=e.error)


@router.post(
    "/confirm_registration/{token}/",
    status_code=status.HTTP_200_OK,
    response_model=bool,
)
async def confirm_registration(uow: uowDEP, token: str) -> bool:
    return await UserService(uow).confirm_registration(token)


@router.post(
    "/auth/",
    status_code=status.HTTP_200_OK,
    response_model=JWTTokensSchema,
)
async def auth_user(
    uow: uowDEP,
    data: UserAuth,
    as_admin: bool = False,
) -> JWTTokensSchema:
    return await UserService(uow).authenticate_user(data, as_admin)


@router.post(
    "/token/verify/",
    status_code=status.HTTP_200_OK,
    response_model=bool,
)
async def verify_token(
    uow: uowDEP,
    token_data: TokenVerifyOrRefreshSchema,
    as_admin: bool = False,
) -> bool:
    return await UserService(uow).verify_user_token(token_data, as_admin)


@router.post(
    "/token/access_from_refresh/",
    status_code=status.HTTP_200_OK,
    response_model=JWTTokensSchema,
)
async def access_token_from_refresh(
    uow: uowDEP,
    token_data: TokenVerifyOrRefreshSchema,
    as_admin: bool = False,
) -> JWTTokensSchema:
    return await UserService(uow).get_user_access_from_refresh(
        token_data,
        as_admin,
    )


@router.put(
    "/update_from_admin/{user_id}/",
    status_code=status.HTTP_200_OK,
    response_model=UserShow,
)
async def update_user_from_admin(
    uow: uowDEP,
    user_id: uuid.UUID,
    data: UserUpdateFromAdmin,
) -> UserShow:
    return await UserService(uow).update_user_from_admin(data, user_id)


@router.get(
    "/list/",
    status_code=status.HTTP_200_OK,
)
async def get_user_list(
    pagination: pagination_params,
    filters_decoder: filters_decoder = None,
    uow: uowDEP = uowDEP,
) -> UserListSchema | list[UserShow]:
    return await UserService(uow).get_user_list(
        pagination=pagination,
        filters_decoder=filters_decoder,
    )


@router.get(
    "/get/{user_id}/",
    status_code=status.HTTP_200_OK,
    response_model=UserShow,
)
async def get_user_by_id(
    uow: uowDEP,
    user_id: uuid.UUID,
) -> UserShow:
    return await UserService(uow).get_user_by_id(user_id)


@router.delete(
    "/delete/{user_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    uow: uowDEP,
    user_id: uuid.UUID,
) -> None:
    await UserService(uow).delete_user_by_id(user_id)


@router.get(
    "/profile/",
    status_code=status.HTTP_200_OK,
    response_model=UserShow,
)
async def get_user_profile(
    uow: uowDEP,
    auth_data: authorization,
) -> UserShow:
    return await UserService(uow).get_user_profile(auth_data)


@router.put(
    "/update/",
    status_code=status.HTTP_200_OK,
    response_model=UserShow,
)
async def update_user(
    uow: uowDEP,
    data: UserUpdate,
    auth_data: authorization,
) -> UserShow:
    return await UserService(uow).update_user(data, auth_data)


@router.put(
    "/change_email/",
    status_code=status.HTTP_200_OK,
    response_model=bool,
)
async def change_user_email(
    uow: uowDEP,
    data: UserChangeEmail,
    auth_data: authorization,
) -> bool:
    return await UserService(uow).user_change_email(data, auth_data)


@router.post(
    "/confirm_change_email/",
    status_code=status.HTTP_200_OK,
    response_model=bool,
)
async def confirm_change_email(
    uow: uowDEP,
    token: str,
) -> bool:
    return await UserService(uow).confirm_email_change(token)


@router.post(
    "/password_reset/",
    status_code=status.HTTP_200_OK,
    response_model=bool,
)
async def password_reset(
    uow: uowDEP,
    data: UserPasswordReset,
) -> bool:
    return await UserService(uow).user_password_reset(data)


@router.post(
    "/password_reset_confirm/",
    status_code=status.HTTP_200_OK,
    response_model=bool,
)
async def password_reset_confirm(
    uow: uowDEP,
    token: str,
    data: UserPasswordResetConfirm,
) -> bool:
    return await UserService(uow).confirm_password_reset(token, data)


@router.post(
    "/password_change/",
    status_code=status.HTTP_200_OK,
    response_model=bool,
)
async def password_change(
    uow: uowDEP,
    data: UserPasswordChange,
    auth_data: authorization,
) -> bool:
    return await UserService(uow).change_password(data, auth_data)
