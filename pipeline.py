import json
import os
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI
from transcribe import video_to_wav, transcribe, download_video
from evidence import find_evidence, format_evidence
from pathlib import Path
from pprint import pprint

load_dotenv()

VERDICT_PROMPT = Path("prompts/verdict.md").read_text(encoding="utf-8")
EXTRACTOR_PROMPT = Path("prompts/extractor.md").read_text(encoding="utf-8")

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key = os.environ["NEBIUS_API_KEY"]
)

def check_transcript(transcript):
    today = date.today()
    claim_extractor = client.chat.completions.create(
        model = "nvidia/nemotron-3-super-120b-a12b",
        messages = [
            {
                "role": "system",
                "content": EXTRACTOR_PROMPT
            },
            {
                "role": "user",
                "content": transcript
            }
        ]
    )

    lines = claim_extractor.choices[0].message.content.split("\n")

    claims = []

    for claim in lines:
        cleaned = claim.strip()
        if cleaned:
            claims.append(cleaned)

    pprint(claims)

    evidence = find_evidence(claims)

    verdicts = []

    for claim, results in evidence.items():
        evidence_text = format_evidence(results)
        user_message = f"""
        
        Today's date is {today}.

        Claim:\n{claim}\n\nEvidence:\n{evidence_text}"""

        response = client.chat.completions.create(
            model = "nvidia/nemotron-3-super-120b-a12b",
            response_format={"type": "json_object"},
            messages = [ 
                {
                    "role": "system",
                    "content": VERDICT_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        content = response.choices[0].message.content

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {"verdict": "Error", "sources": [], "explanation": content}

        result["claim"] = claim

        result["source_details"] = [
            results[n - 1]
            for n in result.get("sources", [])
            if isinstance(n, int) and 1 <= n <= len(results)
        ]

        verdicts.append(result)

    pprint(verdicts)
    return verdicts

def check_video(video_path):
    try:
        transcript = transcribe(video_to_wav(video_path))
    finally:
        Path("audio.wav").unlink(missing_ok = True)    
        Path("download.mp4").unlink(missing_ok = True)    
    return check_transcript(transcript)

def check_link(url):
    video_path = download_video(url)
    try: 
        return check_video(video_path)
    finally:
        Path("audio.wav").unlink(missing_ok = True)
        Path("download.mp4").unlink(missing_ok = True)    

if __name__ == "__main__":
    health_transcript = """

        Okay, three things nobody tells you about your body. First, you only use 10 percent of your brain, so imagine what you could do with the rest. Second, stop cracking your knuckles, it causes arthritis. Big pharma is hiding the fact that vitamin C cures the common cold, by the way. Isn't it crazy that the first carrots people farmed were purple? And you need eight glasses of water a day, minimum. Honestly, looking after yourself is the best investment you'll ever make.

    """

    space_transcript = """

        Space facts that'll blow your mind. The Great Wall of China is the only man-made structure you can see from space. Light from the Sun takes about eight minutes to reach us. Venus is the hottest planet in the solar system, even though Mercury is closer to the Sun. And a day on Venus is longer than its whole year. We'll have people living on Mars within ten years, mark my words.

    """

    history_transcript = """ History class lied to you. Napoleon was tiny, like five foot two. Vikings wore horned helmets into battle, that's why they were so terrifying. The Titanic sank in 1912 on its very first voyage. And get this: Cleopatra lived closer in time to the Moon landing than to the building of the Great Pyramid. History is way more interesting than school makes it."""
    
    check_transcript(health_transcript) 