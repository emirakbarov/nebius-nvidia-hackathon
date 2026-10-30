import os
import base64
import shutil
import subprocess
import tempfile
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MAX_FRAMES = 24
BATCH_SIZE = 8
MIN_FRAMES = 2
FRAMES_PER_SECOND = 0.7

VISION_PROMPT = Path("prompts/vision.md").read_text(encoding="utf-8")

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ["NEBIUS_API_KEY"],
    timeout=90,
)

def image_part(path):
    data = base64.b64encode(Path(path).read_bytes()).decode("utf-8") # converts bytes into base64 then into a string
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}} # formats into expected type for API

def describe_frames(frames):
    descriptions = []
    for start in range(0, len(frames), BATCH_SIZE):
        batch = frames[start:start + BATCH_SIZE]
        if descriptions:
            summary = "\n\n".join(descriptions)
            intro = f"Already reported from earlier frames:\n{summary}\n\nHere are the next frames:"
        else:
            intro = "Here are the frames:"
        content = [{"type": "text", "text": intro}]
        content += [image_part(f) for f in batch]
        response = client.chat.completions.create(
            model = "nvidia/Nemotron-3.5-Super-VL",
            messages = [
                {
                    "role": "system",
                    "content" : VISION_PROMPT
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            descriptions.append(text)
    return "\n\n".join(descriptions)


def get_duration(video_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         video_path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())

def extract_frames(video_path):

    duration = get_duration(video_path)
    max_frames = min(max(round(duration * FRAMES_PER_SECOND), MIN_FRAMES), MAX_FRAMES)
    rate = max_frames / duration
    
    folder = Path(tempfile.mkdtemp(prefix="frames_"))

    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vf", f"fps={rate},scale=1024:-1",
         "-q:v", "2",
         str(folder / "frame_%03d.jpg")],
        check=True,
        capture_output=True,
    )

    frames = sorted(folder.glob("frame_*.jpg"))[:max_frames]

    return folder, frames

if __name__ == "__main__":
    folder, frames = extract_frames("reel.mp4")
    print(describe_frames(frames))
    print(f"{len(frames)} frames in {folder}")
    for f in frames:
        print(f)

    shutil.rmtree(folder, ignore_errors= True)