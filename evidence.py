from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

# for tomorrow: https://www.instagram.com/reels/DYcARZXt8ly/

EXCLUDED_DOMAINS= ["reddit.com", "quora.com", "facebook.com", "instagram.com", "tiktok.com", "pinterest.com", "youtube.com"]

tavily_client = TavilyClient(api_key=os.environ['TAVILY_API_KEY'])

def find_evidence(claims):
    evidence = {}
    for claim in claims:
        response = tavily_client.search(
            query=claim,
            search_depth="basic",
            exclude_domains= EXCLUDED_DOMAINS,
            max_results=5,
            chunks_per_source=3
        )
        evidence[claim] = response["results"]

    return evidence

def format_evidence(results):
    if not results:
        return "No sources were found for this claim."

    sources = []
    for i, result in enumerate(results, start=1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "").strip()
        date = result.get("published_date")

        source = f"[{i}] {title}\nURL: {url}\n"
        if date:
            source += f"Published: {date}\n"
        source += f"Content: {content}"
        sources.append(source)

    return "\n\n".join(sources)
    