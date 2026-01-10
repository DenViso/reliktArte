import uuid
import datetime

from enum import Enum as PyEnum

from sqlalchemy import String, event, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import UUID, ENUM

from ..core.db.base import Base
from ..core.db.mixins import BaseModelMixin

from ..utils.hashing import Hashing

from .enums import UserRole, AuthTokenType


class User(BaseModelMixin, Base):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"), # ДЛЯ БАЗИ ДАНИХ (PostgreSQL)
        doc="User ID",
    )
    full_name: Mapped[str] = mapped_column(
        nullable=True, index=True, doc="Full name"
    )
    email: Mapped[str] = mapped_column(
        nullable=False, unique=True, index=True, doc="Email"
    )
    phone: Mapped[str] = mapped_column(
        String(length=15), nullable=False, index=True, doc="Phone number"
    )
    password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[PyEnum] = mapped_column(
        ENUM(UserRole, name="user_role"),
        nullable=False,
        index=True,
        default=UserRole.CUSTOMER,
        doc="Role",
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, index=True, default=False, doc="Is active"
    )

    @hybrid_property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    def check_password(self, password: str) -> bool:
        return Hashing.verify_password(password, self.password)

    def __str__(self) -> str:
        return f"User: {self.email}. Role: {self.role}"


class AuthToken(BaseModelMixin, Base):
    __tablename__ = "auth_token"

    token: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
        doc="Token",
    )
    owner_email: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
        doc="Owner email",
    )
    owner_new_email: Mapped[str] = mapped_column(
        nullable=True,
        index=True,
        doc="Owner new email",
    )
    token_type: Mapped[PyEnum] = mapped_column(
        ENUM(AuthTokenType, name="auth_token_type"),
        nullable=False,
        index=True,
        doc="Token type",
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text("NOW() + INTERVAL '1 day'"),
        nullable=False,
        doc="Expires at",
    )

    def __str__(self) -> str:
        return f"Token: {self.token}. Owner: {self.owner_email}"


@event.listens_for(User.password, "set", retval=True)
def hash_user_password_before_insert(target, value, oldvalue, initiator):
    if value != oldvalue:
        return Hashing.get_hashed_password(value)
    return value
