import streamlit as st
import tempfile
import os
import re
import io
from datetime import timedelta
from typing import List, Tuple
from openai import OpenAI
import ffmpeg
import imageio_ffmpeg
try:
    from moviepy.editor import VideoFileClip
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

def format_timestamp(seconds: float) -> str:
    """将秒数转换为SRT格式的时间戳"""
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    seconds = td.total_seconds() % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")

def split_text_at_punctuation(text: str) -> List[str]:
    """在句号和感叹号后面分割文本"""
    # 使用正则表达式在 ". " 和 "! " 处分割
    segments = re.split(r'([.!] )', text)
    
    result = []
    current_segment = ""
    
    for i, segment in enumerate(segments):
        if i % 2 == 0:  # 实际文本
            current_segment += segment
        else:  # 标点符号
            current_segment += segment.rstrip()  # 移除末尾空格
            if current_segment.strip():
                result.append(current_segment.strip())
            current_segment = ""
    
    # 添加最后一个段落（如果有的话）
    if current_segment.strip():
        result.append(current_segment.strip())
    
    return result

def split_text_by_length(text: str, max_length: int = 26) -> List[str]:
    """按长度分割文本，确保单词不被截断"""
    words = text.split()
    segments = []
    current_segment = ""
    
    for word in words:
        # 检查添加新单词是否会超过长度限制
        test_segment = current_segment + (" " if current_segment else "") + word
        
        if len(test_segment) <= max_length:
            current_segment = test_segment
        else:
            # 如果当前段落不为空，保存它
            if current_segment:
                segments.append(current_segment)
                current_segment = word
            else:
                # 如果单个单词就超过了限制，强制添加
                segments.append(word)
                current_segment = ""
    
    # 添加最后一个段落
    if current_segment:
        segments.append(current_segment)
    
    return segments

def process_transcript_segments(segments, max_chars: int = 26) -> List[dict]:
    """处理转录段落，按照指定规则分割"""
    processed_segments = []
    
    for segment in segments:
        text = segment.text.strip()
        start_time = segment.start
        end_time = segment.end
        duration = end_time - start_time
        
        # 首先在标点符号处分割
        punctuation_splits = split_text_at_punctuation(text)
        
        for i, punct_segment in enumerate(punctuation_splits):
            # 然后按长度分割每个标点符号段落
            length_splits = split_text_by_length(punct_segment, max_chars)
            
            # 为每个分割的段落计算时间
            total_splits = len(length_splits)
            segment_duration = duration / len(punctuation_splits)
            
            for j, split_text in enumerate(length_splits):
                # 计算此子段落的开始和结束时间
                subsegment_duration = segment_duration / total_splits
                subsegment_start = start_time + (i * segment_duration) + (j * subsegment_duration)
                subsegment_end = subsegment_start + subsegment_duration
                
                processed_segments.append({
                    'text': split_text,
                    'start': subsegment_start,
                    'end': subsegment_end
                })
    
    return processed_segments

def generate_raw_srt(transcript) -> str:
    """生成原始SRT，每个单词一个字幕段，使用精确的单词级时间戳"""
    srt_content = []
    segment_number = 1
    
    # 检查是否有单词级时间戳
    if hasattr(transcript, 'words') and transcript.words and len(transcript.words) > 0:
        # 使用精确的单词级时间戳
        for word_info in transcript.words:
            srt_content.append(f"{segment_number}")
            srt_content.append(f"{format_timestamp(word_info.start)} --> {format_timestamp(word_info.end)}")
            srt_content.append(word_info.word)
            srt_content.append("")
            segment_number += 1
    else:
        # 回退到段落级处理（如果没有单词级时间戳）
        segments = getattr(transcript, 'segments', [])
        if segments:
            for segment in segments:
                words = segment.text.split()
                if not words:
                    continue
                    
                duration = segment.end - segment.start
                word_duration = duration / len(words)
                
                for i, word in enumerate(words):
                    word_start = segment.start + (i * word_duration)
                    word_end = word_start + word_duration
                    
                    srt_content.append(f"{segment_number}")
                    srt_content.append(f"{format_timestamp(word_start)} --> {format_timestamp(word_end)}")
                    srt_content.append(word)
                    srt_content.append("")
                    
                    segment_number += 1
    
    return "\n".join(srt_content)

def generate_srt(segments) -> str:
    """生成标准SRT字幕文件"""
    srt_content = []
    
    for i, segment in enumerate(segments, 1):
        srt_content.append(f"{i}")
        
        # 兼容字典和对象两种格式
        if hasattr(segment, 'start'):
            # 对象格式
            start_time = segment.start
            end_time = segment.end
            text = segment.text
        else:
            # 字典格式
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text']
        
        srt_content.append(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}")
        srt_content.append(text)
        srt_content.append("")
    
    return "\n".join(srt_content)

def extract_audio_from_video(video_file) -> str:
    """从视频文件提取音频"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file:
        audio_path = audio_file.name
    
    with tempfile.NamedTemporaryFile(delete=False) as video_temp:
        video_temp.write(video_file.read())
        video_temp_path = video_temp.name
    
    try:
        # 获取ffmpeg路径并使用它
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        st.write(f"🔧 Using ffmpeg: {ffmpeg_exe}")
        
        # 检查ffmpeg是否可执行
        if not os.path.exists(ffmpeg_exe):
            raise FileNotFoundError(f"FFmpeg not found at: {ffmpeg_exe}")
            
        # 使用ffmpeg提取音频
        stream = ffmpeg.input(video_temp_path)
        stream = ffmpeg.output(stream, audio_path, acodec='pcm_s16le', ar=16000)
        ffmpeg.run(stream, cmd=ffmpeg_exe, quiet=True, overwrite_output=True)
        
        os.unlink(video_temp_path)
        return audio_path
    except Exception as e:
        if os.path.exists(video_temp_path):
            os.unlink(video_temp_path)
        
        # 备用方案：尝试系统ffmpeg
        st.warning(f"⚠️ imageio-ffmpeg failed: {e}")
        st.info("🔄 Trying system ffmpeg...")
        
        try:
            with tempfile.NamedTemporaryFile(delete=False) as video_temp2:
                video_file.seek(0)
                video_temp2.write(video_file.read())
                video_temp2_path = video_temp2.name
            
            stream = ffmpeg.input(video_temp2_path)
            stream = ffmpeg.output(stream, audio_path, acodec='pcm_s16le', ar=16000)
            ffmpeg.run(stream, quiet=True, overwrite_output=True)
            
            os.unlink(video_temp2_path)
            st.success("✅ System ffmpeg worked!")
            return audio_path
            
        except Exception as e2:
            if os.path.exists(audio_path):
                os.unlink(audio_path)
            
            # 最终备用方案：MoviePy
            if HAS_MOVIEPY:
                st.info("🎬 Trying MoviePy as final option...")
                try:
                    with tempfile.NamedTemporaryFile(delete=False) as video_temp3:
                        video_file.seek(0)
                        video_temp3.write(video_file.read())
                        video_temp3_path = video_temp3.name
                    
                    # 使用 MoviePy 提取音频
                    video_clip = VideoFileClip(video_temp3_path)
                    audio_clip = video_clip.audio
                    audio_clip.write_audiofile(audio_path, verbose=False, logger=None)
                    
                    # 清理
                    audio_clip.close()
                    video_clip.close()
                    os.unlink(video_temp3_path)
                    
                    st.success("✅ MoviePy worked!")
                    return audio_path
                    
                except Exception as e3:
                    raise Exception(f"All methods failed. imageio-ffmpeg: {e}, system ffmpeg: {e2}, moviepy: {e3}")
            else:
                raise Exception(f"Both ffmpeg methods failed. imageio-ffmpeg: {e}, system ffmpeg: {e2}")
        
        raise e

def main():
    st.set_page_config(
        page_title="视频字幕生成器",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 视频字幕生成器")
    st.write("使用 OpenAI Whisper 为您的视频生成字幕")
    
    # 从环境变量获取API Key
    env_api_key = os.getenv('OPENAI_API_KEY')
    
    # 侧边栏配置
    with st.sidebar:
        st.header("配置")
        
        if env_api_key:
            st.success("✅ 已从环境变量获取 API Key")
            api_key = env_api_key
            # 显示部分API Key用于确认
            masked_key = env_api_key[:8] + "..." + env_api_key[-4:] if len(env_api_key) > 12 else "***"
            st.info(f"API Key: {masked_key}")
        else:
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                help="请输入您的 OpenAI API Key（或设置 OPENAI_API_KEY 环境变量）"
            )
        
        model = st.selectbox(
            "选择模型",
            ["whisper-1"],
            help="选择要使用的 Whisper 模型"
        )
        
        max_chars = st.slider(
            "每段字幕最大字符数",
            min_value=20,
            max_value=100,
            value=26,
            help="每个字幕段的最大字符数限制"
        )
    
    # 主界面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("上传视频文件")
        uploaded_file = st.file_uploader(
            "选择视频文件",
            type=['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'],
            help="支持常见的视频格式"
        )
        
        if uploaded_file and api_key:
            if st.button("🚀 开始生成字幕", type="primary"):
                try:
                    # 初始化OpenAI客户端
                    client = OpenAI(api_key=api_key)
                    
                    with st.spinner("正在提取音频..."):
                        audio_path = extract_audio_from_video(uploaded_file)
                        # 检查音频文件大小
                        audio_size = os.path.getsize(audio_path)
                        st.write(f"🎵 音频文件大小: {audio_size / 1024 / 1024:.2f} MB")
                    
                    with st.spinner("正在生成字幕..."):
                        with open(audio_path, 'rb') as audio_file:
                            transcript = client.audio.transcriptions.create(
                                file=audio_file,
                                model="whisper-1",
                                response_format="verbose_json",
                                timestamp_granularities=["word", "segment"]
                            )
                    
                    # 清理临时音频文件
                    os.unlink(audio_path)
                    
                    # 添加调试信息
                    st.write("🔍 **调试信息：**")
                    st.write(f"- transcript 类型: {type(transcript)}")
                    st.write(f"- 是否有 words 属性: {hasattr(transcript, 'words')}")
                    st.write(f"- 是否有 segments 属性: {hasattr(transcript, 'segments')}")
                    
                    if hasattr(transcript, 'words'):
                        words_count = len(transcript.words) if transcript.words else 0
                        st.write(f"- words 数量: {words_count}")
                        if words_count > 0:
                            st.write(f"- 第一个 word: {transcript.words[0]}")
                    
                    if hasattr(transcript, 'segments'):
                        segments_count = len(transcript.segments) if transcript.segments else 0
                        st.write(f"- segments 数量: {segments_count}")
                        if segments_count > 0:
                            st.write(f"- 第一个 segment: {transcript.segments[0]}")
                    
                    # 显示完整的 transcript 对象（前100个字符）
                    st.write(f"- transcript 内容预览: {str(transcript)[:500]}...")
                    
                    with st.spinner("正在处理字幕段落..."):
                        # 处理字幕段落，添加安全检查
                        segments = getattr(transcript, 'segments', [])
                        
                        if segments and len(segments) > 0:
                            st.write("✅ 使用API返回的segments数据")
                            
                            # 创建单词到时间戳的映射
                            words_timing = {}
                            if hasattr(transcript, 'words') and transcript.words:
                                for word_info in transcript.words:
                                    # 使用单词文本作为键，存储时间信息
                                    word_key = word_info.word.strip()
                                    if word_key not in words_timing:
                                        words_timing[word_key] = []
                                    words_timing[word_key].append({
                                        'start': word_info.start,
                                        'end': word_info.end,
                                        'used': False
                                    })
                            
                            # 处理每个segment，按字符数和标点分段
                            class TempSegment:
                                def __init__(self, text, start, end):
                                    self.text = text
                                    self.start = start
                                    self.end = end
                            
                            processed_segments_list = []
                            
                            for segment in segments:
                                segment_text = segment.text.strip()
                                segment_words = segment_text.split()
                                
                                # 为segment中的每个单词找到对应的时间戳
                                word_timings = []
                                for word in segment_words:
                                    clean_word = word.strip('.,!?;:"()[]')  # 移除标点符号进行匹配
                                    
                                    # 查找对应的时间戳
                                    found_timing = None
                                    if clean_word in words_timing:
                                        for timing_info in words_timing[clean_word]:
                                            if not timing_info['used']:
                                                found_timing = timing_info
                                                timing_info['used'] = True
                                                break
                                    
                                    if found_timing:
                                        word_timings.append({
                                            'word': word,
                                            'start': found_timing['start'],
                                            'end': found_timing['end']
                                        })
                                    else:
                                        # 如果找不到精确匹配，使用segment的时间进行估算
                                        word_index = segment_words.index(word)
                                        total_words = len(segment_words)
                                        duration = segment.end - segment.start
                                        word_duration = duration / total_words
                                        estimated_start = segment.start + (word_index * word_duration)
                                        estimated_end = estimated_start + word_duration
                                        
                                        word_timings.append({
                                            'word': word,
                                            'start': estimated_start,
                                            'end': estimated_end
                                        })
                                
                                # 首先按句子结束标点符号分段，然后按字符数分段
                                current_words = []
                                current_timings = []
                                
                                for i, (word, timing) in enumerate(zip(segment_words, word_timings)):
                                    current_words.append(word)
                                    current_timings.append(timing)
                                    
                                    # 分段条件（按优先级）
                                    should_split = False
                                    
                                    # 1. 优先级最高：句子结束标点符号 + 下一个单词大写开头（真正的新句子）
                                    # 排除常见缩写词
                                    common_abbreviations = ['Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'St.', 'Ave.', 'etc.', 'vs.', 'Inc.', 'Ltd.', 'Co.']
                                    if (i < len(segment_words) - 1 and 
                                        any(word.endswith(punct) for punct in ['.', '!', '?']) and
                                        segment_words[i + 1][0].isupper() and
                                        word not in common_abbreviations):
                                        should_split = True
                                    
                                    # 2. 最后一个单词
                                    elif i == len(segment_words) - 1:
                                        should_split = True
                                    
                                    # 3. 超过26个字符且有多个单词时，在上一个单词处分段
                                    elif len(' '.join(current_words)) > 26 and len(current_words) > 1:
                                        # 回退一个单词，在前面分段
                                        current_words.pop()
                                        current_timings.pop()
                                        
                                        if current_timings:  # 确保有内容可以分段
                                            current_text = ' '.join(current_words)
                                            start_time = current_timings[0]['start']
                                            end_time = current_timings[-1]['end']
                                            
                                            processed_segments_list.append(TempSegment(current_text, start_time, end_time))
                                        
                                        # 重新开始，包含当前单词
                                        current_words = [word]
                                        current_timings = [timing]
                                        should_split = False
                                    
                                    if should_split and current_timings:
                                        # 使用第一个和最后一个单词的精确时间戳
                                        current_text = ' '.join(current_words)
                                        start_time = current_timings[0]['start']
                                        end_time = current_timings[-1]['end']
                                        
                                        processed_segments_list.append(TempSegment(current_text, start_time, end_time))
                                        current_words = []
                                        current_timings = []
                            
                            processed_segments = processed_segments_list
                            
                        elif hasattr(transcript, 'words') and transcript.words:
                            st.write("⚠️ segments为空，使用words重新构建")
                            # 原有的words重构逻辑保持不变
                            # 创建一个临时的segment对象
                            class TempSegment:
                                def __init__(self, text, start, end):
                                    self.text = text
                                    self.start = start
                                    self.end = end
                            
                            # 智能分段：基于句子结构和标点符号
                            segments = []
                            current_words = []
                            segment_start = None
                            
                            def is_sentence_start(word_text):
                                """判断是否是句子开始（首字母大写且不是常见缩写）"""
                                if not word_text:
                                    return False
                                # 检查首字母是否大写
                                return word_text[0].isupper() and len(word_text) > 1
                            
                            def has_sentence_ending(word_text):
                                """判断单词是否包含句子结束标点"""
                                return any(punct in word_text for punct in ['.', '!', '?'])
                            

                            
                            for i, word in enumerate(transcript.words):
                                if segment_start is None:
                                    segment_start = word.start
                                
                                current_words.append(word.word)
                                
                                # 分段条件（按优先级）：
                                should_segment = False
                                
                                # 1. 最后一个单词
                                if i == len(transcript.words) - 1:
                                    should_segment = True
                                
                                # 2. 当前单词有句子结束标点
                                elif has_sentence_ending(word.word):
                                    should_segment = True
                                
                                # 3. 下一个单词是新句子开始（大写字母），且当前段落有至少2个单词
                                elif i + 1 < len(transcript.words) and len(current_words) >= 2:
                                    next_word = transcript.words[i + 1]
                                    if is_sentence_start(next_word.word):
                                        should_segment = True
                                
                                # 4. 长时间停顿（超过1.2秒）
                                elif i + 1 < len(transcript.words):
                                    next_word = transcript.words[i + 1]
                                    if next_word.start - word.end > 1.2:
                                        should_segment = True
                                
                                # 5. 段落过长（超过12个单词）强制分段
                                elif len(current_words) >= 12:
                                    should_segment = True
                                
                                if should_segment:
                                    # 保持Whisper原始文本不变
                                    segment_text = ' '.join(current_words)
                                    segments.append(TempSegment(segment_text, segment_start, word.end))
                                    current_words = []
                                    segment_start = None
                            
                            processed_segments = segments
                        else:
                            processed_segments = []
                        
                        # 生成SRT文件
                        standard_srt = generate_srt(processed_segments)
                        raw_srt = generate_raw_srt(transcript)
                        
                        # 添加SRT调试信息
                        st.write("📝 **SRT生成调试信息：**")
                        st.write(f"- 处理后的段落数: {len(processed_segments)}")
                        st.write(f"- 标准SRT长度: {len(standard_srt)} 字符")
                        st.write(f"- 原始SRT长度: {len(raw_srt)} 字符")
                        if len(standard_srt) > 0:
                            st.write(f"- 标准SRT预览: {standard_srt[:200]}...")
                        if len(raw_srt) > 0:
                            st.write(f"- 原始SRT预览: {raw_srt[:200]}...")
                    
                    st.success("✅ 字幕生成完成！")
                    
                    # 显示结果
                    with col2:
                        st.header("下载字幕")
                        
                        # 标准SRT下载
                        st.download_button(
                            label="📥 下载标准SRT字幕",
                            data=standard_srt,
                            file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}.srt",
                            mime="text/plain"
                        )
                        
                        # 原始SRT下载
                        st.download_button(
                            label="📥 下载原始SRT字幕（调试用）",
                            data=raw_srt,
                            file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_raw.srt",
                            mime="text/plain"
                        )
                        
                        st.info(f"📊 共生成 {len(processed_segments)} 个字幕段")
                    
                    # 预览字幕
                    st.header("字幕预览")
                    
                    # 选择预览类型
                    preview_type = st.radio(
                        "选择预览类型",
                        ["标准字幕", "原始字幕（每个单词）"],
                        horizontal=True
                    )
                    
                    if preview_type == "标准字幕":
                        preview_segments = processed_segments[:10]  # 只显示前10个段落
                        st.write("**标准字幕预览（前10段）：**")
                    else:
                        # 为原始字幕创建预览段落
                        raw_segments = []
                        if hasattr(transcript, 'words') and transcript.words and len(transcript.words) > 0:
                            # 使用精确的单词级时间戳（前20个单词）
                            for word_info in transcript.words[:20]:
                                raw_segments.append({
                                    'text': word_info.word,
                                    'start': word_info.start,
                                    'end': word_info.end
                                })
                        else:
                            # 回退到段落级处理
                            segments = getattr(transcript, 'segments', [])
                            if segments:
                                for segment in segments[:3]:  # 只处理前3个原始段落
                                    words = segment.text.split()
                                    duration = segment.end - segment.start
                                    word_duration = duration / len(words)
                                    
                                    for i, word in enumerate(words):
                                        word_start = segment.start + (i * word_duration)
                                        word_end = word_start + word_duration
                                        raw_segments.append({
                                            'text': word,
                                            'start': word_start,
                                            'end': word_end
                                        })
                        
                        preview_segments = raw_segments
                        st.write("**原始字幕预览（单词级精确时间戳）：**")
                    
                    for i, segment in enumerate(preview_segments, 1):
                        # 兼容字典和对象两种格式
                        if hasattr(segment, 'start'):
                            # 对象格式
                            start_time = format_timestamp(segment.start)
                            end_time = format_timestamp(segment.end)
                            text = segment.text
                        else:
                            # 字典格式
                            start_time = format_timestamp(segment['start'])
                            end_time = format_timestamp(segment['end'])
                            text = segment['text']
                        
                        st.write(f"**{i}.** `{start_time} --> {end_time}`")
                        st.write(f"   {text}")
                        st.write("")
                
                except Exception as e:
                    st.error(f"❌ 生成字幕时出错: {str(e)}")
        
        elif uploaded_file and not api_key:
            st.warning("⚠️ 请在侧边栏输入 OpenAI API Key")
        
        # 使用说明
        with st.expander("📋 使用说明"):
            st.write("""
            **功能特点：**
            - 支持多种视频格式（MP4, AVI, MOV, MKV, WMV, FLV）
            - 使用 OpenAI Whisper 进行高质量语音转录
            - 智能字幕分段：
              - 在句号和感叹号后自动分段
              - 每段最多26个字符（可调）
              - 保持单词完整性
            - 生成两种SRT文件：
              - 标准字幕文件（优化后的段落）
              - 原始字幕文件（每个单词一段，使用精确的单词级时间戳）
            
            **使用步骤：**
            1. 在侧边栏输入 OpenAI API Key
            2. 上传视频文件
            3. 点击"开始生成字幕"
            4. 等待处理完成
            5. 下载生成的SRT字幕文件
            """)

if __name__ == "__main__":
    main() 