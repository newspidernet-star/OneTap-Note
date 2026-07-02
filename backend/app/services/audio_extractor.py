from pathlib import Path

import ffmpeg

from app.services.storage import resolve_storage_path, session_storage_dir


from pathlib import Path

import ffmpeg

from app.services.storage import resolve_storage_path, session_storage_dir


def extract_audio(video_path: str, output_dir: str) -> str:
    probe = ffmpeg.probe(video_path)
    audio_streams = [s for s in probe.get("streams", []) if s["codec_type"] == "audio"]
    if not audio_streams:
        raise ValueError("NO_AUDIO_STREAM")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest = str(out / f"{Path(video_path).stem}.wav")
    (
        ffmpeg.input(video_path)
        .output(dest, acodec="pcm_s16le", ac=1, ar=16000)
        .overwrite_output()
        .run(quiet=True)
    )
    return dest


def prepare_audio(material) -> str:
    if material.type == "audio":
        return resolve_storage_path(material.file_path)
    d = session_storage_dir(material.session_id)
    audio_dir = d / "audio"
    return extract_audio(resolve_storage_path(material.file_path), str(audio_dir))
