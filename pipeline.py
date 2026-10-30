import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv
from openai import OpenAI

from evidence import search_claim, format_evidence
from transcribe import video_to_wav, transcribe, download_video
from vision import describe_frames, extract_frames

load_dotenv()

MODEL = "nvidia/nemotron-3-super-120b-a12b"
USE_VISION = True
MAX_WORKERS = 6

VERDICT_PROMPT = Path("prompts/verdict.md").read_text(encoding="utf-8")
EXTRACTOR_PROMPT = Path("prompts/extractor.md").read_text(encoding="utf-8")

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ["NEBIUS_API_KEY"],
    timeout=90,
)


def extract_claims(user_content):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": EXTRACTOR_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    text = response.choices[0].message.content or ""
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # The first line describes the video once; the code attaches it to every search and verdict.
    video_context = ""
    if lines and lines[0].lower().startswith("context:"):
        video_context = lines.pop(0)[len("context:"):].strip()
        if video_context.lower().rstrip(".") == "unknown":
            video_context = ""

    return video_context, lines


def judge_claim(claim, today, video_context):
    try:
        results = search_claim(claim, video_context)
    except Exception:
        results = []

    evidence_text = format_evidence(results)
    user_message = (
        f"Today's date is {today}.\n\n"
        f"Description of the video: {video_context or 'unknown'}\n\n"
        f"Claim:\n{claim}\n\n"
        f"Evidence:\n{evidence_text}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": VERDICT_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    content = response.choices[0].message.content or ""

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = None
    if not isinstance(result, dict):
        result = {"verdict": "Error", "sources": [], "explanation": content}

    result["claim"] = claim
    result["source_details"] = [
        results[n - 1]
        for n in result.get("sources", [])
        if isinstance(n, int) and 1 <= n <= len(results)
    ]
    return result


def check_transcript(transcript, on_screen_text="", context=""):
    user_content = f"<transcript>\n{transcript}\n</transcript>"
    if on_screen_text:
        user_content += f"\n\n<on_screen_text>\n{on_screen_text}\n</on_screen_text>"
    if context:
        user_content += f"\n\n<user_context>\n{context}\n</user_context>"

    video_context, claims = extract_claims(user_content)
    if not claims:
        return []

    today = date.today()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        verdicts = list(pool.map(
            lambda claim: judge_claim(claim, today, video_context),
            claims,
        ))
    return verdicts


def check_video(video_path, context=""):
    folder = None
    on_screen_text = ""
    try:
        transcript = transcribe(video_to_wav(video_path))
        if USE_VISION:
            folder, frames = extract_frames(video_path)
            on_screen_text = describe_frames(frames)
    finally:
        Path("audio.wav").unlink(missing_ok=True)
        if folder:
            shutil.rmtree(folder, ignore_errors=True)
    return check_transcript(transcript, on_screen_text, context)


def check_link(url, context=""):
    video_path = download_video(url)
    try:
        return check_video(video_path, context)
    finally:
        Path(video_path).unlink(missing_ok=True)


if __name__ == "__main__":
    health_transcript = """Okay, three things nobody tells you about your body. First, you only use 10 percent of your brain, so imagine what you could do with the rest. Second, stop cracking your knuckles, it causes arthritis. Big pharma is hiding the fact that vitamin C cures the common cold, by the way. Isn't it crazy that the first carrots people farmed were purple? And you need eight glasses of water a day, minimum. Honestly, looking after yourself is the best investment you'll ever make."""

    pprint(check_transcript(health_transcript))