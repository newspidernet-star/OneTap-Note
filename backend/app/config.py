from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    storage_dir: Path = Path("storage")
    db_url: str = "sqlite:///storage/smart_scribe.db"
    secret_key_file: Path = Path("storage/secret.key")
    ocr_mode: str = "local"
    public_base_url: str = ""
    # 语音转写需要公网回拉音频：auto = 无 public_base_url 时自动起 cloudflared 临时隧道
    tunnel_mode: str = "auto"
    tunnel_target_port: int = 8000

    class Config:
        env_file = ".env"
        env_prefix = "SMART_SCRIBE_"


def get_settings() -> Settings:
    return Settings()