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
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")
    tavily_api_key: str = Field(default="", description="Tavily API Key")
    geo_api_key: str = Field(default="", description="Mapbox Geocoding API Key")
    weather_api_key: str = Field(default="", description="Tomorrow.io Weather API Key")

    # Model settings
    default_model: str = Field(default="gpt-4o-mini", description="Default AI model")
    max_tokens: int = Field(default=1000, description="Max tokens for AI responses")
    temperature: float = Field(default=0.7, description="AI model temperature")

    # Environment
    environment: str = Field(
        default="development", description="Environment (development/production)"
    )
    debug: bool = Field(default=False, description="Debug mode")

    # Frontend specific
    next_public_api_url: str = Field(
        default="http://localhost:8000", description="Public API URL for frontend"
    )
    cors_origins: str = Field(
        default='["http://localhost:3000"]', description="CORS allowed origins"
    )

    # S3-Style Image Upload Service
    s3_api_token: str = Field(default="", description="S3 API Token")
    s3_url: str = Field(default="", description="S3 Service URL")

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
