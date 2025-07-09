import textwrap
import zlib
from typing import Iterator, TextIO


def exact_div(x, y):
    assert x % y == 0
    return x // y


def str2bool(string):
    str2val = {"True": True, "False": False}
    if string in str2val:
        return str2val[string]
    else:
        raise ValueError(f"Expected one of {set(str2val.keys())}, got {string}")


def optional_int(string):
    return None if string == "None" else int(string)


def optional_float(string):
    return None if string == "None" else float(string)


def compression_ratio(text) -> float:
    return len(text) / len(zlib.compress(text.encode("utf-8")))


def format_timestamp(seconds: float, always_include_hours: bool = False, fractionalSeperator: str = '.'):
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000

    hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
    return f"{hours_marker}{minutes:02d}:{seconds:02d}{fractionalSeperator}{milliseconds:03d}"


def write_txt(transcript: Iterator[dict], file: TextIO):
    for segment in transcript:
        print(segment['text'].strip(), file=file, flush=True)


def write_vtt(transcript: Iterator[dict], file: TextIO, maxLineWidth=None):
    print("WEBVTT\n", file=file)
    for segment in transcript:
        text = segment['text'].strip()
        if maxLineWidth and len(text) > maxLineWidth:
            words = text.split()
            segments = []
            current_segment = ""
            for word in words:
                if current_segment:
                    next_segment = current_segment + " " + word
                else:
                    next_segment = word
                # 只在句号+空格处强制分段
                if next_segment.endswith('. '):
                    segments.append(next_segment.strip())
                    current_segment = ""
                elif len(next_segment) > maxLineWidth and current_segment:
                    segments.append(current_segment.strip())
                    current_segment = word
                else:
                    current_segment = next_segment
            if current_segment:
                segments.append(current_segment.strip())
            segment_duration = segment['end'] - segment['start']
            segment_duration_per_part = segment_duration / len(segments)
            for j, segment_text in enumerate(segments):
                start_time = segment['start'] + j * segment_duration_per_part
                end_time = segment['start'] + (j + 1) * segment_duration_per_part
                print(
                    f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n"
                    f"{segment_text.replace('-->', '->')}\n",
                    file=file,
                    flush=True,
                )
        else:
            print(
                f"{format_timestamp(segment['start'])} --> {format_timestamp(segment['end'])}\n"
                f"{text.replace('-->', '->')}\n",
                file=file,
                flush=True,
            )


def write_srt(transcript: Iterator[dict], file: TextIO, maxLineWidth=None):
    """
    Write a transcript to a file in SRT format.
    Example usage:
        from pathlib import Path
        from whisper.utils import write_srt
        result = transcribe(model, audio_path, temperature=temperature, **args)
        # save SRT
        audio_basename = Path(audio_path).stem
        with open(Path(output_dir) / (audio_basename + ".srt"), "w", encoding="utf-8") as srt:
            write_srt(result["segments"], file=srt)
    """
    subtitle_index = 1
    for i, segment in enumerate(transcript, start=1):
        text = segment['text'].strip()
        if maxLineWidth and len(text) > maxLineWidth:
            words = text.split()
            segments = []
            current_segment = ""
            for word in words:
                if current_segment:
                    next_segment = current_segment + " " + word
                else:
                    next_segment = word
                # 只在句号+空格处强制分段
                if next_segment.endswith('. '):
                    segments.append(next_segment.strip())
                    current_segment = ""
                elif len(next_segment) > maxLineWidth and current_segment:
                    segments.append(current_segment.strip())
                    current_segment = word
                else:
                    current_segment = next_segment
            if current_segment:
                segments.append(current_segment.strip())
            segment_duration = segment['end'] - segment['start']
            segment_duration_per_part = segment_duration / len(segments)
            for j, segment_text in enumerate(segments):
                start_time = segment['start'] + j * segment_duration_per_part
                end_time = segment['start'] + (j + 1) * segment_duration_per_part
                print(
                    f"{subtitle_index}\n"
                    f"{format_timestamp(start_time, always_include_hours=True, fractionalSeperator=',')} --> "
                    f"{format_timestamp(end_time, always_include_hours=True, fractionalSeperator=',')}\n"
                    f"{segment_text.replace('-->', '->')}\n",
                    file=file,
                    flush=True,
                )
                subtitle_index += 1
        else:
            print(
                f"{subtitle_index}\n"
                f"{format_timestamp(segment['start'], always_include_hours=True, fractionalSeperator=',')} --> "
                f"{format_timestamp(segment['end'], always_include_hours=True, fractionalSeperator=',')}\n"
                f"{text.replace('-->', '->')}\n",
                file=file,
                flush=True,
            )
            subtitle_index += 1


