import json
import os
import subprocess
import tempfile
import time
import wave

import webrtcvad
from loguru import logger

VALID_FRAME_MS = (10, 20, 30)
VALID_SAMPLE_RATES = (8000, 16000, 32000, 48000)


def get_default_media_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../datas/media_datas"))


def extract_audio(video_path, audio_path, ffmpeg_path="ffmpeg"):
    cmd = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        video_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-vn",
        "-f",
        "wav",
        audio_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 执行失败: {result.stderr.strip() or result.stdout.strip()}")


def detect_speech_vad(audio_path, aggressiveness=2, frame_ms=30):
    if frame_ms not in VALID_FRAME_MS:
        raise ValueError(f"vad_frame_ms 仅支持 {VALID_FRAME_MS}")
    vad = webrtcvad.Vad(int(aggressiveness))
    with wave.open(audio_path, "rb") as wf:
        sample_rate = wf.getframerate()
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise ValueError("音频必须是单声道 16bit PCM")
        if sample_rate not in VALID_SAMPLE_RATES:
            raise ValueError(f"采样率仅支持 {VALID_SAMPLE_RATES}")
        frame_count = int(sample_rate * frame_ms / 1000.0)
        bytes_per_frame = frame_count * 2
        total_frames = 0
        speech_frames = 0
        while True:
            frame = wf.readframes(frame_count)
            if len(frame) < bytes_per_frame:
                break
            total_frames += 1
            if vad.is_speech(frame, sample_rate):
                speech_frames += 1
    if total_frames == 0:
        return {
            "speech_frames": 0,
            "total_frames": 0,
            "speech_ratio": 0.0,
            "speech_seconds": 0.0,
        }
    speech_ratio = speech_frames / total_frames
    speech_seconds = speech_frames * (frame_ms / 1000.0)
    return {
        "speech_frames": speech_frames,
        "total_frames": total_frames,
        "speech_ratio": speech_ratio,
        "speech_seconds": speech_seconds,
    }


def evaluate_speech(metrics, min_speech_seconds, min_speech_ratio, threshold_mode="any"):
    if threshold_mode == "all":
        return metrics["speech_seconds"] >= min_speech_seconds and metrics["speech_ratio"] >= min_speech_ratio
    return metrics["speech_seconds"] >= min_speech_seconds or metrics["speech_ratio"] >= min_speech_ratio


def load_info_json(info_path):
    if not os.path.exists(info_path):
        return {}
    with open(info_path, mode="r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return {}
    try:
        return json.loads(content.splitlines()[0])
    except json.JSONDecodeError:
        logger.warning(f"info.json 解析失败: {info_path}")
        return {}


def write_info_json(info_path, payload):
    with open(info_path, mode="w", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def iter_video_targets(base_path, video_name="video.mp4"):
    for root, _dirs, files in os.walk(base_path):
        if video_name in files:
            yield os.path.join(root, video_name), os.path.join(root, "info.json")


def analyze_video(
    video_path,
    ffmpeg_path="ffmpeg",
    vad_aggressiveness=2,
    vad_frame_ms=30,
    min_speech_seconds=1.0,
    min_speech_ratio=0.02,
    threshold_mode="any",
    keep_audio=False,
):
    note_dir = os.path.dirname(video_path)
    if keep_audio:
        audio_path = os.path.join(note_dir, "_audio.wav")
        temp_dir = None
    else:
        temp_dir = tempfile.TemporaryDirectory()
        audio_path = os.path.join(temp_dir.name, "audio.wav")
    try:
        extract_audio(video_path, audio_path, ffmpeg_path=ffmpeg_path)
        metrics = detect_speech_vad(
            audio_path,
            aggressiveness=vad_aggressiveness,
            frame_ms=vad_frame_ms,
        )
        speech_detected = evaluate_speech(
            metrics,
            min_speech_seconds=min_speech_seconds,
            min_speech_ratio=min_speech_ratio,
            threshold_mode=threshold_mode,
        )
        metrics["speech_detected"] = speech_detected
        return metrics
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def process_video(
    video_path,
    info_path,
    action="mark",
    ffmpeg_path="ffmpeg",
    vad_aggressiveness=2,
    vad_frame_ms=30,
    min_speech_seconds=1.0,
    min_speech_ratio=0.02,
    threshold_mode="any",
    keep_audio=False,
):
    try:
        metrics = analyze_video(
            video_path,
            ffmpeg_path=ffmpeg_path,
            vad_aggressiveness=vad_aggressiveness,
            vad_frame_ms=vad_frame_ms,
            min_speech_seconds=min_speech_seconds,
            min_speech_ratio=min_speech_ratio,
            threshold_mode=threshold_mode,
            keep_audio=keep_audio,
        )
    except Exception as exc:
        logger.error(f"处理失败: {video_path} -> {exc}")
        return {
            "status": "error",
            "video_path": video_path,
            "error": str(exc),
        }

    info = load_info_json(info_path)
    info.update(
        {
            "speech_checked": True,
            "speech_detected": metrics["speech_detected"],
            "speech_ratio": metrics["speech_ratio"],
            "speech_seconds": metrics["speech_seconds"],
            "speech_frames": metrics["speech_frames"],
            "speech_total_frames": metrics["total_frames"],
            "speech_vad_aggressiveness": vad_aggressiveness,
            "speech_vad_frame_ms": vad_frame_ms,
            "speech_min_seconds": min_speech_seconds,
            "speech_min_ratio": min_speech_ratio,
            "speech_threshold_mode": threshold_mode,
            "speech_checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    if action == "delete" and not metrics["speech_detected"]:
        if os.path.exists(video_path):
            os.remove(video_path)
            info["speech_removed_video"] = True
            logger.info(f"删除无声视频: {video_path}")
    write_info_json(info_path, info)

    return {
        "status": "ok",
        "video_path": video_path,
        "speech_detected": metrics["speech_detected"],
        "speech_ratio": metrics["speech_ratio"],
        "speech_seconds": metrics["speech_seconds"],
    }


def process_media_dir(
    base_path,
    action="mark",
    ffmpeg_path="ffmpeg",
    vad_aggressiveness=2,
    vad_frame_ms=30,
    min_speech_seconds=1.0,
    min_speech_ratio=0.02,
    threshold_mode="any",
    force=False,
    keep_audio=False,
):
    base_path = os.path.abspath(base_path)
    if not os.path.isdir(base_path):
        raise ValueError(f"媒体目录不存在: {base_path}")
    summary = {
        "total": 0,
        "processed": 0,
        "speech": 0,
        "no_speech": 0,
        "skipped": 0,
        "errors": 0,
    }
    for video_path, info_path in iter_video_targets(base_path):
        summary["total"] += 1
        info = load_info_json(info_path)
        if info.get("speech_checked") and not force:
            summary["skipped"] += 1
            continue
        result = process_video(
            video_path,
            info_path,
            action=action,
            ffmpeg_path=ffmpeg_path,
            vad_aggressiveness=vad_aggressiveness,
            vad_frame_ms=vad_frame_ms,
            min_speech_seconds=min_speech_seconds,
            min_speech_ratio=min_speech_ratio,
            threshold_mode=threshold_mode,
            keep_audio=keep_audio,
        )
        if result["status"] == "error":
            summary["errors"] += 1
            continue
        summary["processed"] += 1
        if result["speech_detected"]:
            summary["speech"] += 1
        else:
            summary["no_speech"] += 1
    logger.info(f"后处理完成: {summary}")
    return summary
