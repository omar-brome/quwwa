"""YouTube search for exercise form videos.

Two providers behind one endpoint:
- With YOUTUBE_API_KEY configured: the official Data API v3 (reliable, quota'd).
- Without: parse ytInitialData from the public results page — zero-config, the
  same degrade-gracefully approach as the AI key. If YouTube changes markup the
  UI falls back to an external search link.

Results are cached in-process for a day; form videos don't go stale.
"""

import html
import json
import re
import time

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.schemas import VideoResult, VideoSearchOut

router = APIRouter(prefix="/videos", tags=["videos"])

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_CACHE_TTL = 24 * 3600
_CACHE_MAX = 256
_cache: dict[str, tuple[float, list[dict]]] = {}


def _thumb(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"


def parse_yt_initial_data(page_html: str, limit: int) -> list[dict]:
    """Pull videoRenderer entries out of the results page's embedded JSON."""
    match = re.search(r"var ytInitialData\s*=\s*(\{.*?\});</script>", page_html, re.DOTALL)
    if not match:
        raise ValueError("ytInitialData not found in results page")
    data = json.loads(match.group(1))
    sections = (
        data.get("contents", {})
        .get("twoColumnSearchResultsRenderer", {})
        .get("primaryContents", {})
        .get("sectionListRenderer", {})
        .get("contents", [])
    )
    items: list[dict] = []
    for section in sections:
        for entry in section.get("itemSectionRenderer", {}).get("contents", []):
            vr = entry.get("videoRenderer")
            if not vr or "videoId" not in vr:
                continue
            video_id = vr["videoId"]
            title = "".join(run.get("text", "") for run in vr.get("title", {}).get("runs", []))
            owner_runs = vr.get("ownerText", {}).get("runs", [])
            items.append(
                {
                    "video_id": video_id,
                    "title": title or "Untitled",
                    "channel": owner_runs[0].get("text") if owner_runs else None,
                    "duration": vr.get("lengthText", {}).get("simpleText"),
                    "thumbnail_url": _thumb(video_id),
                }
            )
            if len(items) >= limit:
                return items
    return items


async def _search_scrape(q: str, limit: int) -> list[dict]:
    async with httpx.AsyncClient(
        headers={"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"},
        cookies={"CONSENT": "YES+1"},
        timeout=10,
        follow_redirects=True,
    ) as client:
        resp = await client.get(
            "https://www.youtube.com/results",
            params={"search_query": q, "hl": "en"},
        )
        resp.raise_for_status()
    return parse_yt_initial_data(resp.text, limit)


async def _search_api(q: str, limit: int, api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "type": "video",
                "videoEmbeddable": "true",
                "maxResults": limit,
                "q": q,
                "key": api_key,
            },
        )
        resp.raise_for_status()
    return [
        {
            "video_id": item["id"]["videoId"],
            "title": html.unescape(item["snippet"]["title"]),
            "channel": item["snippet"].get("channelTitle"),
            "duration": None,  # not included in search responses
            "thumbnail_url": _thumb(item["id"]["videoId"]),
        }
        for item in resp.json().get("items", [])
        if item.get("id", {}).get("videoId")
    ]


async def _fetch(q: str, limit: int) -> tuple[list[dict], str]:
    api_key = get_settings().youtube_api_key
    if api_key:
        return await _search_api(q, limit, api_key), "api"
    return await _search_scrape(q, limit), "scrape"


@router.get("/search", response_model=VideoSearchOut)
async def search_videos(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=6, ge=1, le=12),
):
    key = f"{q.strip().lower()}|{limit}"
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        items = cached[1]
        return {"items": items, "source": "cache"}

    try:
        items, source = await _fetch(q.strip(), limit)
    except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(502, f"YouTube search failed: {exc}") from exc

    if len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (time.time(), items)
    return {"items": items, "source": source}
