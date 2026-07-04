from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    storage_dir: Path = Path("storage")
    db_url: str = "sqlite:///storage/smart_scribe.db"
    secret_key_file: Path = Path("storage/secret.key")
    ocr_mode: str = "cloud"
    public_base_url: str = ""
    # 语音转写需要公网回拉音频：auto = 无 public_base_url 时自动起 cloudflared 临时隧道
    # 对应环境变量 SMART_SCRIBE_TUNNEL
    tunnel: str = "auto"
    tunnel_target_port: int = 8000
    # 用完即焚：生成总结后自动删除该会话的媒体+DB记录（多人共用部署，如 Fly）
    ephemeral: bool = False
    ephemeral_ttl: int = 60
    # 前端构建产物目录（Fly/生产部署用；留空则自动探测 ../frontend/dist）
    frontend_dist_dir: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "SMART_SCRIBE_"


def get_settings() -> Settings:
    return Settings()