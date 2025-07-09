import os
import openai
from typing import Dict, List, Any
import json
from utils import write_vtt, write_srt
from io import StringIO
import streamlit as st


def setup_openai_client(api_key: str = None):
    """设置OpenAI客户端"""
    if api_key:
        client = openai.OpenAI(api_key=api_key)
    else:
        # 尝试从Streamlit secrets获取API key
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except:
            api_key = None
            
        # 如果secrets中没有，尝试从环境变量获取
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
            
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in .streamlit/secrets.toml or environment variable.")
        client = openai.OpenAI(api_key=api_key)
    return client


def transcribe_with_openai(audio_file_path: str, task: str = "transcribe", language: str = None, 
                          api_key: str = None, model: str = "whisper-1") -> Dict[str, Any]:
    """
    使用OpenAI Whisper API进行转录
    
    Args:
        audio_file_path: 音频文件路径
        task: "transcribe" 或 "translate"
        language: 语言代码 (可选)
        api_key: OpenAI API key
        model: 使用的模型 (默认 "whisper-1")
    
    Returns:
        包含转录结果的字典
    """
    client = setup_openai_client(api_key)
    
    with open(audio_file_path, "rb") as audio_file:
        # OpenAI Whisper API不支持task参数，只支持transcribe
        # 对于翻译，需要使用不同的API端点
        if task == "translate":
            # 使用translations API进行翻译
            transcript = client.audio.translations.create(
                model=model,
                file=audio_file,
                response_format="verbose_json"
            )
        else:
            # 使用transcriptions API进行转录
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                response_format="verbose_json",
                language=language
            )
    
    # 转换OpenAI API响应格式为与本地whisper兼容的格式
    result = {
        "text": transcript.text,
        "language": transcript.language,
        "segments": []
    }
    
    # 处理segments
    for segment in transcript.segments:
        result["segments"].append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip()
        })
    
    return result


def getSubs(segments: List[Dict], format: str, maxLineWidth: int) -> str:
    """生成字幕文件内容"""
    segmentStream = StringIO()

    if format == 'vtt':
        write_vtt(segments, file=segmentStream, maxLineWidth=maxLineWidth)
    elif format == 'srt':
        write_srt(segments, file=segmentStream, maxLineWidth=maxLineWidth)
    else:
        raise Exception("Unknown format " + format)

    segmentStream.seek(0)
    return segmentStream.read()


def transcribe_audio_file(audio_file_path: str, task: str = "transcribe", 
                         api_key: str = None) -> tuple:
    """
    转录音频文件并返回文本、VTT、SRT和语言信息
    
    Args:
        audio_file_path: 音频文件路径
        task: "transcribe" 或 "translate"
        api_key: OpenAI API key
    
    Returns:
        (text, vtt, srt, language)
    """
    results = transcribe_with_openai(audio_file_path, task=task, api_key=api_key)
    
    vtt = getSubs(results["segments"], "vtt", 45)
    srt = getSubs(results["segments"], "srt", 45)
    lang = results["language"]
    
    return results["text"], vtt, srt, lang 