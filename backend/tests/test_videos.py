import json

from app.routers import videos
from app.routers.videos import parse_yt_initial_data


def _results_page(video_ids: list[str]) -> str:
    contents = [
        {
            "itemSectionRenderer": {
                "contents": [
                    {"shelfRenderer": {"title": "ignored shelf"}},
                    *[
                        {
                            "videoRenderer": {
                                "videoId": vid,
                                "title": {"runs": [{"text": f"How to {vid}"}]},
                                "ownerText": {"runs": [{"text": "Coach Channel"}]},
                                "lengthText": {"simpleText": "8:24"},
                            }
                        }
                        for vid in video_ids
                    ],
                ]
            }
        }
    ]
    data = {
        "contents": {
            "twoColumnSearchResultsRenderer": {
                "primaryContents": {"sectionListRenderer": {"contents": contents}}
            }
        }
    }
    return f"<html><script>var ytInitialData = {json.dumps(data)};</script></html>"


def test_parse_yt_initial_data():
    items = parse_yt_initial_data(_results_page(["abc123", "def456", "ghi789"]), limit=2)
    assert len(items) == 2
    assert items[0] == {
        "video_id": "abc123",
        "title": "How to abc123",
        "channel": "Coach Channel",
        "duration": "8:24",
        "thumbnail_url": "https://i.ytimg.com/vi/abc123/mqdefault.jpg",
    }


def test_parse_rejects_pages_without_data():
    import pytest

    with pytest.raises(ValueError):
        parse_yt_initial_data("<html>nothing here</html>", limit=5)


async def test_search_endpoint_caches(client, monkeypatch):
    calls = []

    async def fake_fetch(q, limit):
        calls.append(q)
        return (
            [
                {
                    "video_id": "vid1",
                    "title": "Barbell Row Form Guide",
                    "channel": "Coach",
                    "duration": "6:01",
                    "thumbnail_url": "https://i.ytimg.com/vi/vid1/mqdefault.jpg",
                }
            ],
            "scrape",
        )

    monkeypatch.setattr(videos, "_fetch", fake_fetch)
    videos._cache.clear()

    first = await client.get("/api/videos/search", params={"q": "barbell row form"})
    assert first.status_code == 200
    body = first.json()
    assert body["source"] == "scrape"
    assert body["items"][0]["video_id"] == "vid1"

    second = await client.get("/api/videos/search", params={"q": "Barbell Row Form"})
    assert second.json()["source"] == "cache"
    assert len(calls) == 1  # case-insensitive cache hit

    await client.get("/api/videos/search", params={"q": "front squat form"})
    assert len(calls) == 2

    too_short = await client.get("/api/videos/search", params={"q": "x"})
    assert too_short.status_code == 422
