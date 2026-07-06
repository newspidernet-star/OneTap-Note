import json
import logging

import httpx
from sqlalchemy.orm import Session

from app.models import ApiSettings, EvidenceBlock, Match
from app.services.crypto import get_secret

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"
MAX_RETRIES = 5

logger = logging.getLogger("smart_scribe")

_MATERIAL_TYPES = {"video_frame", "image", "document", "screen"}

SYSTEM_PROMPT = """你是一个课堂/会议记录助手。请严格按 JSON 格式输出，不要添加任何 JSON 之外的解释文字。

重要原则：画面 OCR 文字是权威来源（视频里实际显示的文字），语音转写可能有同音字/术语错误。
当两份内容冲突时（如转写"大寻劝"vs OCR"大江大河"），以 OCR 为准纠错。

你的任务：
1. 纠错转写文本中的同音字/领域术语错误（优先依据 OCR），输出修正后的完整文本
2. 撰写详细的段落级摘要（8-10句），覆盖所有关键信息点，不要过于精简——保留足够的细节和上下文，让读者即使没课件也能理解核心内容
3. 提炼 3-5 条核心要点（术语名词优先用 OCR 显示的原文）

每个结论必须引用证据块 ID（格式: [S001] 或 [P003]），确保可追溯。

请输出合法 JSON，格式如下（示例）：
{
  "corrected_text": "修正后的完整转写文本...",
  "summary": "详细的段落级摘要...",
  "key_points": [
    {"point": "核心要点一", "citations": ["S001", "P003"]},
    {"point": "核心要点二", "citations": ["S002"]}
  ],
  "corrections": [
    {"offset": 0, "old": "错误文本", "new": "正确文本"}
  ]
}"""


def build_prompt(blocks: list[EvidenceBlock], matches: list[Match]) -> str:
    # OCR 放在前（权威，AI 先看到的版本），ASR 放后（可能有同音字错误）
    lines = ["## 画面 OCR 原文（权威，术语/名词以此为准）\n"]
    for b in blocks:
        if b.type in _MATERIAL_TYPES:
            lines.append(f"[{b.block_id}] [{b.timestamp:.0f}s] {b.text}")
    lines.append("\n## 语音转写原文（可能同音字错误，请依据上述 OCR 纠错）\n")
    for b in blocks:
        if b.type == "speech":
            lines.append(f"[{b.block_id}] [{b.speaker} {b.timestamp:.0f}s] {b.text}")
    lines.append("\n## S×P 匹配关联\n")
    block_map = {b.id: b.block_id for b in blocks}
    for m in matches:
        sid = block_map.get(m.speech_block_id, "?")
        pid = block_map.get(m.screen_block_id, "?")
        lines.append(f"- [{sid}] ↔ [{pid}] (相似度 {m.score:.2f})")
    lines.append("\n## Summary requirements\n")
    lines.append("- The final summary must synthesize BOTH visual evidence blocks (P/video frame/image OCR) and speech blocks (S/ASR).")
    lines.append("- If any P blocks contain meaningful text, include their concrete concepts, slide titles, labels, or selected-frame information in the summary and key points.")
    lines.append("- Do not write a speech-only summary when visual/OCR evidence exists. If visual evidence changes or supplements the speech, cite the P block and explain that content.")
    lines.append("- Prefer citations that mix S and P blocks when both support the same conclusion.")
    lines.append("\n请输出 JSON (不再额外解释):")
    return "\n".join(lines)


def _parse_json_content(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        parts = content.split("```")
        if len(parts) > 1:
            content = parts[1]
            if content.startswith("json"):
                content = content[4:].strip()
    return json.loads(content)


def call_deepseek(prompt: str, db: Session) -> dict:
    api_key = get_secret(db, "deepseek_api_key")
    if not api_key:
        raise ValueError("DeepSeek API key 未配置（设置页或 SMART_SCRIBE_DEEPSEEK_API_KEY 环境变量）")

    last_error: Exception | None = None
    last_raw: str | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = httpx.post(
                DEEPSEEK_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 8192,
                    "response_format": {"type": "json_object"},
                    "thinking": {"type": "disabled"},
                },
                timeout=180,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            last_raw = content
            return _parse_json_content(content)
        except (json.JSONDecodeError, KeyError) as e:
            last_error = e
            logger.warning(f"DeepSeek 返回内容解析失败（第 {attempt} 次）: {e}, raw={last_raw!r}")
        except httpx.HTTPStatusError as e:
            last_error = e
            logger.warning(f"DeepSeek HTTP 错误（第 {attempt} 次）: {e.response.status_code} {e.response.text[:200]}")
        except httpx.RequestError as e:
            last_error = e
            logger.warning(f"DeepSeek 请求错误（第 {attempt} 次）: {e}")

    raise RuntimeError(
        f"DeepSeek 总结生成失败，已重试 {MAX_RETRIES} 次。"
        f"最后一次错误: {last_error}"
        f"{f'; 返回内容: {last_raw[:200]!r}' if last_raw else ''}"
    )


def generate_summary(session_id: int, db: Session) -> dict:
    blocks = db.query(EvidenceBlock).filter_by(session_id=session_id).all()
    if not blocks:
        raise ValueError("会话无证据块")
    matches = db.query(Match).filter(
        Match.speech_block_id.in_([b.id for b in blocks if b.type == "speech"])
    ).all()
    prompt = build_prompt(blocks, matches)
    result = call_deepseek(prompt, db)
    # 如果 DeepSeek 返回空纠错文本（纯图片会话无语音可纠），用 OCR 原文兜底
    if not result.get("corrected_text", "").strip():
        ocr_parts = [f"[{b.block_id}] {b.text}" for b in blocks if b.type in _MATERIAL_TYPES]
        result["corrected_text"] = "\n".join(ocr_parts)
    return result


def verify_citations(result: dict, session_id: int, db: Session) -> dict:
    import re

    existing = {b.block_id for b in db.query(EvidenceBlock).filter_by(session_id=session_id).all()}
    all_cited: set[str] = set()
    for kp in result.get("key_points", []):
        all_cited.update(kp.get("citations", []))
    for field in ("corrected_text", "summary"):
        text = result.get(field, "")
        found = re.findall(r"\[(S\d+|P\d+)\]", text)
        all_cited.update(found)
    invalid = [cid for cid in all_cited if cid not in existing]
    return {"valid": len(invalid) == 0, "invalid_ids": invalid}


def detect_unused_blocks(result: dict, session_id: int, db: Session) -> list[str]:
    import re

    existing = {b.block_id for b in db.query(EvidenceBlock).filter_by(session_id=session_id).all()}
    all_cited: set[str] = set()
    for kp in result.get("key_points", []):
        all_cited.update(kp.get("citations", []))
    for field in ("corrected_text", "summary"):
        text = result.get(field, "")
        found = re.findall(r"\[(S\d+|P\d+)\]", text)
        all_cited.update(found)
    return sorted(existing - all_cited)


def save_summary(result: dict, session_id: int, db: Session) -> "Summary":
    from app.models import Summary

    unused = detect_unused_blocks(result, session_id, db)
    existing = db.query(Summary).filter_by(session_id=session_id).first()
    if existing:
        db.delete(existing)
        db.flush()
    summary = Summary(
        session_id=session_id,
        corrected_text=result.get("corrected_text", ""),
        summary_markdown=result.get("summary", ""),
        key_points=result.get("key_points", []),
        citations=result.get("key_points", []),
        unused_block_ids=unused,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def clear_summary(session_id: int, db: Session):
    from app.models import Summary

    existing = db.query(Summary).filter_by(session_id=session_id).first()
    if existing:
        db.delete(existing)
        db.commit()
