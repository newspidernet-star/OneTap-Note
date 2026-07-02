import json
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
        _ocr_instance = PaddleOCR(use_textline_orientation=True, lang="ch")
    return _ocr_instance


def _ocr_local(image_path: str) -> OcrResult:
    global _ocr_instance
    try:
        ocr = _get_local_ocr()
        results = ocr.predict(image_path)
    except Exception:
        # PaddlePaddle can leave the model in a bad state — recreate next time
        _ocr_instance = None
        return OcrResult(text="")
    if not results:
        return OcrResult(text="")
    res = results[0]
    rec_texts = res["rec_texts"] if isinstance(res, dict) else getattr(res, "rec_texts", [])
    rec_scores = res["rec_scores"] if isinstance(res, dict) else getattr(res, "rec_scores", [])
    dt_polys = res["dt_polys"] if isinstance(res, dict) else getattr(res, "dt_polys", [])
    if not rec_texts:
        return OcrResult(text="")
    boxes = []
    for poly in dt_polys:
        try:
            boxes.append(poly.tolist() if hasattr(poly, "tolist") else list(poly))
        except Exception:
            boxes.append([])
    scores = [float(s) for s in rec_scores]
    return OcrResult(text="".join(str(t) for t in rec_texts), boxes=boxes, scores=scores)


def _ocr_cloud(image_path: str, api_key: str) -> OcrResult:
    import httpx
    import time

    JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
    MODEL = "PP-OCRv6"
    headers = {"Authorization": f"bearer {api_key}"}
    optional_payload = {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useTextlineOrientation": False,
    }

    # 429 限流重试（最多 3 次，指数退避）
    for attempt in range(3):
        with open(image_path, "rb") as f:
            resp = httpx.post(
                JOB_URL,
                headers=headers,
                data={"model": MODEL, "optionalPayload": json.dumps(optional_payload)},
                files={"file": f},
                timeout=30,
            )
        if resp.status_code == 429:
            if attempt < 2:
                delay = (attempt + 1) * 3
                time.sleep(delay)
                continue
        resp.raise_for_status()
        break
    job_id = resp.json()["data"]["jobId"]

    for _ in range(120):
        time.sleep(2)
        r = httpx.get(f"{JOB_URL}/{job_id}", headers=headers, timeout=10)
        r.raise_for_status()
        state = r.json()["data"]["state"]
        if state == "done":
            jsonl_url = r.json()["data"]["resultUrl"]["jsonUrl"]
            break
        if state == "failed":
            raise ValueError(f"PaddleOCR 任务失败: {r.json()['data'].get('errorMsg')}")
    else:
        raise TimeoutError("PaddleOCR 任务超时")

    text_parts = []
    resp = httpx.get(jsonl_url, timeout=30)
    resp.raise_for_status()
    for line in resp.text.strip().split("\n"):
        if not line.strip():
            continue
        result = json.loads(line.strip())["result"]
        # PP-OCRv6 返回 ocrResults[].prunedResult.rec_texts
        for res in result.get("ocrResults", []):
            pruned = res.get("prunedResult", {})
            rec_texts = pruned.get("rec_texts", [])
            if rec_texts:
                text_parts.append("".join(str(t) for t in rec_texts))
            # 兜底：部分接口可能直接返回 text/markdown
            text = res.get("text") or res.get("markdown", {}).get("text")
            if text:
                text_parts.append(text)
        # 兼容 PaddleOCR-VL-1.6 的 layoutParsingResults
        for res in result.get("layoutParsingResults", []):
            markdown = res.get("markdown", {})
            if isinstance(markdown, dict) and markdown.get("text"):
                text_parts.append(markdown["text"])

    return OcrResult(text="\n".join(text_parts))


def ocr_image(image_path: str, db: Session) -> OcrResult:
    settings = get_settings()
    if settings.ocr_mode == "cloud":
        record = db.query(ApiSettings).filter_by(key="paddleocr_cloud_key").first()
        if not record or not record.encrypted_value:
            raise ValueError("云端 OCR 未配置 API key")
        api_key = decrypt(record.encrypted_value)
        return _ocr_cloud(image_path, api_key)
    return _ocr_local(image_path)


def _ocr_cloud_parallel(image_paths: list[str], api_key: str) -> list[OcrResult]:
    import concurrent.futures
    results: list[OcrResult | None] = [None] * len(image_paths)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(image_paths)) as executor:
        futures = {executor.submit(_ocr_cloud, p, api_key): i for i, p in enumerate(image_paths)}
        for future in concurrent.futures.as_completed(futures):
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as e:
                results[i] = OcrResult(text="")
    return [r if r is not None else OcrResult(text="") for r in results]


def ocr_batch(image_paths: list[str], db: Session) -> list[OcrResult]:
    settings = get_settings()
    if settings.ocr_mode == "cloud":
        record = db.query(ApiSettings).filter_by(key="paddleocr_cloud_key").first()
        if not record or not record.encrypted_value:
            raise ValueError("云端 OCR 未配置 API key")
        api_key = decrypt(record.encrypted_value)
        return _ocr_cloud_parallel(image_paths, api_key)
    return [ocr_image(p, db) for p in image_paths]