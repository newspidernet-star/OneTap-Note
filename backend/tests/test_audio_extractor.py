import ffmpeg
from pathlib import Path

from app.models import Material


def _make_stereo_video(path: str):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    video = ffmpeg.input("color=c=blue:s=64x64:d=3", f="lavfi")
    audio = ffmpeg.input("sine=frequency=440:duration=3", f="lavfi")
    (
        ffmpeg.output(video, audio, str(out), vcodec="libx264", acodec="aac", ar=44100, ac=2)
        .overwrite_output()
        .run(quiet=True)
    )


def test_extract_audio_from_video(tmp_path):
    from app.services.audio_extractor import extract_audio

    video = str(tmp_path / "video.mp4")
    _make_stereo_video(video)
    result = extract_audio(video, str(tmp_path / "audio"))
    assert Path(result).exists()
    assert result.endswith(".wav")


def test_extract_audio_stereo_to_mono(tmp_path):
    from app.services.audio_extractor import extract_audio

    video = str(tmp_path / "video.mp4")
    _make_stereo_video(video)
    result = extract_audio(video, str(tmp_path / "audio"))
    probe = ffmpeg.probe(result)
    stream = probe["streams"][0]
    assert stream["channels"] == 1
    assert int(stream["sample_rate"]) == 16000


def test_prepare_audio_video_material(tmp_path, db_session):
    from app.services.audio_extractor import prepare_audio

    video = str(tmp_path / "video.mp4")
    _make_stereo_video(video)
    m = Material(type="video", source="local_file", file_path=video, sort_order=0, session_id=1)
    result = prepare_audio(m)
    assert Path(result).exists()


def test_prepare_audio_audio_material(tmp_path, db_session):
    from app.services.audio_extractor import prepare_audio

    audio = str(tmp_path / "audio.wav")
    Path(audio).parent.mkdir(parents=True, exist_ok=True)
    (
        ffmpeg.input("sine=frequency=440:duration=2", f="lavfi")
        .output(audio, ar=16000, ac=1)
        .overwrite_output()
        .run(quiet=True)
    )
    m = Material(type="audio", source="local_file", file_path=audio, sort_order=0, session_id=1)
    result = prepare_audio(m)
    assert result == audio
