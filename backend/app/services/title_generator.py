import httpx
import re
from sqlalchemy.orm import Session

from app.models import ApiSettings
from app.services.crypto import get_secret

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"

SYSTEM_PROMPT = """你是一个标题生成助手。请根据用户提供的课堂或会议内容，生成一个简短、准确的标题。
要求：
- 2~8 个汉字
- 不要标点符号
- 不要解释，只输出标题"""


def _clean_title(text: str) -> str:
    text = text.strip()
    # Remove quotes
    text = text.strip("'\"").strip("「」").strip("【】").strip()
    # Remove punctuation
    text = re.sub(r"[\s\n\r\t.,;:!?。，；：！？、]", "", text)
    # Limit length
    if len(text) > 20:
        text = text[:20]
    return text


def generate_title(text: str, db: Session) -> str | None:
    if not text or not text.strip():
        return None

    record = get_secret(db, "deepseek_api_key")
    if not record:
        return None
    api_key = record

    sample = text.strip()[:1500]

    try:
        # 分开超时：连接 5s 读取 10s 写入 5s（总约 20s 上限）
        resp = httpx.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"请为以下内容生成标题：\n\n{sample}"},
                ],
                "temperature": 0.3,
                "max_tokens": 256,
                "thinking": {"type": "disabled"},
            },
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        title = _clean_title(content)
        return title if title else None
    except Exception as e:
        import logging
        logging.getLogger("smart_scribe").warning(f"Title generation failed: {e}")
        return None
