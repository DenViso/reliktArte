from functools import lru_cache

from fastapi_mail import ConnectionConfig

from pydantic import (
    Field,
    field_validator,
    ValidationInfo,
    PostgresDsn,
)
from pydantic_settings import BaseSettings

from .helpers import DotenvListHelper, load_environment


# class CorsSettings(BaseSettings):
#     origins: str = Field(alias="cors_origins", default=["http://localhost:3000","https://relikt-arte.vercel.app","https://*.vercel.app",])

class CorsSettings(BaseSettings):
    origins: str = Field(
        alias="cors_origins", 
        # Додаємо адресу Netlify до списку
        default="https://localhost:3000,http://localhost:5173,https://relikt-arte.vercel.app,https://relikt.vercel.app,https://relikt.netlify.app"
    )

    @field_validator("origins")
    @classmethod
    def assemble_cors_origins(cls, v: str) -> list[str]:
        return DotenvListHelper.get_list_from_value(v)


class DBSettings(BaseSettings):
    name: str = Field(alias="db_name", default="")
    user: str = Field(alias="db_user", default="")
    password: str = Field(alias="db_password", default="")
    host: str = Field(alias="db_host", default="")
    port: int = Field(alias="db_port", default=5432)
    scheme: str = Field(alias="db_scheme", default="postgresql")
    url: str | None = Field(alias="db_url", default=None)

    @field_validator("url")
    @classmethod
    def assemble_db_url(
        cls, v: str | None, validation_info: ValidationInfo
    ) -> str:
        if v is not None:
            return v
        
        # Спробувати отримати DATABASE_URL з environment
        import os
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Railway надає postgres://, а нам потрібно postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            return database_url
        
        # Якщо DATABASE_URL немає, збираємо з окремих частин
        values = validation_info.data
        url = PostgresDsn.build(
            scheme=values.get("scheme", "postgresql"),
            username=values.get("user"),
            password=values.get("password"),
            host=values.get("host"),
            port=values.get("port", 5432),
            path=values.get("name", ""),
        )
        return str(url)


class CelerySettings(BaseSettings):
    timezone: str = Field(alias="celery_timezone", default="UTC")
    broker_url: str | None = Field(alias="celery_broker_url", default=None)
    result_backend: str = Field(
        alias="celery_result_backend",
        default="rpc://",
    )


class CacheSettings(BaseSettings):
    use_redis: bool = Field(alias="cache_use_redis", default=True)
    redis_url: str = Field(alias="cache_redis_url", default="redis://localhost:6379")


class StaticFilesSettings(BaseSettings):
    directory: str = Field(alias="static_dir", default="./static")
    max_file_size: int = Field(alias="static_max_file_size", default=10485760)
    allowed_extensions: str = Field(alias="static_upload_allowed_extensions", default=".jpg,.jpeg,.png,.gif,.webp,.pdf,.docx")

    @field_validator("allowed_extensions")
    @classmethod
    def assemble_allowed_extensions(cls, v: str) -> list[str]:
        return DotenvListHelper.get_list_from_value(v)


class PaginationSettings(BaseSettings):
    limit_per_page: int = Field(
        alias="pagination_limit_per_page",
        default=30,
    )


class SMTPSettings(BaseSettings):
    host: str = Field(alias="smtp_host", default="smtp.gmail.com")
    port: int = Field(alias="smtp_port", default=587)
    username: str = Field(alias="smtp_username", default="")
    password: str = Field(alias="smtp_password", default="")

    @property
    def connection_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            MAIL_USERNAME=self.username,
            MAIL_PASSWORD=self.password,
            MAIL_FROM=self.username,
            MAIL_PORT=self.port,
            MAIL_SERVER=self.host,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )


class JWTSettings(BaseSettings):
    access_token_expire: int = Field(alias="jwt_access_token_expire", default=3600)
    refresh_token_expire: int = Field(alias="jwt_refresh_token_expire", default=604800)
    algorithm: str = Field(alias="jwt_algorithm", default="HS256")


class FrontendSettings(BaseSettings):
    app_scheme: str = Field(alias="frontend_app_scheme", default="https")
    app_domain: str = Field(
        alias="frontend_app_domain",
        default="localhost:3000",
    )
    registration_confirm_path: str = Field(
        alias="frontend_registration_confirm_path",
        default="/confirm",
    )
    password_reset_path: str = Field(
        alias="frontend_password_reset_path",
        default="/reset-password",
    )
    email_change_confirm_path: str = Field(
        alias="frontend_email_change_confirm_path",
        default="/confirm-email",
    )

    @property
    def base_url(self) -> str:
        return f"{self.app_scheme}://{self.app_domain}"


class NovaPostSettings(BaseSettings):
    api_key: str = Field(alias="nova_post_api_key", default="")
    enter_url: str = Field(alias="nova_post_enter_url", default="https://api.novaposhta.ua/v2.0/json/")


class Settings(BaseSettings):
    # App settings
    app_name: str = "Relict Arte API"
    app_version: int = 1
    # app_domain: str = "localhost:8000"
    app_domain: str = "reliktarte-production.up.railway.app"
    app_scheme: str = "https"
    # debug: bool = True
    debug: bool = False # На продакшні краще False
    secret_key: str = Field(default="changeme-please-use-secure-key-in-production")

    # Cors
    cors: CorsSettings = Field(default_factory=CorsSettings)

    # Database settings
    db: DBSettings = Field(default_factory=DBSettings)

    # Celery
    celery: CelerySettings = Field(default_factory=CelerySettings)

    # Cache
    cache: CacheSettings = Field(default_factory=CacheSettings)

    # Static files
    static: StaticFilesSettings = Field(default_factory=StaticFilesSettings)

    # Pagination
    pagination: PaginationSettings = Field(default_factory=PaginationSettings)

    # SMTP
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)

    # JWT
    jwt: JWTSettings = Field(default_factory=JWTSettings)

    # Frontend
    frontend_app: FrontendSettings = Field(default_factory=FrontendSettings)

    # Nova Post
    nova_post: NovaPostSettings = Field(default_factory=NovaPostSettings)

    @property
    def base_url(self) -> str:
        return f"{self.app_scheme}://{self.app_domain}"


@lru_cache
def get_settings() -> Settings:
    load_environment()
    return Settings()


settings = get_settings()