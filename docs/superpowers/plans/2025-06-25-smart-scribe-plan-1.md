# Smart Scribe Plan 1: 后端基础 + 媒体处理 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建后端基础设施，实现文件上传/链接下载、ffmpeg 抽帧去重、PaddleOCR 识别，产生可测试的媒体处理 API。

**Architecture:** FastAPI 单体应用，SQLAlchemy + SQLite 存储，服务层封装 ffmpeg/PaddleOCR/yt-dlp，API 层暴露 REST 端点。所有外部 API key 加密存 DB，本地 OCR 为默认模式。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, SQLite, ffmpeg-python, PaddleOCR 3.7+, yt-dlp, Playwright, Pydantic v2, pytest, Docker Compose

## Global Constraints

- Python >= 3.11
- 包管理: requirements.txt (后端)
- 代码无注释（遵循用户偏好）
- 文件存储根目录: `backend/storage/` (Docker volume 挂载)
- 数据库: `backend/storage/smart_scribe.db`
- 项目根目录: `/home/wxc/projects/smart-scribe/`
- 后端代码目录: `/home/wxc/projects/smart-scribe/backend/`
- API key 加密: AES-256-GCM，密钥由部署时生成的随机 secret（存 `backend/storage/secret.key`）
- 配置通过环境变量 + `.env` 文件，用 Pydantic Settings
- 测试: pytest + httpx (AsyncClient)，测试 DB 用内存 SQLite
- 每 task 完成后 commit

---

## File Structure

```
smart-scribe/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, 挂载路由
│   │   ├── config.py                # Pydantic Settings
│   │   ├── database.py              # engine + get_db 依赖
│   │   ├── models/
│   │   │   ├── __init__.py          # re-export 所有模型
│   │   │   ├── base.py              # DeclarativeBase
│   │   │   ├── session.py           # Session, Material, EvidenceBlock, Match
│   │   │   ├── transcript.py        # Transcript, TranscriptSegment
│   │   │   ├── summary.py           # Summary
│   │   │   └── settings.py          # ApiSettings
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── media.py             # 上传/素材请求响应
│   │   │   └── settings.py          # 设置请求响应
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py              # get_db 等共享依赖
│   │   │   ├── media.py             # /api/media/*
│   │   │   └── settings.py          # /api/settings/*
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── crypto.py            # AES 加解密
│   │       ├── storage.py           # 文件存储管理
│   │       ├── downloader.py        # yt-dlp + Playwright
│   │       ├── frame_extractor.py   # ffmpeg 抽帧 + 去重
│   │       ├── ocr.py               # PaddleOCR local/cloud
│   │       └── pipeline.py          # 媒体处理流水线编排
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # fixtures
│   │   ├── test_models.py
│   │   ├── test_crypto.py
│   │   ├── test_settings_api.py
│   │   ├── test_storage.py
│   │   ├── test_upload.py
│   │   ├── test_downloader.py
│   │   ├── test_frame_extractor.py
│   │   ├── test_ocr.py
│   │   └── test_pipeline.py
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
├── docker-compose.yml
└── docs/superpowers/
```

---

### Task 1: 项目脚手架 + Docker + 健康检查

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py` (空)
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/pytest.ini`
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `backend/tests/__init__.py` (空)
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `create_app()` -> FastAPI 实例; `get_settings()` -> Settings; `GET /api/health` -> `{"status": "ok"}`

- [ ] **Step 1: 写 requirements.txt**

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.9
httpx>=0.27.0
ffmpeg-python>=0.2.0
paddleocr>=3.7.0
yt-dlp>=2024.0.0
playwright>=1.40.0
cryptography>=42.0.0
pillow>=10.0.0
numpy>=1.26.0

pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: 写 config.py**

```python
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    storage_dir: Path = Path("storage")
    db_url: str = "sqlite:///storage/smart_scribe.db"
    secret_key_file: Path = Path("storage/secret.key")
    ocr_mode: str = "local"

    class Config:
        env_file = ".env"
        env_prefix = "SMART_SCRIBE_"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: 写 main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Smart Scribe", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: 写 conftest.py**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

- [ ] **Step 5: 写 pytest.ini**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 6: 写 test_health.py**

```python
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 7: 写 Dockerfile**

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 8: 写 docker-compose.yml**

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/storage:/app/storage
    environment:
      - SMART_SCRIBE_OCR_MODE=local
```

- [ ] **Step 9: 安装依赖并跑测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pip install -r requirements.txt && pytest tests/test_health.py -v`
Expected: 1 passed

- [ ] **Step 10: Commit**

```bash
cd /home/wxc/projects/smart-scribe
git init
git add -A
git commit -m "feat: scaffolding with FastAPI, Docker, health check"
```

---

### Task 2: 数据库模型

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/session.py`
- Create: `backend/app/models/transcript.py`
- Create: `backend/app/models/summary.py`
- Create: `backend/app/models/settings.py`
- Create: `backend/tests/test_models.py`
- Modify: `backend/tests/conftest.py` (加 db fixture)

**Interfaces:**
- Consumes: `app.config.Settings`
- Produces: `Base` (DeclarativeBase); `get_db()` 依赖; 所有 ORM 模型类; `init_db()` 建表函数

- [ ] **Step 1: 写 base.py**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 2: 写 database.py**

```python
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.base import Base


def get_engine():
    settings = get_settings()
    return create_engine(settings.db_url, connect_args={"check_same_thread": False})


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    from app.models import __init__  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: 写 models/session.py**

```python
from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="Untitled")
    status: Mapped[str] = mapped_column(String(20), default="created")
    created_at: Mapped[str] = mapped_column(String(30))
    updated_at: Mapped[str] = mapped_column(String(30))

    materials: Mapped[list["Material"]] = relationship(back_populates="session")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    type: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(20))
    file_path: Mapped[str] = mapped_column(String(500))
    original_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    session: Mapped["Session"] = relationship(back_populates="materials")
    evidence_blocks: Mapped[list["EvidenceBlock"]] = relationship(back_populates="material")


class EvidenceBlock(Base):
    __tablename__ = "evidence_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_id: Mapped[str] = mapped_column(String(10), unique=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    type: Mapped[str] = mapped_column(String(10))
    timestamp: Mapped[float] = mapped_column(Float, default=0.0)
    end_timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(50), nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    material: Mapped["Material"] = relationship(back_populates="evidence_blocks")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    speech_block_id: Mapped[int] = mapped_column(ForeignKey("evidence_blocks.id"))
    screen_block_id: Mapped[int] = mapped_column(ForeignKey("evidence_blocks.id"))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    time_sim: Mapped[float] = mapped_column(Float, default=0.0)
    keyword_sim: Mapped[float] = mapped_column(Float, default=0.0)
    semantic_sim: Mapped[float] = mapped_column(Float, default=0.0)
```

- [ ] **Step 4: 写 models/transcript.py**

```python
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), unique=True)
    segments: Mapped[list["TranscriptSegment"]] = relationship(back_populates="transcript", cascade="all, delete-orphan")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"))
    start_time: Mapped[float] = mapped_column(Float, default=0.0)
    end_time: Mapped[float] = mapped_column(Float, default=0.0)
    speaker: Mapped[str] = mapped_column(String(50), default="")
    text: Mapped[str] = mapped_column(Text, default="")

    transcript: Mapped["Transcript"] = relationship(back_populates="segments")
```

- [ ] **Step 5: 写 models/summary.py**

```python
from sqlalchemy import JSON, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), unique=True)
    corrected_text: Mapped[str] = mapped_column(Text, default="")
    summary_markdown: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[dict] = mapped_column(JSON, default=list)
    citations: Mapped[dict] = mapped_column(JSON, default=list)
    unused_block_ids: Mapped[dict] = mapped_column(JSON, default=list)
```

- [ ] **Step 6: 写 models/settings.py**

```python
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiSettings(Base):
    __tablename__ = "api_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    encrypted_value: Mapped[str] = mapped_column(Text, default="")
    is_required: Mapped[bool] = mapped_column(default=True)
```

- [ ] **Step 7: 写 models/__init__.py**

```python
from app.models.base import Base
from app.models.session import EvidenceBlock, Match, Material, Session
from app.models.settings import ApiSettings
from app.models.summary import Summary
from app.models.transcript import Transcript, TranscriptSegment

__all__ = [
    "Base",
    "Session",
    "Material",
    "EvidenceBlock",
    "Match",
    "Transcript",
    "TranscriptSegment",
    "Summary",
    "ApiSettings",
]
```

- [ ] **Step 8: 更新 conftest.py 加 db fixture**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import base
from app.models import __init__ as _models  # noqa: F401
from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
```

- [ ] **Step 9: 写 test_models.py**

```python
from datetime import datetime

from app.models import EvidenceBlock, Material, Session


def test_create_session(db_session):
    s = Session(title="Test", status="created", created_at="2025-01-01", updated_at="2025-01-01")
    db_session.add(s)
    db_session.commit()

    assert s.id is not None
    assert s.title == "Test"


def test_session_material_relationship(db_session):
    s = Session(title="Test", status="created", created_at="2025-01-01", updated_at="2025-01-01")
    db_session.add(s)
    db_session.commit()

    m = Material(session_id=s.id, type="video", source="local_file", file_path="/tmp/x.mp4", sort_order=0)
    db_session.add(m)
    db_session.commit()

    eb = EvidenceBlock(
        block_id="P001",
        session_id=s.id,
        material_id=m.id,
        type="screen",
        timestamp=12.5,
        text="测试OCR文本",
        page_number=1,
        image_path="/tmp/frame_001.jpg",
    )
    db_session.add(eb)
    db_session.commit()

    assert db_session.query(Session).count() == 1
    assert db_session.query(Material).count() == 1
    assert db_session.query(EvidenceBlock).count() == 1
    assert db_session.query(EvidenceBlock).first().block_id == "P001"
```

- [ ] **Step 10: 跑测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_models.py -v`
Expected: 2 passed

- [ ] **Step 11: Commit**

```bash
cd /home/wxc/projects/smart-scribe
git add -A
git commit -m "feat: SQLAlchemy models for session, material, evidence, transcript, summary, settings"
```

---

### Task 3: 加密服务 + 设置 API

**Files:**
- Create: `backend/app/services/__init__.py` (空)
- Create: `backend/app/services/crypto.py`
- Create: `backend/app/schemas/__init__.py` (空)
- Create: `backend/app/schemas/settings.py`
- Create: `backend/app/api/__init__.py` (空)
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/settings.py`
- Create: `backend/tests/test_crypto.py`
- Create: `backend/tests/test_settings_api.py`
- Modify: `backend/app/main.py` (挂载 settings 路由)
- Modify: `backend/app/database.py` (app 启动时 init_db)

**Interfaces:**
- Produces: `encrypt(plaintext: str) -> str`; `decrypt(ciphertext: str) -> str`; `ensure_secret_key() -> bytes`; `GET/POST /api/settings`; `POST /api/settings/{key}/test`

- [ ] **Step 1: 写 crypto.py**

```python
import os
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


def ensure_secret_key() -> bytes:
    settings = get_settings()
    key_file = settings.secret_key_file
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if not key_file.exists():
        key = AESGCM.generate_key(bit_length=256)
        key_file.write_bytes(key)
        return key
    return key_file.read_bytes()


def encrypt(plaintext: str) -> str:
    key = ensure_secret_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt(ciphertext: str) -> str:
    key = ensure_secret_key()
    raw = base64.b64decode(ciphertext)
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()
```

- [ ] **Step 2: 写 test_crypto.py**

```python
from app.services.crypto import decrypt, encrypt


def test_encrypt_decrypt_roundtrip():
    plaintext = "sk-volcano-abc123secret"
    ct = encrypt(plaintext)
    assert ct != plaintext
    assert decrypt(ct) == plaintext


def test_encrypt_produces_different_ciphertext():
    pt = "same-secret"
    assert encrypt(pt) != encrypt(pt)
```

- [ ] **Step 3: 跑 crypto 测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_crypto.py -v`
Expected: 2 passed

- [ ] **Step 4: 写 schemas/settings.py**

```python
from pydantic import BaseModel


class SettingItem(BaseModel):
    key: str
    value: str
    is_required: bool = True


class SettingOut(BaseModel):
    key: str
    is_set: bool
    is_required: bool


class SettingsUpdate(BaseModel):
    settings: list[SettingItem]


class TestResult(BaseModel):
    key: str
    ok: bool
    message: str = ""
```

- [ ] **Step 5: 写 api/deps.py**

```python
from app.database import get_db
```

- [ ] **Step 6: 写 api/settings.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import ApiSettings
from app.schemas.settings import SettingItem, SettingsUpdate, TestResult
from app.services.crypto import decrypt, encrypt

router = APIRouter(prefix="/api/settings", tags=["settings"])

REQUIRED_KEYS = [
    ("volcano_app_id", True),
    ("volcano_access_token", True),
    ("deepseek_api_key", True),
    ("paddleocr_cloud_key", False),
    ("ytdlp_cookie_path", False),
]


@router.get("")
async def list_settings(db: Session = Depends(get_db)):
    result = []
    for key, required in REQUIRED_KEYS:
        existing = db.query(ApiSettings).filter_by(key=key).first()
        result.append({"key": key, "is_set": existing is not None, "is_required": required})
    return result


@router.post("")
async def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    for item in body.settings:
        existing = db.query(ApiSettings).filter_by(key=item.key).first()
        enc = encrypt(item.value)
        if existing:
            existing.encrypted_value = enc
            existing.is_required = item.is_required
        else:
            db.add(ApiSettings(key=item.key, encrypted_value=enc, is_required=item.is_required))
    db.commit()
    return {"status": "ok"}


@router.post("/{key}/test")
async def test_setting(key: str, db: Session = Depends(get_db)):
    existing = db.query(ApiSettings).filter_by(key=key).first()
    if not existing or not existing.encrypted_value:
        return TestResult(key=key, ok=False, message="未配置")
    plaintext = decrypt(existing.encrypted_value)
    if not plaintext:
        return TestResult(key=key, ok=False, message="值为空")
    return TestResult(key=key, ok=True, message="格式有效")
```

- [ ] **Step 7: 修改 main.py 挂载路由 + init_db**

把 main.py 的 `create_app` 中 health 检查之后追加：

```python
from app.database import init_db
from app.api.settings import router as settings_router


def create_app() -> FastAPI:
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)

    init_db()

    app = FastAPI(title="Smart Scribe", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    app.include_router(settings_router)

    return app
```

- [ ] **Step 8: 写 test_settings_api.py**

```python
from app.models import ApiSettings


async def test_list_settings_empty(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    assert data[0]["is_set"] is False
    assert data[0]["is_required"] is True


async def test_update_and_list_settings(client):
    await client.post("/api/settings", json={
        "settings": [{"key": "deepseek_api_key", "value": "sk-test123", "is_required": True}]
    })
    resp = await client.get("/api/settings")
    deepseek = [s for s in resp.json() if s["key"] == "deepseek_api_key"][0]
    assert deepseek["is_set"] is True


async def test_test_setting(client):
    await client.post("/api/settings", json={
        "settings": [{"key": "deepseek_api_key", "value": "sk-test123", "is_required": True}]
    })
    resp = await client.post("/api/settings/deepseek_api_key/test")
    assert resp.json()["ok"] is True


async def test_test_setting_not_configured(client):
    resp = await client.post("/api/settings/volcano_app_id/test")
    assert resp.json()["ok"] is False
```

- [ ] **Step 9: 跑测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_settings_api.py tests/test_crypto.py -v`
Expected: 5 passed

- [ ] **Step 10: Commit**

```bash
cd /home/wxc/projects/smart-scribe
git add -A
git commit -m "feat: AES-256 encrypted settings storage + settings API"
```

---

### Task 4: 文件存储 + 上传 API + 会话创建

**Files:**
- Create: `backend/app/services/storage.py`
- Create: `backend/app/schemas/media.py`
- Create: `backend/app/api/media.py`
- Create: `backend/tests/test_storage.py`
- Create: `backend/tests/test_upload.py`
- Modify: `backend/app/main.py` (挂载 media 路由)

**Interfaces:**
- Produces: `save_upload(file: UploadFile, session_id: int) -> str`; `classify_media(filename: str, content_type: str) -> str` (返回 video/audio/image/unknown); `POST /api/sessions`；`POST /api/media/upload`; `GET /api/media/session/{id}/materials`

- [ ] **Step 1: 写 storage.py**

```python
import shutil
from pathlib import Path
from fastapi import UploadFile

from app.config import get_settings

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def classify_media(filename: str, content_type: str = "") -> str:
    ext = Path(filename).suffix.lower()
    if ext in VIDEO_EXTS or content_type.startswith("video/"):
        return "video"
    if ext in AUDIO_EXTS or content_type.startswith("audio/"):
        return "audio"
    if ext in IMAGE_EXTS or content_type.startswith("image/"):
        return "image"
    return "unknown"


def session_storage_dir(session_id: int) -> Path:
    settings = get_settings()
    d = settings.storage_dir / f"session_{session_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_upload(file: UploadFile, session_id: int) -> str:
    d = session_storage_dir(session_id)
    dest = d / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(dest)
```

- [ ] **Step 2: 写 test_storage.py**

```python
from io import BytesIO
from fastapi import UploadFile

from app.services.storage import classify_media, save_upload


def test_classify_video():
    assert classify_media("lecture.mp4") == "video"
    assert classify_media("x.mkv") == "video"
    assert classify_media("x.txt", "video/mp4") == "video"


def test_classify_audio():
    assert classify_media("voice.m4a") == "audio"
    assert classify_media("note.mp3") == "audio"


def test_classify_image():
    assert classify_media("slide.png") == "image"
    assert classify_media("pic.jpeg") == "image"


def test_classify_unknown():
    assert classify_media("data.csv") == "unknown"


def test_save_upload(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage.get_settings", lambda: type("S", (), {"storage_dir": tmp_path})())
    content = b"fake video data"
    file = UploadFile(filename="test.mp4", file=BytesIO(content))
    path = save_upload(file, 1)
    assert "test.mp4" in path
    with open(path, "rb") as f:
        assert f.read() == content
```

- [ ] **Step 3: 跑 storage 测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_storage.py -v`
Expected: 5 passed

- [ ] **Step 4: 写 schemas/media.py**

```python
from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: str = "Untitled"


class SessionOut(BaseModel):
    id: int
    title: str
    status: str


class MaterialOut(BaseModel):
    id: int
    type: str
    source: str
    file_path: str
    sort_order: int
    status: str

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    material_id: int
    type: str
    status: str
```

- [ ] **Step 5: 写 api/media.py**

```python
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Material, Session
from app.schemas.media import MaterialOut, SessionCreate, SessionOut, UploadResponse
from app.services.storage import classify_media, save_upload

router = APIRouter(tags=["media"])


@router.post("/api/sessions", response_model=SessionOut)
async def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    s = Session(title=body.title, status="created", created_at=now, updated_at=now)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.post("/api/media/upload", response_model=UploadResponse)
async def upload_file(
    session_id: int = Form(...),
    sort_order: int = Form(0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    media_type = classify_media(file.filename, file.content_type)
    file_path = save_upload(file, session_id)
    m = Material(
        session_id=session_id,
        type=media_type,
        source="local_file",
        file_path=file_path,
        sort_order=sort_order,
        status="pending",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return UploadResponse(material_id=m.id, type=media_type, status="pending")


@router.get("/api/media/session/{session_id}/materials", response_model=list[MaterialOut])
async def list_materials(session_id: int, db: Session = Depends(get_db)):
    return db.query(Material).filter_by(session_id=session_id).order_by(Material.sort_order).all()
```

- [ ] **Step 6: 修改 main.py 挂载 media 路由**

在 settings_router 之后追加：

```python
from app.api.media import router as media_router
```
以及 `app.include_router(media_router)`

- [ ] **Step 7: 写 test_upload.py**

```python
from io import BytesIO


async def test_create_session(client):
    resp = await client.post("/api/sessions", json={"title": "物理课"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "物理课"
    assert resp.json()["status"] == "created"


async def test_upload_and_list(client):
    s = await client.post("/api/sessions", json={"title": "T"})
    sid = s.json()["id"]

    resp = await client.post(
        "/api/media/upload",
        data={"session_id": sid, "sort_order": 0},
        files={"file": ("lec.mp4", BytesIO(b"fake"), "video/mp4")},
    )
    assert resp.status_code == 200
    assert resp.json()["type"] == "video"

    resp = await client.post(
        "/api/media/upload",
        data={"session_id": sid, "sort_order": 1},
        files={"file": ("slide.png", BytesIO(b"fake"), "image/png")},
    )
    assert resp.json()["type"] == "image"

    materials = await client.get(f"/api/media/session/{sid}/materials")
    assert len(materials.json()) == 2
    assert materials.json()[0]["sort_order"] == 0
    assert materials.json()[1]["sort_order"] == 1
```

- [ ] **Step 8: 跑测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_upload.py -v`
Expected: 2 passed

- [ ] **Step 9: Commit**

```bash
cd /home/wxc/projects/smart-scribe
git add -A
git commit -m "feat: file storage, session creation, upload API with auto media classification"
```

---

### Task 5: 下载模块 (yt-dlp + Playwright)

**Files:**
- Create: `backend/app/services/downloader.py`
- Create: `backend/tests/test_downloader.py`

**Interfaces:**
- Consumes: `app.services.storage.session_storage_dir`
- Produces: `detect_platform(url: str) -> str` (返回 youtube/bilibili/douyin_video/douyin_image/direct/unknown)；`download_video(url: str, session_id: int) -> str` (本地路径)；`download_images(url: str, session_id: int) -> list[str]`；`download(url: str, session_id: int) -> list[MaterialSpec]`，其中 `MaterialSpec = tuple[str, str, str]` (file_path, media_type, original_url)

- [ ] **Step 1: 写 downloader.py**

```python
from pathlib import Path
from urllib.parse import urlparse

from app.services.storage import session_storage_dir


class MaterialSpec:
    def __init__(self, file_path: str, media_type: str, original_url: str):
        self.file_path = file_path
        self.media_type = media_type
        self.original_url = original_url


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "bilibili.com" in host or "b23.tv" in host:
        return "bilibili"
    if "douyin.com" in host or "iesdouyin.com" in host:
        return "douyin_video"
    if "iesdouyin.com/share/article" in url or "/note/" in url:
        return "douyin_image"
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in {".mp4", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".jpg", ".jpeg", ".png"}:
        return "direct"
    return "unknown"


def download_video(url: str, session_id: int) -> str:
    import yt_dlp

    d = session_storage_dir(session_id)
    outtmpl = str(d / "%(title)s.%(ext)s")
    ydl_opts = {"outtmpl": outtmpl, "format": "best"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def download_images(url: str, session_id: int) -> list[str]:
    from playwright.sync_api import sync_playwright

    d = session_storage_dir(session_id)
    paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        images = page.query_selector_all("img")
        for i, img in enumerate(images):
            src = img.get_attribute("src")
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            if not src.startswith("http"):
                continue
            ext = Path(urlparse(src).path).suffix or ".jpg"
            dest = d / f"image_{i:03d}{ext}"
            try:
                resp = page.request.get(src)
                dest.write_bytes(resp.body())
                paths.append(str(dest))
            except Exception:
                continue
        browser.close()
    return paths


def download(url: str, session_id: int) -> list[MaterialSpec]:
    platform = detect_platform(url)
    if platform in ("youtube", "bilibili", "douyin_video"):
        path = download_video(url, session_id)
        media_type = "video"
        if Path(path).suffix.lower() in {".mp3", ".m4a", ".wav"}:
            media_type = "audio"
        return [MaterialSpec(path, media_type, url)]
    if platform in ("douyin_image", "direct") and any(
        ext in url for ext in (".jpg", ".png", ".jpeg", ".webp")
    ):
        paths = download_images(url, session_id)
        return [MaterialSpec(p, "image", url) for p in paths]
    if platform == "douyin_image":
        paths = download_images(url, session_id)
        return [MaterialSpec(p, "image", url) for p in paths]
    if platform == "direct":
        import shutil
        import urllib.request
        d = session_storage_dir(session_id)
        filename = Path(urlparse(url).path).name or "download.bin"
        dest = d / filename
        with urllib.request.urlopen(url) as resp:
            dest.write_bytes(resp.read())
        media_type = "video" if dest.suffix in {".mp4", ".mkv", ".webm"} else "audio" if dest.suffix in {".mp3", ".wav", ".m4a"} else "image"
        return [MaterialSpec(str(dest), media_type, url)]
    raise ValueError(f"不支持的平台: {url}")
```

- [ ] **Step 2: 写 test_downloader.py**

```python
from app.services.downloader import detect_platform


def test_detect_youtube():
    assert detect_platform("https://www.youtube.com/watch?v=abc") == "youtube"
    assert detect_platform("https://youtu.be/abc") == "youtube"


def test_detect_bilibili():
    assert detect_platform("https://www.bilibili.com/video/BV1xx") == "bilibili"
    assert detect_platform("https://b23.tv/abc") == "bilibili"


def test_detect_douyin():
    assert detect_platform("https://www.douyin.com/video/123") == "douyin_video"


def test_detect_direct():
    assert detect_platform("https://example.com/file.mp4") == "direct"
    assert detect_platform("https://example.com/file.mp3") == "direct"


def test_detect_unknown():
    assert detect_platform("https://example.com/page") == "unknown"
```

- [ ] **Step 3: 跑测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_downloader.py -v`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
cd /home/wxc/projects/smart-scribe
git add -A
git commit -m "feat: download module with yt-dlp + Playwright, platform detection"
```

---

### Task 6: ffmpeg 抽帧 + 去重

**Files:**
- Create: `backend/app/services/frame_extractor.py`
- Create: `backend/tests/test_frame_extractor.py`

**Interfaces:**
- Consumes: 视频文件路径
- Produces: `extract_frames(video_path: str, output_dir: str, interval: float = 3.0) -> list[str]`；`dedup_frames(frame_paths: list[str], threshold: float = 0.95) -> list[str]`；`extract_and_dedup(video_path: str, output_dir: str, interval: float = 3.0) -> list[str]`

- [ ] **Step 1: 写 frame_extractor.py**

```python
from pathlib import Path

import ffmpeg
import numpy as np
from PIL import Image


def extract_frames(video_path: str, output_dir: str, interval: float = 3.0) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    probe = ffmpeg.probe(video_path)
    duration = float(probe["format"]["duration"])
    frame_times = np.arange(0, duration, interval)
    paths = []
    for i, t in enumerate(frame_times):
        dest = str(out / f"frame_{i:04d}.jpg")
        try:
            (
                ffmpeg.input(video_path, ss=float(t))
                .output(dest, vframes=1, format="image2", vcodec="mjpeg", qscale=2)
                .overwrite_output()
                .run(quiet=True)
            )
            paths.append(dest)
        except ffmpeg.Error:
            continue
    return paths


def _load_gray(path: str) -> np.ndarray:
    img = Image.open(path).convert("L").resize((256, 256))
    return np.asarray(img, dtype=np.float32) / 255.0


def _similarity(a: str, b: str) -> float:
    ga, gb = _load_gray(a), _load_gray(b)
    diff = np.abs(ga - gb).mean()
    return 1.0 - float(diff)


def dedup_frames(frame_paths: list[str], threshold: float = 0.95) -> list[str]:
    if not frame_paths:
        return []
    kept = [frame_paths[0]]
    for p in frame_paths[1:]:
        if _similarity(kept[-1], p) < threshold:
            kept.append(p)
    return kept


def extract_and_dedup(video_path: str, output_dir: str, interval: float = 3.0) -> list[str]:
    frames = extract_frames(video_path, output_dir, interval)
    return dedup_frames(frames)
```

- [ ] **Step 2: 写 test_frame_extractor.py**

```python
from pathlib import Path

import ffmpeg
import numpy as np
from PIL import Image

from app.services.frame_extractor import dedup_frames, extract_frames


def _make_test_video(path: str, duration: float = 6.0, fps: int = 10):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    for i in range(int(duration * fps)):
        if i < fps * 3:
            img = np.full((64, 64, 3), 50 + i, dtype=np.uint8)
        else:
            img = np.full((64, 64, 3), 200, dtype=np.uint8)
        frames.append(img)
    (
        ffmpeg.input("pipe:", format="rawvideo", pix_fmt="rgb24", s="64x64", r=fps)
        .output(str(out), vcodec="libx264", pix_fmt="yuv420p", t=duration)
        .overwrite_output()
        .run(input=b"".join(f.tobytes() for f in frames), quiet=True)
    )


def test_extract_frames(tmp_path):
    video = str(tmp_path / "test.mp4")
    _make_test_video(video, duration=6.0, fps=10)
    frames = extract_frames(video, str(tmp_path / "frames"), interval=2.0)
    assert len(frames) >= 2
    for p in frames:
        assert Path(p).exists()
```

实际上构建测试视频依赖 ffmpeg 的 rawvideo pipe 输入可能不稳定。用 ffmpeg 的 color source filter 更可靠：

替换 test_frame_extractor.py 内容为：

```python
from pathlib import Path

import ffmpeg

from app.services.frame_extractor import dedup_frames, extract_frames


def _make_test_video(path: str, duration: float = 9.0):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    (
        ffmpeg.input(f"color=c=red:s=64x64:d={duration}", f="lavfi")
        .output(str(out), vcodec="libx264", pix_fmt="yuv420p", r=10)
        .overwrite_output()
        .run(quiet=True)
    )


def test_extract_frames(tmp_path):
    video = str(tmp_path / "test.mp4")
    _make_test_video(video, duration=9.0)
    frames = extract_frames(video, str(tmp_path / "frames"), interval=3.0)
    assert len(frames) >= 2
    for p in frames:
        assert Path(p).exists()


def test_dedup_frames_identical(tmp_path):
    video = str(tmp_path / "test.mp4")
    _make_test_video(video, duration=6.0)
    frames = extract_frames(video, str(tmp_path / "frames"), interval=2.0)
    deduped = dedup_frames(frames, threshold=0.95)
    assert len(deduped) == 1
```

- [ ] **Step 3: 跑测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_frame_extractor.py -v`
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
cd /home/wxc/projects/smart-scribe
git add -A
git commit -m "feat: ffmpeg frame extraction + pixel similarity dedup"
```

---

### Task 7: OCR 服务 (本地 + 云端切换)

**Files:**
- Create: `backend/app/services/ocr.py`
- Create: `backend/tests/test_ocr.py`
- Modify: `backend/app/api/settings.py` (加 OCR 模式读写)
- Modify: `backend/app/config.py` (ocr_mode 已存在)

**Interfaces:**
- Consumes: `app.config.Settings.ocr_mode`；设置 DB 中的 `paddleocr_cloud_key`
- Produces: `ocr_image(image_path: str, db: Session) -> OcrResult`，其中 `OcrResult = {text: str, boxes: list, scores: list}`；`ocr_batch(image_paths: list[str], db: Session) -> list[OcrResult]`

- [ ] **Step 1: 写 ocr.py**

```python
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ApiSettings
from app.services.crypto import decrypt


@dataclass
class OcrResult:
    text: str
    boxes: list = field(default_factory=list)
    scores: list = field(default_factory=list)


_ocr_instance = None


def _get_local_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    return _ocr_instance


def _ocr_local(image_path: str) -> OcrResult:
    ocr = _get_local_ocr()
    result = ocr.ocr(image_path, cls=True)
    if not result or not result[0]:
        return OcrResult(text="")
    texts, boxes, scores = [], [], []
    for line in result[0]:
        box, (txt, conf) = line
        texts.append(txt)
        boxes.append(box)
        scores.append(float(conf))
    return OcrResult(text="".join(texts), boxes=boxes, scores=scores)


def _ocr_cloud(image_path: str, api_key: str) -> OcrResult:
    import base64
    import httpx

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    resp = httpx.post(
        "https://aistudio.baidu.com/llm/lmapi/v3/paddleocr/ocr",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"image": b64},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return OcrResult(text=data.get("text", ""), boxes=data.get("boxes", []), scores=data.get("scores", []))


def ocr_image(image_path: str, db: Session) -> OcrResult:
    settings = get_settings()
    if settings.ocr_mode == "cloud":
        record = db.query(ApiSettings).filter_by(key="paddleocr_cloud_key").first()
        if not record or not record.encrypted_value:
            raise ValueError("云端 OCR 未配置 API key")
        api_key = decrypt(record.encrypted_value)
        return _ocr_cloud(image_path, api_key)
    return _ocr_local(image_path)


def ocr_batch(image_paths: list[str], db: Session) -> list[OcrResult]:
    return [ocr_image(p, db) for p in image_paths]
```

- [ ] **Step 2: 写 test_ocr.py**

本地 OCR 模型下载慢，测试只验证 OcrResult 数据结构和本地路径不存在的容错。云端测试 mock httpx。

```python
from unittest.mock import MagicMock, patch

from app.services.ocr import OcrResult, ocr_image


def test_ocr_result_dataclass():
    r = OcrResult(text="测试", boxes=[[0, 0]], scores=[0.95])
    assert r.text == "测试"
    assert r.scores == [0.95]


def test_ocr_local_calls_paddleocr(tmp_path, monkeypatch):
    img = tmp_path / "x.jpg"
    img.write_bytes(b"fake")
    monkeypatch.setattr("app.services.ocr._get_local_ocr", lambda: None)

    fake_ocr = MagicMock()
    fake_ocr.ocr.return_value = [[[[0, 0], [1, 0], [1, 1], [0, 1]], ("测试文本", 0.99)]]
    monkeypatch.setattr("paddleocr.PaddleOCR", lambda **kw: fake_ocr)

    db = MagicMock()
    result = ocr_image(str(img), db)
    assert "测试文本" in result.text
```

- [ ] **Step 3: 跑测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_ocr.py -v`
Expected: 2 passed

- [ ] **Step 4: 加 OCR 模式切换到 settings API**

在 `api/settings.py` 末尾追加：

```python
from app.config import get_settings


@router.get("/ocr-mode")
async def get_ocr_mode():
    return {"mode": get_settings().ocr_mode}


@router.post("/ocr-mode")
async def set_ocr_mode(mode: str):
    if mode not in ("local", "cloud"):
        from fastapi import HTTPException
        raise HTTPException(400, "mode 必须是 local 或 cloud")
    return {"status": "ok", "note": "OCR 模式通过环境变量 SMART_SCRIBE_OCR_MODE 配置，需重启生效"}
```

- [ ] **Step 5: Commit**

```bash
cd /home/wxc/projects/smart-scribe
git add -A
git commit -m "feat: PaddleOCR service with local/cloud switch"
```

---

### Task 8: 媒体处理流水线编排

**Files:**
- Create: `backend/app/services/pipeline.py`
- Create: `backend/tests/test_pipeline.py`
- Modify: `backend/app/api/media.py` (加 `POST /api/media/session/{id}/process` 和 `GET /api/media/evidence/{id}`)

**Interfaces:**
- Consumes: Task 4 的 Material; Task 6 的 frame_extractor; Task 7 的 ocr
- Produces: `process_session(session_id: int, db: Session) -> ProcessingResult`，其中 ProcessingResult 含 `frames_count`, `ocr_pages_count`, `evidence_blocks`；`POST /api/media/session/{id}/process` 端点；`GET /api/media/evidence/{id}` 端点

- [ ] **Step 1: 写 pipeline.py**

```python
from pathlib import Path
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import EvidenceBlock, Material
from app.services.frame_extractor import extract_and_dedup
from app.services.ocr import OcrResult, ocr_image
from app.services.storage import session_storage_dir, IMAGE_EXTS


@dataclass
class ProcessingResult:
    frames_count: int = 0
    ocr_pages_count: int = 0
    evidence_block_ids: list = field(default_factory=list)


_p_counters: dict[int, int] = {}
_s_counters: dict[int, int] = {}


def _next_p_id(session_id: int) -> str:
    _p_counters[session_id] = _p_counters.get(session_id, 0) + 1
    return f"P{_p_counters[session_id]:03d}"


def _process_video(material: Material, db: Session) -> tuple[int, int, list[str]]:
    d = session_storage_dir(material.session_id)
    frames_dir = d / "frames"
    frames = extract_and_dedup(material.file_path, str(frames_dir))

    blocks = []
    best_text_len = 0
    best_block_id = None

    for idx, fp in enumerate(frames):
        result = ocr_image(fp, db)
        if len(result.text.strip()) > 0:
            block_id = _next_p_id(material.session_id)
            is_main = len(result.text) > best_text_len * 0.5 if best_text_len else True
            timestamp = idx * 3.0
            eb = EvidenceBlock(
                block_id=block_id,
                session_id=material.session_id,
                material_id=material.id,
                type="screen",
                timestamp=timestamp,
                text=result.text,
                page_number=idx + 1,
                image_path=fp,
            )
            db.add(eb)
            db.flush()
            blocks.append(block_id)
            if len(result.text) > best_text_len:
                best_text_len = len(result.text)
                best_block_id = block_id

    return len(frames), len(blocks), blocks


def _process_image(material: Material, db: Session) -> tuple[int, int, list[str]]:
    result = ocr_image(material.file_path, db)
    block_id = _next_p_id(material.session_id)
    timestamp = float(material.sort_order) * 60.0
    eb = EvidenceBlock(
        block_id=block_id,
        session_id=material.session_id,
        material_id=material.id,
        type="screen",
        timestamp=timestamp,
        text=result.text,
        page_number=material.sort_order + 1,
        image_path=material.file_path,
    )
    db.add(eb)
    db.flush()
    return 1, 1 if result.text.strip() else 0, [block_id] if result.text.strip() else []


def process_session(session_id: int, db: Session) -> ProcessingResult:
    materials = db.query(Material).filter_by(session_id=session_id).order_by(Material.sort_order).all()
    result = ProcessingResult()
    all_blocks = []
    for m in materials:
        if m.status != "pending":
            continue
        if m.type == "video":
            fc, oc, blocks = _process_video(m, db)
        elif m.type == "image":
            fc, oc, blocks = _process_image(m, db)
        else:
            continue
        result.frames_count += fc
        result.ocr_pages_count += oc
        all_blocks.extend(blocks)
        m.status = "done"
    db.commit()
    result.evidence_block_ids = all_blocks
    return result
```

- [ ] **Step 2: 在 api/media.py 追加两个端点**

```python
from app.models import EvidenceBlock
from app.services.pipeline import process_session


@router.post("/api/media/session/{session_id}/process")
async def process_materials(session_id: int, db: Session = Depends(get_db)):
    result = process_session(session_id, db)
    return {
        "frames_count": result.frames_count,
        "ocr_pages_count": result.ocr_pages_count,
        "evidence_block_ids": result.evidence_block_ids,
    }


@router.get("/api/media/evidence/{session_id}")
async def list_evidence(session_id: int, db: Session = Depends(get_db)):
    blocks = db.query(EvidenceBlock).filter_by(session_id=session_id).order_by(EvidenceBlock.timestamp).all()
    return [
        {
            "id": b.block_id,
            "type": b.type,
            "timestamp": b.timestamp,
            "speaker": b.speaker,
            "text": b.text,
            "page_number": b.page_number,
            "image_path": b.image_path,
        }
        for b in blocks
    ]
```

- [ ] **Step 3: 写 test_pipeline.py**

```python
from io import BytesIO
from unittest.mock import patch

from app.services.ocr import OcrResult


async def test_process_image_creates_evidence(client, monkeypatch):
    fake = OcrResult(text="法拉第电磁感应定律")
    monkeypatch.setattr("app.services.pipeline.ocr_image", lambda path, db: fake)

    s = await client.post("/api/sessions", json={"title": "T"})
    sid = s.json()["id"]
    await client.post(
        "/api/media/upload",
        data={"session_id": sid, "sort_order": 0},
        files={"file": ("slide.png", BytesIO(b"fake"), "image/png")},
    )

    resp = await client.post(f"/api/media/session/{sid}/process")
    assert resp.status_code == 200
    assert resp.json()["ocr_pages_count"] == 1
    assert "P001" in resp.json()["evidence_block_ids"]

    evidence = await client.get(f"/api/media/evidence/{sid}")
    assert evidence.status_code == 200
    assert len(evidence.json()) == 1
    assert evidence.json()[0]["text"] == "法拉第电磁感应定律"
    assert evidence.json()[0]["type"] == "screen"
```

- [ ] **Step 4: 跑测试**

Run: `cd /home/wxc/projects/smart-scribe/backend && pytest tests/test_pipeline.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
cd /home/wxc/projects/smart-scribe
git add -A
git commit -m "feat: media processing pipeline - frames, OCR, evidence blocks"
```

---

## Self-Review

**Spec coverage check (Plan 1 范围内):**
- [x] 项目脚手架 + Docker Compose — Task 1
- [x] SQLite + SQLAlchemy 数据模型 — Task 2
- [x] 设置面板后端（加密存储 + API） — Task 3
- [x] 本地上传视频/音频/图片 — Task 4
- [x] 链接下载 (yt-dlp + Playwright) — Task 5
- [x] ffmpeg 抽帧去重 — Task 6
- [x] PaddleOCR 本地/云端切换 — Task 7
- [x] 媒体处理流水线编排 — Task 8

**不在 Plan 1 范围（留给 Plan 2/3）:**
- 语音转写（火山引擎）→ Plan 2
- AI 总结（DeepSeek 纠错+摘要+要点）→ Plan 2
- 证据块自动匹配 → Plan 2
- 引用校验 → Plan 2
- 前端工作区 → Plan 3
- WebSocket 进度推送 → Plan 3

**Placeholder scan:** 无 TBD/TODO。
**Type consistency:** OcrResult / MaterialSpec / ProcessingResult 命名一致。block_id 格式 P001 统一。

---