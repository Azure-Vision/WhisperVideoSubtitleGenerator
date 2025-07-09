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
            # 首先按句号空格分割
            sentence_parts = text.split('. ')
            # 给除了最后一个部分都加回句号
            for i in range(len(sentence_parts) - 1):
                sentence_parts[i] += '.'
            
            # 然后对每个句子部分按字符限制进一步分割
            segments = []
            for sentence_part in sentence_parts:
                if len(sentence_part) <= maxLineWidth:
                    segments.append(sentence_part)
                else:
                    # 对超长的句子部分按单词分割
                    part_words = sentence_part.split()
                    current_segment = ""
                    
                    for word in part_words:
                        test_segment = current_segment + " " + word if current_segment else word
                        
                        if len(test_segment) > maxLineWidth and current_segment:
                            segments.append(current_segment.strip())
                            current_segment = word
                        else:
                            current_segment = test_segment
                    
                    if current_segment:
                        segments.append(current_segment.strip())
            
            # 改进的时间戳分配策略
            segment_duration = segment['end'] - segment['start']
            current_time = segment['start']
            
            # 计算单词数而不是字符数，更符合语音节奏
            total_words = sum(len(seg.split()) for seg in segments)
            min_duration = 0.8  # 每段最少0.8秒
            
            for i, segment_text in enumerate(segments):
                word_count = len(segment_text.split())
                
                if total_words > 0:
                    # 基于单词数按比例分配时间
                    word_ratio = word_count / total_words
                    duration = segment_duration * word_ratio
                    
                    # 确保最小时长
                    if duration < min_duration and i < len(segments) - 1:
                        duration = min_duration
                    
                    # 确保不超过剩余时间
                    remaining_time = (segment['end'] - current_time)
                    if duration > remaining_time:
                        duration = remaining_time
                else:
                    duration = segment_duration / len(segments)
                
                end_time = current_time + duration
                
                print(
                    f"{format_timestamp(current_time)} --> {format_timestamp(end_time)}\n"
                    f"{segment_text.replace('-->', '->')}\n",
                    file=file,
                    flush=True,
                )
                current_time = end_time
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
            # 首先按句号空格分割
            sentence_parts = text.split('. ')
            # 给除了最后一个部分都加回句号
            for i in range(len(sentence_parts) - 1):
                sentence_parts[i] += '.'
            
            # 然后对每个句子部分按字符限制进一步分割
            segments = []
            for sentence_part in sentence_parts:
                if len(sentence_part) <= maxLineWidth:
                    segments.append(sentence_part)
                else:
                    # 对超长的句子部分按单词分割
                    part_words = sentence_part.split()
                    current_segment = ""
                    
                    for word in part_words:
                        test_segment = current_segment + " " + word if current_segment else word
                        
                        if len(test_segment) > maxLineWidth and current_segment:
                            segments.append(current_segment.strip())
                            current_segment = word
                        else:
                            current_segment = test_segment
                    
                    if current_segment:
                        segments.append(current_segment.strip())
            
            # 改进的时间戳分配策略
            segment_duration = segment['end'] - segment['start']
            current_time = segment['start']
            
            # 计算单词数而不是字符数，更符合语音节奏
            total_words = sum(len(seg.split()) for seg in segments)
            min_duration = 0.8  # 每段最少0.8秒
            
            for j, segment_text in enumerate(segments):
                word_count = len(segment_text.split())
                
                if total_words > 0:
                    # 基于单词数按比例分配时间
                    word_ratio = word_count / total_words
                    duration = segment_duration * word_ratio
                    
                    # 确保最小时长
                    if duration < min_duration and j < len(segments) - 1:
                        duration = min_duration
                    
                    # 确保不超过剩余时间
                    remaining_time = (segment['end'] - current_time)
                    if duration > remaining_time:
                        duration = remaining_time
                else:
                    duration = segment_duration / len(segments)
                
                end_time = current_time + duration
                
                print(
                    f"{subtitle_index}\n"
                    f"{format_timestamp(current_time, always_include_hours=True, fractionalSeperator=',')} --> "
                    f"{format_timestamp(end_time, always_include_hours=True, fractionalSeperator=',')}\n"
                    f"{segment_text.replace('-->', '->')}\n",
                    file=file,
                    flush=True,
                )
                subtitle_index += 1
                current_time = end_time
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


def write_raw_srt(transcript: Iterator[dict], file: TextIO):
    """
    Write a transcript to a file in SRT format without any processing.
    Each original Whisper segment becomes one subtitle entry.
    """
    subtitle_index = 1
    for segment in transcript:
        text = segment['text'].strip()
        print(
            f"{subtitle_index}\n"
            f"{format_timestamp(segment['start'], always_include_hours=True, fractionalSeperator=',')} --> "
            f"{format_timestamp(segment['end'], always_include_hours=True, fractionalSeperator=',')}\n"
            f"{text.replace('-->', '->')}\n",
            file=file,
            flush=True,
        )
        subtitle_index += 1


