import os
from dotenv import load_dotenv
import subprocess
import riva.client
import yt_dlp

load_dotenv()

def download_video(url, output_path="download.mp4"):
    options = {
        "outtmpl": output_path,
        "format": "mp4",
        "overwrites": True,
        "quiet": True
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])
    return output_path

def video_to_wav(video_path, wav_path="audio.wav"):
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vn", "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
         wav_path],
         check = True,
         capture_output = True
    ) 
    return wav_path

def transcribe(wav_path):
    auth = riva.client.Auth(
        uri="grpc.nvcf.nvidia.com:443",
        use_ssl = True,
        metadata_args=[
            ["function-id", "d3fe9151-442b-4204-a70d-5fcc597fd610"],
            ["authorization", f"Bearer {os.environ['PARAKEET_API_KEY']}"],
        ]
    )
    asr = riva.client.ASRService(auth)

    config = riva.client.RecognitionConfig(
        language_code="en-US",
        max_alternatives = 1,
        enable_automatic_punctuation = True
    )

    riva.client.add_audio_file_specs_to_config(config, wav_path)

    with open(wav_path, "rb") as f:
        audio = f.read()

    response = asr.offline_recognize(audio, config)
    return " ".join(r.alternatives[0].transcript.strip() for r in response.results)