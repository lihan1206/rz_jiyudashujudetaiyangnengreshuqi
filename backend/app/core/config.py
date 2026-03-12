from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "太阳能热水器健康度评估与故障诊断平台"
    app_env: str = "production"
    secret_key: str = "solar-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    mysql_user: str = "root"
    mysql_password: str = "root"
    mysql_host: str = "db"
    mysql_port: int = 3306
    mysql_database: str = "solar_health"

    allowed_origins: str = "*"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@"
            f"{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
