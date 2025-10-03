from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Any

class Settings(BaseSettings):
    database_url: str
    app_env: str = "dev"
    jwt_secret: str = "change-me"

    # ✅ listă cu default_factory (nu listă literală)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    frontend_base_url: str = "http://localhost:5173"
    rate_limit_window_seconds: int = 60
    rate_limit_max_hits: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    # ✅ acceptă din .env fie JSON, fie listă separată prin virgulă
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                # JSON: ["http://localhost:5173","http://127.0.0.1:5173"]
                import json
                try:
                    return json.loads(s)
                except Exception:
                    pass
            # CSV: http://localhost:5173,http://127.0.0.1:5173
            return [p.strip() for p in s.split(",") if p.strip()]
        return v

settings = Settings()
