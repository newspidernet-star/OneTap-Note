import json
import logging
import re

import httpx
from sqlalchemy.orm import Session

from app.models import ApiSettings, EvidenceBlock, Match
from app.services.crypto import get_secret

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"
MAX_RETRIES = 5
LONG_NOTE_BLOCK_LIMIT = 240
LONG_NOTE_TEXT_LIMIT = 24000
REVIEW_BLOCK_LIMIT = 220
REVIEW_TEXT_LIMIT = 28000

logger = logging.getLogger("smart_scribe")

_MATERIAL_TYPES = {"video_frame", "image", "document", "screen"}

SYSTEM_PROMPT = """你是一个把视频转化为可直接使用知识的编辑。请严格按 JSON 格式输出，不要添加任何 JSON 之外的解释文字。

重要原则：画面 OCR 文字是权威来源（视频里实际显示的文字），语音转写可能有同音字/术语错误。
当两份内容冲突时（如转写"大寻劝"vs OCR"大江大河"），以 OCR 为准纠错。

你的任务：
1. 纠错转写文本中的同音字/领域术语错误（优先依据 OCR），输出修正后的完整文本
2. 先判断内容类型，再把内容写成一篇不看原视频也能理解、执行或用于决策的知识笔记
3. 提炼 2-5 条内部校验要点，用于保存证据引用；这些要点不能替代正文

知识笔记不是视频简介，也不是按时间顺序复述。直接给出最终结论、方法、步骤和判断依据。

根据内容类型选择结构：
- 教程/操作：一句话结论、操作步骤、常见错误、注意事项、关键画面
- 清单/框架：一句话总纲、按原始顺序保留的完整清单、可选的主题归类
- 观点/评论：核心观点、论证脉络、事实或案例、值得保留的表达、尚未解决的问题
- 访谈/对话：核心结论、不同立场、重要事实或案例、值得保留的表达、待确认问题
- 演示/产品：结果或能力、使用方式、关键过程、限制与注意事项、关键画面
- 会议/记录：结果或决策、过程节点、待办事项、负责人及期限、待确认问题
- 无法明确分类：核心结论、关键信息；只有原文明确提供用途时才增加使用方式

硬性规则：
1. summary 必须是结构清晰的 Markdown 正文，使用二级标题、段落、列表或步骤。
2. summary 不要写“本视频介绍了”“作者讲述了”等简介式句子。
3. summary 不输出证据 ID、证据统计、未引用证据或说话人标签。
4. 正文需要来源时，只使用人能理解的时间戳，如“> 来源：00:45-01:06”；每个结论最多保留 1-2 个代表性时间范围。
5. 合并时间相邻、语义重复的语音与画面，不为了数量凑内容。
6. 教程必须优先提取目标、步骤、错误方式、正确结果和注意事项；读者应能照着完成操作。
7. 关键画面只保留能展示操作位置、前后差异或最终结果的画面。
8. 追加素材是用户主动补充的重点，必须吸收进正文，除非内容为空或明显是噪声。
9. 无法从证据确认的内容不得补写。
10. key_points 仅用于内部证据校验，每条必须引用 1-2 个最强证据块 ID，优先组合语音与关键画面。
11. 如果原文明确声明有 N 条原则、忠告、步骤、方法、错误或案例，summary 必须逐项覆盖全部 N 条。可以按主题分组和精炼措辞，但不得用少数概括替代完整清单，也不得把不同条目合并到无法一一对应。
12. 输出前进行清单完整性检查：标题或正文声称有 N 条时，实际编号必须从 1 到 N 连续存在；证据不足的条目应标注“信息不足”，不能静默删除。
13. 不得擅自增加“行动优先级”“立即执行/短期/长期”等价值排序。只有原文明确给出优先级，或用户明确要求排序时才可以保留；原文中的号召性表达只属于对应条目，不能据此重排整份清单。
14. 不要为了结构完整而固定生成“注意事项”或“如何使用这些信息”。只有原始内容确实给出了风险、限制、前置条件、适用场景或具体用途时才保留对应章节。
15. 正文不得出现处理过程说明，例如“本分析基于语音转写”“未提供 OCR 画面”“角色名在转写中一致”“证据数量”“由 AI 生成”等。这些属于系统审计信息，应留在证据视图，不属于知识本身。

请输出合法 JSON，格式如下（示例）：
{
  "corrected_text": "修正后的完整转写文本...",
  "content_type": "tutorial",
  "summary": "## 一句话结论\n\n...\n\n## 操作步骤\n\n1. ...",
  "key_points": [
    {"point": "完成操作所需的核心结论", "citations": ["S001", "P003"]}
  ],
  "corrections": [
    {"offset": 0, "old": "错误文本", "new": "正确文本"}
  ]
}"""

REVIEW_SYSTEM_PROMPT = """你是知识笔记的完整性审校员。你的任务不是重新发挥，而是对照原始证据检查初稿是否准确、完整、可直接使用。

审校规则：
1. 原文明确声称有 N 条原则、步骤、方法、错误或案例时，最终正文必须逐项保留全部 N 条，编号连续且可一一对应。
2. 检查是否遗漏关键步骤、条件、限制、反例、案例、链接或用户追加素材。
3. 删除证据不支持的推断、优先级、价值判断和“立即/短期/长期”等擅自排序。
4. 保持初稿已经正确的结构与措辞，只修复确实存在的问题，不为了显得更丰富而扩写。
5. summary 是给人阅读的 Markdown，不显示 S/P 证据 ID；key_points 仅用于内部校验，每条引用 1-2 个真实证据 ID。
6. 无法确认的内容标注“信息不足”，不得编造。
7. 删除正文中的系统处理说明，包括转写来源、是否使用 OCR、证据数量、识别质量和模型自我评价。仅当这些信息本身就是原始内容讨论的主题时例外。
8. 不要补齐模板式章节。“注意事项”“如何使用”只有在证据确实支持且对内容有独立价值时才保留。

严格输出 JSON：
{
  "revised": true,
  "summary": "审校后的完整 Markdown 正文",
  "key_points": [{"point": "内部校验要点", "citations": ["S001"]}],
  "issues": ["修复了什么；如果无需修改则为空数组"]
}"""


def _block_is_priority(block: EvidenceBlock, priority_material_ids: set[int]) -> bool:
    return bool(block.is_manual) or (block.material_id is not None and block.material_id in priority_material_ids)


def _block_prefix(block: EvidenceBlock, priority_material_ids: set[int]) -> str:
    return " [用户重点追加]" if _block_is_priority(block, priority_material_ids) else ""


def _extract_links_from_text(text: str) -> list[str]:
    patterns = [
        r"https?://[^\s<>()\]\"'，。；、]+",
        r"www\.[^\s<>()\]\"'，。；、]+",
        r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        r"[A-Za-z0-9][A-Za-z0-9.-]+\.(?:com|io|ai|dev|app|org|net|cn)/[^\s<>()\]\"'，。；、]+",
    ]
    links: list[str] = []
    for pattern in patterns:
        links.extend(re.findall(pattern, text or "", flags=re.IGNORECASE))
    cleaned: list[str] = []
    seen: set[str] = set()
    for link in links:
        link = link.rstrip(".,;:!?)]}，。；：！？）】》")
        if link.startswith("www.") or link.lower().startswith("github.com/"):
            link = f"https://{link}"
        key = link.lower()
        if link and key not in seen:
            seen.add(key)
            cleaned.append(link)
    return cleaned


def _append_extracted_links(result: dict, blocks: list[EvidenceBlock]) -> None:
    links: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        for link in _extract_links_from_text(block.text or ""):
            key = link.lower()
            if key not in seen:
                seen.add(key)
                links.append(link)
    if not links:
        return
    summary = (result.get("summary") or "").rstrip()
    if "来源链接" in summary:
        return
    section = "\n\n## 来源链接\n\n" + "\n".join(f"- {link}" for link in links[:12])
    result["summary"] = f"{summary}{section}" if summary else section.strip()


def build_prompt(blocks: list[EvidenceBlock], matches: list[Match], priority_material_ids: set[int] | None = None) -> str:
    priority_material_ids = priority_material_ids or set()
    # OCR 放在前（权威，AI 先看到的版本），ASR 放后（可能有同音字错误）
    lines = ["## 画面 OCR 原文（权威，术语/名词以此为准）\n"]
    for b in blocks:
        if b.type in _MATERIAL_TYPES:
            lines.append(f"[{b.block_id}]{_block_prefix(b, priority_material_ids)} [{b.timestamp:.0f}s] {b.text}")
    lines.append("\n## 语音转写原文（可能同音字错误，请依据上述 OCR 纠错）\n")
    for b in blocks:
        if b.type == "speech":
            lines.append(f"[{b.block_id}]{_block_prefix(b, priority_material_ids)} [{b.speaker} {b.timestamp:.0f}s] {b.text}")
    priority_blocks = [b for b in blocks if _block_is_priority(b, priority_material_ids)]
    if priority_blocks:
        lines.append("\n## 用户重点追加素材（必须吸收，不要被旧内容淹没）\n")
        for b in priority_blocks:
            lines.append(f"[{b.block_id}] [{b.type} {b.timestamp:.0f}s] {b.text}")
    lines.append("\n## S×P 匹配关联\n")
    block_map = {b.id: b.block_id for b in blocks}
    for m in matches:
        sid = block_map.get(m.speech_block_id, "?")
        pid = block_map.get(m.screen_block_id, "?")
        lines.append(f"- [{sid}] ↔ [{pid}] (相似度 {m.score:.2f})")
    lines.append("\n## 知识笔记生成要求\n")
    lines.append("- 先识别内容类型，再选择对应结构；不要所有内容都套用摘要加要点。")
    lines.append("- 正文必须综合画面 OCR 与语音转写。画面出现有意义的标题、按钮、参数或结果时，必须写入正文。")
    lines.append("- 正文不显示 S/P 证据 ID；需要标注来源时只写时间戳。证据 ID 仅放在 key_points.citations 中供系统校验。")
    lines.append("- 不要按视频顺序复述，不要写成简介；直接告诉读者结论、如何操作或如何使用这些信息。")
    lines.append("- 显式清单必须保真：原文说有 N 条规则、步骤、忠告或案例时，正文必须保留并编号列出全部 N 条；如有必要，只做不改变原意的主题归类。")
    lines.append("- 输出前核对清单数量，不能把 28 条压缩成 6 个主题后丢掉其余内容。")
    lines.append("- 保持清单原始顺序。不要自行生成行动优先级，也不要把编号机械分成“立即、短期、长期”；原文明确排序或用户要求时除外。")
    lines.append("- 用户重点追加素材必须进入正文或内部校验要点，除非为空或噪声。")
    lines.append("- 如果 OCR/ASR 中出现 URL、GitHub 或项目链接，在正文末尾保留简短的“## 来源链接”章节。")
    lines.append("- 长视频、访谈、讲座或评论类内容不能压缩成短摘要；必须保留完整论证链、关键例子、人物/公司/国家对比、预测与分歧。")
    lines.append("- 对 30 分钟以上或证据块很多的内容，summary 应是一篇可独立阅读的长笔记，而不是目录式概括。")
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


def _call_deepseek_with_system(prompt: str, db: Session, system_prompt: str) -> dict:
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
                        {"role": "system", "content": system_prompt},
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


def call_deepseek(prompt: str, db: Session) -> dict:
    return _call_deepseek_with_system(prompt, db, SYSTEM_PROMPT)


def _blocks_text_length(blocks: list[EvidenceBlock]) -> int:
    return sum(len(block.text or "") for block in blocks)


def _is_long_note(blocks: list[EvidenceBlock]) -> bool:
    return len(blocks) > LONG_NOTE_BLOCK_LIMIT or _blocks_text_length(blocks) > LONG_NOTE_TEXT_LIMIT


def review_summary_completeness(result: dict, session_id: int, db: Session) -> dict:
    blocks = db.query(EvidenceBlock).filter_by(session_id=session_id).order_by(EvidenceBlock.timestamp).all()
    text_len = _blocks_text_length(blocks)
    if len(blocks) > REVIEW_BLOCK_LIMIT or text_len > REVIEW_TEXT_LIMIT:
        logger.info(
            "[AI-REVIEW] session %s: skipped for large evidence set, blocks=%s text_len=%s",
            session_id,
            len(blocks),
            text_len,
        )
        result = dict(result)
        result["_review_skipped"] = True
        result["_review_revised"] = False
        result["_review_issues"] = ["skipped-large-evidence-set"]
        return result
    evidence_lines = [
        f"[{block.block_id}] [{block.type} {_fmt_review_ts(block.timestamp)}] {block.text}"
        for block in blocks
        if (block.text or "").strip()
    ]
    review_prompt = "\n".join([
        "## 原始证据",
        *evidence_lines,
        "",
        "## 待审校初稿",
        json.dumps({
            "summary": result.get("summary", ""),
            "key_points": result.get("key_points", []),
        }, ensure_ascii=False),
        "",
        "请先逐项核对覆盖率，再输出最终 JSON。",
    ])
    reviewed = _call_deepseek_with_system(review_prompt, db, REVIEW_SYSTEM_PROMPT)
    if not (reviewed.get("summary") or "").strip():
        return result
    merged = dict(result)
    merged["summary"] = reviewed["summary"]
    if isinstance(reviewed.get("key_points"), list):
        merged["key_points"] = reviewed["key_points"]
    merged["_review_issues"] = reviewed.get("issues", [])
    merged["_review_revised"] = bool(reviewed.get("revised"))
    _append_extracted_links(merged, blocks)
    return merged


def _fmt_review_ts(seconds: float | int | None) -> str:
    total = max(0, int(seconds or 0))
    return f"{total // 60:02d}:{total % 60:02d}"


def generate_summary(session_id: int, db: Session, priority_material_ids: list[int] | None = None) -> dict:
    blocks = db.query(EvidenceBlock).filter_by(session_id=session_id).all()
    if not blocks:
        raise ValueError("会话无证据块")
    matches = db.query(Match).filter(
        Match.speech_block_id.in_([b.id for b in blocks if b.type == "speech"])
    ).all()
    prompt = build_prompt(blocks, matches, set(priority_material_ids or []))
    if _is_long_note(blocks):
        prompt = "\n".join([
            prompt,
            "",
            "## Long content mode",
            "This session has many transcript blocks. To avoid truncated JSON, set corrected_text to an empty string.",
            "Generate a detailed long-form knowledge note in summary and the internal citations in key_points only.",
            "Do not paste the full transcript into corrected_text.",
            "Do not over-compress a long video into a short abstract. The reader should understand the speaker's complete argument without opening the original video.",
            "For long interviews, lectures, talks, debates, or commentary videos, write 8-14 substantial sections when the source supports it.",
            "Each important section should include concrete claims, reasoning, examples, named people or companies, comparisons, predictions, and caveats from the source.",
            "Preserve the argument chain: why the speaker believes this, what historical analogy is used, what evidence or example supports it, and what conclusion follows.",
            "When the topic includes multiple positions or countries, keep each side's logic separate instead of merging it into one vague bullet.",
            "Target about 2500-5000 Chinese characters for a 30+ minute source, unless the source itself is repetitive or thin.",
            "Good section patterns for long viewpoint content: core thesis, historical analogy, technology path, China/US comparison, platform power structure, future forecast, actionable takeaways, memorable expressions, unresolved questions.",
            "It is acceptable for key_points to stay short. The summary must be rich.",
        ])
        result = _call_deepseek_with_system(prompt, db, SYSTEM_PROMPT)
    else:
        result = call_deepseek(prompt, db)
    _append_extracted_links(result, blocks)
    # 如果 DeepSeek 返回空纠错文本（纯图片会话无语音可纠），用 OCR 原文兜底
    if not result.get("corrected_text", "").strip():
        original_parts = [
            f"[{b.block_id}] {b.text}"
            for b in blocks
            if b.type == "speech" or b.type in _MATERIAL_TYPES
        ]
        result["corrected_text"] = "\n".join(original_parts)
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
