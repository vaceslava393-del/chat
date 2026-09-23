from pathlib import Path
from urllib.parse import quote_plus

import uvicorn
import httpx

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


# ============================================================
# НАСТРОЙКИ
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
CHARACTERS_DIR = STATIC_DIR / "characters"

STATIC_DIR.mkdir(exist_ok=True)
CHARACTERS_DIR.mkdir(exist_ok=True)


app = FastAPI(
    title="Game Music Dance",
    version="4.0"
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
            <h1>❌ Ошибка</h1>
            <p>Файл static/index.html не найден.</p>
            """,
            status_code=500
        )

    try:

        html = index_file.read_text(
            encoding="utf-8"
        )

        return HTMLResponse(
            content=html,
            status_code=200
        )

    except Exception as error:

        return HTMLResponse(
            f"""
            <h1>❌ Ошибка чтения index.html</h1>
            <p>{error}</p>
            """,
            status_code=500
        )


# ============================================================
# GOOGLE ПОИСК МУЗЫКИ
# ============================================================

    url = "https://api.deezer.com/search"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params={
                "q": q,
                "limit": 10
            }
        )

    data = response.json()

    results = []

    for item in data.get("data", []):

        results.append({
            "title": item["title"],
            "artist": item["artist"]["name"],
            "cover": item["album"]["cover_medium"],
            "preview": item["preview"]
        })

    return {
        "success": True,
        "results": results
    }


# ============================================================
# ОТКРЫТИЕ САЙТА
# ============================================================

@app.get("/api/open-site")
async def open_site(
    url: str = Query(
        ...,
        min_length=1,
        max_length=500
    )
):

    url = url.strip()

    if not url:

        return {
            "success": False,
            "error": "Введите адрес сайта."
        }

    # Если пользователь написал:
    # google.com
    # автоматически добавляем https://

    if not url.startswith(
        ("http://", "https://")
    ):

        url = "https://" + url

    # Разрешаем только обычные HTTP/HTTPS сайты
    if not url.startswith(
        ("http://", "https://")
    ):

        return {
            "success": False,
            "error": "Разрешены только HTTP и HTTPS сайты."
        }

    return {
        "success": True,
        "url": url
    }


# ============================================================
# ПЕРСОНАЖИ
# ============================================================

CHARACTERS = [

    {
        "id": "mario",
        "name": "Mario",
        "game": "Super Mario",
        "image": "/static/characters/mario.png",
        "description":
            "Главный герой серии Super Mario.",
        "role":
            "Главный герой",

        "characteristics": {
            "Сила": 85,
            "Скорость": 80,
            "Прыжок": 95,
            "Выносливость": 85,
            "Ловкость": 90
        }
    },

    {
        "id": "sonic",
        "name": "Sonic",
        "game": "Sonic the Hedgehog",
        "image": "/static/characters/sonic.png",
        "description":
            "Синий ёж, известный своей невероятной скоростью.",
        "role":
            "Главный герой",

        "characteristics": {
            "Сила": 75,
            "Скорость": 100,
            "Прыжок": 90,
            "Выносливость": 90,
            "Ловкость": 100
        }
    },

    {
        "id": "pacman",
        "name": "Pac-Man",
        "game": "Pac-Man",
        "image": "/static/characters/pacman.png",
        "description":
            "Легендарный персонаж аркадной игры Pac-Man.",
        "role":
            "Главный герой",

        "characteristics": {
            "Сила": 60,
            "Скорость": 85,
            "Прыжок": 20,
            "Выносливость": 95,
            "Ловкость": 90
        }
    },

    {
        "id": "player",
        "name": "Player",
        "game": "Fortnite",
        "image": "/static/characters/player.png",
        "description":
            "Игровой персонаж Fortnite.",
        "role":
            "Герой",

        "characteristics": {
            "Сила": 90,
            "Скорость": 75,
            "Прыжок": 70,
            "Выносливость": 90,
            "Ловкость": 85
        }
    },

    {
        "id": "noob",
        "name": "Noob",
        "game": "Roblox",
        "image": "/static/characters/noob.png",
        "description":
            "Персонаж Roblox.",
        "role":
            "Главный герой",

        "characteristics": {
            "Сила": 80,
            "Скорость": 70,
            "Прыжок": 95,
            "Выносливость": 90,
            "Ловкость": 85
        }
    },

    {
        "id": "steve",
        "name": "Steve",
        "game": "Minecraft",
        "image": "/static/characters/steve.png",
        "description":
            "Персонаж Minecraft, исследователь и строитель.",
        "role":
            "Игрок",

        "characteristics": {
            "Сила": 85,
            "Скорость": 70,
            "Прыжок": 60,
            "Выносливость": 95,
            "Ловкость": 70
        }
    }
]


# ============================================================
# API ПЕРСОНАЖЕЙ
# ============================================================

@app.get("/api/characters")
async def get_characters():

    return {
        "success": True,
        "count": len(CHARACTERS),
        "characters": CHARACTERS
    }


@app.get("/api/characters/{character_id}")
async def get_character(
    character_id: str
):

    character_id = character_id.strip().lower()

    for character in CHARACTERS:

        if character["id"] == character_id:

            return {
                "success": True,
                "character": character
            }

    return {
        "success": False,
        "error": "Персонаж не найден",
        "character": None
    }


# ============================================================
# STATUS
# ============================================================

@app.get("/api/status")
async def status():

    return {
        "success": True,
        "app": "Game Music Dance",
        "version": "4.0",
        "music_search": "Google",
        "characters": len(CHARACTERS)
    }


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("           🎮 GAME MUSIC DANCE")
    print("=" * 60)

    print("🔎 Поиск музыки: Google")
    print("🌐 Открытие сайтов: включено")
    print("🎮 Персонажи:", len(CHARACTERS))
    print("🌐 Сервер:")
    print("http://127.0.0.1:8000")

    print("=" * 60)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False
    )