import streamlit as st
from streamlit_lottie import st_lottie
from utils import write_vtt, write_srt
import ffmpeg
import requests
from typing import Iterator
from io import StringIO
import numpy as np
import pathlib
import os
from openai_whisper_utils import transcribe_audio_file

st.set_page_config(page_title="Auto Subtitled Video Generator", page_icon=":movie_camera:", layout="wide")

# Define a function that we can use to load lottie files from a link.
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


APP_DIR = pathlib.Path(__file__).parent.absolute()

LOCAL_DIR = APP_DIR / "local"
LOCAL_DIR.mkdir(exist_ok=True)
save_dir = LOCAL_DIR / "output"
save_dir.mkdir(exist_ok=True)


# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


col1, col2 = st.columns([1, 3])
with col1:
    lottie = load_lottieurl("https://assets1.lottiefiles.com/packages/lf20_HjK9Ol.json")
    st_lottie(lottie)

with col2:
    st.write("""
    ## Auto Subtitled Video Generator 
    ##### Upload a video file and get subtitles in multiple formats.
    ###### ➠ If you want to transcribe the video in its original language, select the task as "Transcribe"
    ###### ➠ If you want to translate the subtitles to English, select the task as "Translate" 
    ###### I recommend starting with the base model and then experimenting with the larger models, the small and medium models often work well. """)


def get_openai_api_key():
    """获取OpenAI API key"""
    if not OPENAI_API_KEY:
        st.error("请在环境变量中设置 OPENAI_API_KEY")
        st.stop()
    return OPENAI_API_KEY


# @st.cache_data
def inference(uploaded_file, task):
    with open(f"{save_dir}/input.mp4", "wb") as f:
            f.write(uploaded_file.read())
    audio = ffmpeg.input(f"{save_dir}/input.mp4")
    audio = ffmpeg.output(audio, f"{save_dir}/output.wav", acodec="pcm_s16le", ac=1, ar="16k")
    ffmpeg.run(audio, overwrite_output=True)
    
    api_key = get_openai_api_key()
    return transcribe_audio_file(f"{save_dir}/output.wav", task=task.lower(), api_key=api_key)




def main():
    st.info("使用OpenAI Whisper API进行转录，请确保已设置OPENAI_API_KEY环境变量")
    input_file = st.file_uploader("File", type=["mp4", "avi", "mov", "mkv"])
    # get the name of the input_file
    if input_file is not None:
        filename = input_file.name[:-4]
    else:
        filename = None
    task = st.selectbox("Select Task", ["Transcribe", "Translate"], index=0)
    if task == "Transcribe":
        if st.button("Transcribe"):
            results = inference(input_file, task)
            
            # 调试输出 - 添加安全检查
            st.write("DEBUG - Results structure:", type(results))
            st.write("DEBUG - Results length:", len(results))
            st.write("DEBUG - Results[0] (text):", results[0][:100] + "..." if len(results) > 0 and results[0] else "None")
            if len(results) > 3:
                st.write("DEBUG - Results[3] (raw_srt):", results[3][:200] + "..." if results[3] else "None")
            if len(results) > 4:
                st.write("DEBUG - Results[4] (raw_json):", results[4][:300] + "..." if results[4] else "None")
            else:
                st.error("返回值长度不正确，请清除缓存重试")
                st.button("清除缓存", on_click=st.cache_data.clear)
                return
            
            col3, col4 = st.columns(2)
            col5, col6, col7, col10, col11 = st.columns(5)
            col8, col9 = st.columns(2)
            with col3:
                st.video(input_file)
                
            with open("transcript.txt", "w+", encoding='utf8') as f:
                f.write(results[0])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.txt"), "rb") as f:
                datatxt = f.read()
                
            with open("transcript.vtt", "w+",encoding='utf8') as f:
                f.write(results[1])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.vtt"), "rb") as f:
                datavtt = f.read()
                
            with open("transcript.srt", "w+",encoding='utf8') as f:
                f.write(results[2])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.srt"), "rb") as f:
                datasrt = f.read()

            with open("transcript_raw.srt", "w+",encoding='utf8') as f:
                f.write(results[3])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript_raw.srt"), "rb") as f:
                datarawsrt = f.read()

            with open("transcript_raw.json", "w+",encoding='utf8') as f:
                f.write(results[4])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript_raw.json"), "rb") as f:
                datarawjson = f.read()

            with col5:
                st.download_button(label="Download Transcript (.txt)",
                                data=datatxt,
                                file_name="transcript.txt")
            with col6:   
                st.download_button(label="Download Transcript (.vtt)",
                                    data=datavtt,
                                    file_name="transcript.vtt")
            with col7:
                st.download_button(label="Download Transcript (.srt)",
                                    data=datasrt,
                                    file_name="transcript.srt")
            with col10:
                st.download_button(label="Download Raw SRT (debug)",
                                    data=datarawsrt,
                                    file_name="transcript_raw.srt")
            with col11:
                st.download_button(label="Download Raw JSON (debug)",
                                    data=datarawjson,
                                    file_name="transcript_raw.json")
            with col8:
                st.success("You can download the transcript in .srt format, edit it (if you need to) and upload it to YouTube to create subtitles for your video.")
            with col9:
                st.info("Streamlit refreshes after the download button is clicked. The data is cached so you can download the transcript again without having to transcribe the video again.")
    elif task == "Translate":
        if st.button("Translate to English"):
            results = inference(input_file, task)
            col3, col4 = st.columns(2)
            col5, col6, col7, col10, col11 = st.columns(5)
            col8, col9 = st.columns(2)
            with col3:
                st.video(input_file)
                
            with open("transcript.txt", "w+", encoding='utf8') as f:
                f.write(results[0])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.txt"), "rb") as f:
                datatxt = f.read()
                
            with open("transcript.vtt", "w+",encoding='utf8') as f:
                f.write(results[1])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.vtt"), "rb") as f:
                datavtt = f.read()
                
            with open("transcript.srt", "w+",encoding='utf8') as f:
                f.write(results[2])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.srt"), "rb") as f:
                datasrt = f.read()

            with open("transcript_raw.srt", "w+",encoding='utf8') as f:
                f.write(results[3])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript_raw.srt"), "rb") as f:
                datarawsrt = f.read()

            with open("transcript_raw.json", "w+",encoding='utf8') as f:
                f.write(results[4])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript_raw.json"), "rb") as f:
                datarawjson = f.read()
                
            with col5:
                st.download_button(label="Download Transcript (.txt)",
                                data=datatxt,
                                file_name="transcript.txt")
            with col6:   
                st.download_button(label="Download Transcript (.vtt)",
                                    data=datavtt,
                                    file_name="transcript.vtt")
            with col7:
                st.download_button(label="Download Transcript (.srt)",
                                    data=datasrt,
                                    file_name="transcript.srt")
            with col10:
                st.download_button(label="Download Raw SRT (debug)",
                                    data=datarawsrt,
                                    file_name="transcript_raw.srt")
            with col11:
                st.download_button(label="Download Raw JSON (debug)",
                                    data=datarawjson,
                                    file_name="transcript_raw.json")
            with col8:
                st.success("You can download the transcript in .srt format, edit it (if you need to) and upload it to YouTube to create subtitles for your video.")
            with col9:
                st.info("Streamlit refreshes after the download button is clicked. The data is cached so you can download the transcript again without having to transcribe the video again.")
    else:
        st.error("Please select a task.")


if __name__ == "__main__":
    main()
    st.markdown("###### Made with :heart: by [@BatuhanYılmaz](https://github.com/BatuhanYilmaz26) [![this is an image link](https://i.imgur.com/thJhzOO.png)](https://www.buymeacoffee.com/batuhanylmz)")