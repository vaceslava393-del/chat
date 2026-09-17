from pathlib import Path
from urllib.parse import quote

import httpx
import uvicorn

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

STATIC_DIR.mkdir(exist_ok=True)


app = FastAPI(
    title="Game Music Dance"
)


app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# ============================================================
# ГЛАВНАЯ СТРАНИЦА
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home():

    index_file = STATIC_DIR / "index.html"

    if not index_file.exists():

        return HTMLResponse(
            """
            <h1>Ошибка</h1>
            <p>Файл static/index.html не найден.</p>
            """,
            status_code=500
        )

    return HTMLResponse(
        index_file.read_text(
            encoding="utf-8"
        )
    )


# ============================================================
# ПОИСК YOUTUBE
# ============================================================

@app.get("/api/search")
async def search_music(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100
    )
):

    query = quote(q)

    url = (
        "https://www.youtube.com/results"
        f"?search_query={query}"
    )

    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/150.0 Safari/537.36"
    }

    try:

        async with httpx.AsyncClient(
            headers=headers,
            timeout=15,
            follow_redirects=True
        ) as client:

            response = await client.get(url)

            response.raise_for_status()

            text = response.text

    except Exception as error:

        return {
            "success": False,
            "error": str(error),
            "results": []
        }


    # --------------------------------------------------------
    # Ищем videoId в ответе YouTube
    # --------------------------------------------------------

    import re

    pattern = r'"videoId":"([A-Za-z0-9_-]{11})"'

    ids = re.findall(
        pattern,
        text
    )


    # Убираем повторения
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

            "embed":
                f"https://www.youtube.com/embed/{video_id}",

            "thumbnail":
                f"https://i.ytimg.com/vi/"
                f"{video_id}/hqdefault.jpg"

        })


    return {
        "success": True,
        "query": q,
        "results": results
    }


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("             🎵 GAME MUSIC DANCE")
    print("=" * 60)
    print()
    print("🌐 Сайт:")
    print("http://127.0.0.1:8000")
    print()
    print("🔎 Поиск музыки через YouTube")
    print("🎮 Игровые персонажи")
    print("💃 Танцы под музыку")
    print()
    print("=" * 60)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )