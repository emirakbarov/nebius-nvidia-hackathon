import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

EXCLUDED_DOMAINS = [
    "reddit.com", "quora.com", "facebook.com", "instagram.com", "tiktok.com",
    "pinterest.com", "youtube.com", "linkedin.com", "x.com", "twitter.com",
]
MAX_QUERY_LENGTH = 400

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def search_claim(claim, video_context=""):
    # The video's context is added to the query so the search finds the right event, place and time.
    query = f"{claim} {video_context}".strip()[:MAX_QUERY_LENGTH]
    response = tavily_client.search(
        query=query,
        search_depth="basic",
        exclude_domains=EXCLUDED_DOMAINS,
        max_results=5,
        chunks_per_source=3,
    )
    return response["results"]


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