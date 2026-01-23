import argparse
import json
from loguru import logger

from xhs_utils.audio_filter import get_default_media_path, process_media_dir


def build_parser():
    parser = argparse.ArgumentParser(description="后处理过滤无人声解说（VAD）")
    parser.add_argument("--media-dir", default=None, help="媒体目录，默认 datas/media_datas")
    parser.add_argument("--action", default="mark", choices=["mark", "delete"], help="无声处理动作")
    parser.add_argument("--ffmpeg-path", default="ffmpeg", help="ffmpeg 可执行文件路径")
    parser.add_argument("--vad-aggressiveness", type=int, default=2, choices=[0, 1, 2, 3], help="VAD 灵敏度")
    parser.add_argument("--vad-frame-ms", type=int, default=30, choices=[10, 20, 30], help="VAD 帧长(ms)")
    parser.add_argument("--min-speech-seconds", type=float, default=1.0, help="最短语音时长阈值")
    parser.add_argument("--min-speech-ratio", type=float, default=0.02, help="语音占比阈值")
    parser.add_argument("--threshold-mode", default="any", choices=["any", "all"], help="阈值判定方式")
    parser.add_argument("--force", action="store_true", help="强制重新检测")
    parser.add_argument("--keep-audio", action="store_true", help="保留抽取的音频文件")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    base_path = args.media_dir or get_default_media_path()
    logger.info(f"开始后处理: {base_path}")
    summary = process_media_dir(
        base_path=base_path,
        action=args.action,
        ffmpeg_path=args.ffmpeg_path,
        vad_aggressiveness=args.vad_aggressiveness,
        vad_frame_ms=args.vad_frame_ms,
        min_speech_seconds=args.min_speech_seconds,
        min_speech_ratio=args.min_speech_ratio,
        threshold_mode=args.threshold_mode,
        force=args.force,
        keep_audio=args.keep_audio,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
