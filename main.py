from pathlib import Path
from urllib.parse import quote
import re

import httpx
import uvicorn

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

STATIC_DIR.mkdir(exist_ok=True)


app = FastAPI(title="Game Music Dance")


app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


@app.get("/", response_class=HTMLResponse)
async def home():

    index_file = STATIC_DIR / "index.html"

    if not index_file.exists():
        return HTMLResponse(
            "<h1>Ошибка: static/index.html не найден</h1>",
            status_code=500
        )

    return HTMLResponse(
        index_file.read_text(encoding="utf-8")
    )


@app.get("/api/search")
async def search_music(
    q: str = Query(..., min_length=1, max_length=100)
):

    url = (
        "https://www.youtube.com/results"
        "?search_query=" + quote(q)
    )

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/150.0 Safari/537.36"
    }

    try:

        async with httpx.AsyncClient(
            headers=headers,
            timeout=20,
            follow_redirects=True
        ) as client:

            response = await client.get(url)
            response.raise_for_status()

            text = response.text

    except Exception as error:

        return {
            "success": False,
            "error": f"Ошибка соединения: {error}",
            "results": []
        }


    ids = re.findall(
        r'"videoId":"([A-Za-z0-9_-]{11})"',
        text
    )


    unique_ids = []

    for video_id in ids:

        if video_id not in unique_ids:
            unique_ids.append(video_id)


    unique_ids = unique_ids[:12]


    results = []

    for video_id in unique_ids:

        results.append({
            "id": video_id,

            "url":
            f"https://www.youtube.com/watch?v={video_id}",

            "thumbnail":
            f"https://i.ytimg.com/vi/"
            f"{video_id}/hqdefault.jpg"
        })


    return {
        "success": True,
        "query": q,
        "results": results
    }


if __name__ == "__main__":

    print()
    print("=" * 60)
    print("             🎵 GAME MUSIC DANCE")
    print("=" * 60)
    print()
    print("🌐 http://127.0.0.1:8000")
    print()
    print("🔎 YouTube поиск")
    print("🔊 Звук через браузер")
    print("🎮 Игровые персонажи")
    print("💃 Танцы")
    print()
    print("=" * 60)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )