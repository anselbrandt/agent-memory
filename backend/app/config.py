from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic import Field


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    # Database settings
    database_url: str = Field(
        default="postgresql://postgres@localhost:5432/agentmemory",
        description="Database connection URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # Authentication settings
    google_client_id: str = Field(default="", description="Google OAuth Client ID")
    google_client_secret: str = Field(
        default="", description="Google OAuth Client Secret"
    )
    google_oauth_url: str = Field(
        default="https://accounts.google.com/o/oauth2/auth", description="Google OAuth URL"
    )
    google_token_url: str = Field(
        default="https://accounts.google.com/o/oauth2/token", description="Google token URL"
    )
    google_user_url: str = Field(
        default="https://www.googleapis.com/oauth2/v1/userinfo", description="Google user info URL"
    )
    
    # Facebook OAuth settings
    facebook_app_id: str = Field(default="", description="Facebook App ID")
    facebook_app_secret: str = Field(default="", description="Facebook App Secret")
    jwt_secret_key: str = Field(default="", description="JWT Secret Key")
    jwt_algorithm: str = Field(default="HS256", description="JWT Algorithm")
    frontend_url: str = Field(
        default="http://localhost:3000", description="Frontend URL"
    )
    host: str = Field(default="http://localhost:8000", description="Backend host URL")

    # External API keys
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    tavily_api_key: str = Field(default="", description="Tavily API Key")

    # Model settings
    default_model: str = Field(default="gpt-4o-mini", description="Default AI model")

    # Environment
    environment: str = Field(
        default="development", description="Environment (development/production)"
    )
    debug: bool = Field(default=False, description="Debug mode")


    # Session settings
    session_expires_days: int = Field(default=7, description="Session expiration in days")

    # Chat/AI settings
    chat_debounce_delay: float = Field(default=0.01, description="Chat stream debounce delay")

    # Frontend specific
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], description="CORS allowed origins"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        return super().settings_customise_sources(
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )
