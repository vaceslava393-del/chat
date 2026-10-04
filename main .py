from pathlib import Path
from urllib.parse import quote_plus

import httpx
import uvicorn

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
CHARACTERS_DIR = STATIC_DIR / "characters"

print("=" * 60)
print("🎵 GAME MUSIC DANCE")
print("=" * 60)

print("BASE_DIR:", BASE_DIR)
print("STATIC_DIR:", STATIC_DIR)
print("CHARACTERS_DIR:", CHARACTERS_DIR)
print("Characters существует:", CHARACTERS_DIR.exists())


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Game Music Dance",
    version="3.0"
)


# ============================================================
# STATIC
# ============================================================

if STATIC_DIR.exists():

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static"
    )

    print("✅ Static подключён:", STATIC_DIR)

else:

    print("⚠️ Папка static не найдена!")
    print("Создай папку:", STATIC_DIR)


# ============================================================
# CHARACTERS / GAMES
# ============================================================

CHARACTERS = [

    {
        "id": "spiderman",
        "name": "Человек-паук",
        "image": "/static/characters/spiderman.png",
        "game": "Marvel's Spider-Man Remastered",
        "launch_url": "steam://run/1817070",
        "store_url": "https://store.steampowered.com/app/1817070/",
        "type": "steam",
        "role": "Супергерой",
        "description": "Человек-паук — герой Marvel, который защищает Нью-Йорк.",
        "stats": {
            "Сила": 95,
            "Скорость": 100,
            "Прыжок": 100,
            "Боевые навыки": 90
        }
    },

    {
        "id": "skyline",
        "name": "Nissan Skyline",
        "image": "/static/characters/skyline.png",
        "game": "Car Mechanic Simulator 2021",
        "launch_url": "steam://run/1190000",
        "store_url": "https://store.steampowered.com/app/1190000/",
        "type": "steam",
        "role": "Гоночный автомобиль",
        "description": "Nissan Skyline — легендарный японский автомобиль.",
        "stats": {
            "Скорость": 98,
            "Мощность": 95,
            "Дрифт": 100,
            "Стиль": 100
        }
    },

    {
        "id": "mickey",
        "name": "Mickey Mouse",
        "image": "/static/characters/mickey.png",
        "game": "Disney Epic Mickey: Rebrushed",
        "launch_url": "steam://run/1522160",
        "store_url": "https://store.steampowered.com/app/1522160/",
        "type": "steam",
        "role": "Герой Disney",
        "description": "Микки Маус отправляется в невероятное приключение.",
        "stats": {
            "Смелость": 90,
            "Скорость": 85,
            "Удача": 100,
            "Харизма": 100
        }
    },

    {
        "id": "noob",
        "name": "Noob",
        "image": "/static/characters/noob.png",
        "game": "Terraria",
        "launch_url": "steam://run/105600",
        "store_url": "https://store.steampowered.com/app/105600/",
        "type": "steam",
        "role": "Исследователь",
        "description": "Noob отправляется исследовать огромный мир Terraria.",
        "stats": {
            "Исследование": 95,
            "Крафт": 100,
            "Бой": 80,
            "Выживание": 90
        }
    },


{
    "id": "steve",
    "name": "Steve",
    "image": "/static/characters/steve.png",

    "game": "Minecraft",

    "launch_url": "https://tlauncher.org/",
    "store_url": "https://tlauncher.org/",

    "type": "tlauncher",

    "role": "Строитель",

    "description": "Steve — главный герой Minecraft.",

    "stats": {
        "Строительство": 100,
        "Добыча": 100,
        "Выживание": 95,
        "Крафт": 100
    }
},



]


# ============================================================
# HTML PAGE
# ============================================================

HTML_PAGE = r"""
<!DOCTYPE html>

<html lang="ru">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Game Music Dance</title>

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    min-height: 100vh;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background:
        radial-gradient(
            circle at top,
            #26324d 0%,
            #111522 45%,
            #080a10 100%
        );

    color: white;

}


/* ============================================================
   HEADER
   ============================================================ */

header {

    padding: 25px 20px;

    text-align: center;

    background:
        rgba(0, 0, 0, 0.35);

    border-bottom:
        1px solid rgba(255,255,255,0.1);

}

header h1 {

    margin: 0;

    font-size: 38px;

}

header p {

    margin: 10px 0 0;

    color: #b9c2d0;

}


/* ============================================================
   CONTAINER
   ============================================================ */

.container {

    width: min(1200px, 94%);

    margin: 30px auto;

}


/* ============================================================
   MUSIC
   ============================================================ */

.music-box {

    background:
        rgba(255,255,255,0.06);

    border:
        1px solid rgba(255,255,255,0.1);

    border-radius: 20px;

    padding: 22px;

    margin-bottom: 30px;

    box-shadow:
        0 15px 50px rgba(0,0,0,0.25);

}

.music-box h2 {

    margin-top: 0;

}

.search-row {

    display: flex;

    gap: 10px;

}

.search-row input {

    flex: 1;

    padding: 14px 16px;

    border-radius: 12px;

    border: none;

    outline: none;

    background: #202738;

    color: white;

    font-size: 16px;

}

button {

    border: none;

    border-radius: 12px;

    padding: 12px 18px;

    cursor: pointer;

    font-weight: bold;

    transition: 0.2s;

}

button:hover {

    transform: translateY(-2px);

}

.search-button {

    background: #5865f2;

    color: white;

}


/* ============================================================
   MUSIC RESULTS
   ============================================================ */

.music-results {

    margin-top: 20px;

}

.track {

    display: flex;

    align-items: center;

    gap: 15px;

    padding: 12px;

    margin-top: 10px;

    background: rgba(255,255,255,0.05);

    border-radius: 14px;

}

.track img {

    width: 60px;

    height: 60px;

    border-radius: 10px;

    object-fit: cover;

}

.track-info {

    flex: 1;

}

.track-title {

    font-weight: bold;

}

.track-artist {

    color: #aeb7c8;

    margin-top: 5px;

}

.play-button {

    background: #23c483;

    color: white;

}


/* ============================================================
   CHARACTERS
   ============================================================ */

.section-title {

    margin-bottom: 18px;

}

.characters {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(200px, 1fr)
        );

    gap: 20px;

}

.character {

    background:
        linear-gradient(
            180deg,
            rgba(255,255,255,0.09),
            rgba(255,255,255,0.035)
        );

    border:
        1px solid rgba(255,255,255,0.1);

    border-radius: 20px;

    padding: 15px;

    cursor: pointer;

    transition:
        transform 0.25s,
        box-shadow 0.25s;

}

.character:hover {

    transform:
        translateY(-8px)
        scale(1.02);

    box-shadow:
        0 20px 50px rgba(0,0,0,0.35);

}

.character-image {

    width: 100%;

    height: 230px;

    object-fit: contain;

    border-radius: 15px;

    background:
        rgba(0,0,0,0.25);

}

.character-name {

    font-size: 20px;

    font-weight: bold;

    margin-top: 12px;

}

.character-game {

    color: #aeb7c8;

    margin-top: 6px;

}

.open-character-button {

    width: 100%;

    margin-top: 12px;

    background: #5865f2;

    color: white;

}


/* ============================================================
   DANCE
   ============================================================ */

.dancing {

    animation:
        dance 0.55s infinite alternate ease-in-out;

}

@keyframes dance {

    from {

        transform:
            translateY(0)
            rotate(-3deg);

    }

    to {

        transform:
            translateY(-12px)
            rotate(3deg);

    }

}


/* ============================================================
   MODAL
   ============================================================ */

.modal {

    position: fixed;

    inset: 0;

    display: none;

    align-items: center;

    justify-content: center;

    padding: 20px;

    background:
        rgba(0,0,0,0.78);

    z-index: 1000;

}

.modal.active {

    display: flex;

}

.modal-box {

    width: min(700px, 100%);

    max-height: 90vh;

    overflow-y: auto;

    background:
        #171c29;

    border:
        1px solid rgba(255,255,255,0.1);

    border-radius: 24px;

    padding: 25px;

    position: relative;

}

.close {

    position: absolute;

    right: 15px;

    top: 15px;

    width: 40px;

    height: 40px;

    border-radius: 50%;

    background: #292f40;

    color: white;

    font-size: 22px;

}

.modal-image {

    width: 100%;

    height: 300px;

    object-fit: contain;

    border-radius: 18px;

    background: rgba(0,0,0,0.25);

}

.modal h2 {

    font-size: 30px;

    margin-bottom: 5px;

}

.modal-game {

    color: #8f9bb0;

    margin-bottom: 20px;

}

.description {

    color: #d6dbe5;

    line-height: 1.6;

}

.stats {

    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 10px;

    margin-top: 20px;

}

.stat {

    background: #202638;

    padding: 12px;

    border-radius: 12px;

}

.stat-name {

    color: #aab4c7;

}

.stat-value {

    font-weight: bold;

    margin-top: 5px;

}

.modal-buttons {

    display: flex;

    flex-wrap: wrap;

    gap: 10px;

    margin-top: 25px;

}

.play-game {

    background: #23c483;

    color: white;

}

.steam-button {

    background: #315b9b;

    color: white;

}

.dance-button {

    background: #e84393;

    color: white;

}


/* ============================================================
   FOOTER
   ============================================================ */

footer {

    text-align: center;

    padding: 30px;

    color: #7f899d;

}


/* ============================================================
   MOBILE
   ============================================================ */

@media (max-width: 600px) {

    header h1 {

        font-size: 28px;

    }

    .search-row {

        flex-direction: column;

    }

    .character-image {

        height: 200px;

    }

    .stats {

        grid-template-columns: 1fr;

    }

}

</style>

</head>


<body>


<header>

    <h1>🎵 Game Music Dance</h1>

    <p>
        🎮 Игры • 🎵 Музыка • 💃 Танцы
    </p>

</header>


<div class="container">


    <!-- ======================================================
         MUSIC
         ====================================================== -->

    <section class="music-box">

        <h2>🎵 Музыкальный поиск</h2>

        <div class="search-row">

            <input
                id="musicSearch"
                type="text"
                placeholder="Например: Alan Walker"
                onkeydown="
                    if(event.key === 'Enter')
                        searchMusic();
                "
            >

            <button
                class="search-button"
                onclick="searchMusic()"
            >
                🔎 Найти
            </button>

        </div>

        <div
            id="musicResults"
            class="music-results"
        ></div>

    </section>


    <!-- ======================================================
         CHARACTERS
         ====================================================== -->

    <h2 class="section-title">
        🎮 Выбери игру
    </h2>

    <div
        id="characters"
        class="characters"
    >

        <p>Загрузка персонажей...</p>

    </div>


</div>


<footer>

    Game Music Dance 🎵🎮

</footer>


<!-- ============================================================
     MODAL
     ============================================================ -->

<div
    id="modal"
    class="modal"
    onclick="
        if(event.target === this)
            closeModal();
    "
>

    <div class="modal-box">

        <button
            class="close"
            onclick="closeModal()"
        >
            ×
        </button>

        <div id="modalContent"></div>

    </div>

</div>


<script>


// ============================================================
// GLOBAL
// ============================================================

let characters = [];

let currentCharacter = null;

let currentAudio = null;


// ============================================================
// LOAD CHARACTERS
// ============================================================

async function loadCharacters() {

    const container =
        document.getElementById("characters");

    try {

        const response =
            await fetch("/api/characters");

        const data =
            await response.json();

        if (!data.success) {

            throw new Error(
                "Не удалось загрузить персонажей"
            );

        }

        characters =
            data.characters || [];

        renderCharacters();

    }

    catch(error) {

        console.error(error);

        container.innerHTML = `
            <p style="color:#ff6b6b">
                ❌ Ошибка загрузки персонажей
            </p>
        `;

    }

}


// ============================================================
// RENDER CHARACTERS
// ============================================================

function renderCharacters() {

    const container =
        document.getElementById("characters");

    container.innerHTML = "";

    characters.forEach(character => {

        const card =
            document.createElement("div");

        card.className =
            "character";

        card.onclick = () => {

            showCharacter(character.id);

        };


        card.innerHTML = `

            <img
                class="character-image"
                src="${character.image}"
                alt="${escapeHtml(character.name)}"
                onerror="
                    this.style.display='none';
                    this.parentElement.querySelector('.image-error').style.display='block';
                "
            >

            <div
                class="image-error"
                style="
                    display:none;
                    height:230px;
                    border-radius:15px;
                    background:#202638;
                    align-items:center;
                    justify-content:center;
                    text-align:center;
                    padding:20px;
                "
            >
                ❌ Картинка не найдена

                <br><br>

                <small>
                    ${character.image}
                </small>
            </div>

            <div class="character-name">
                ${escapeHtml(character.name)}
            </div>

            <div class="character-game">
                🎮 ${escapeHtml(character.game)}
            </div>

            <button
                class="open-character-button"
                onclick="
                    event.stopPropagation();
                    showCharacter('${character.id}');
                "
            >
                👤 Подробнее
            </button>

        `;

        container.appendChild(card);

    });

}


// ============================================================
// SHOW CHARACTER
// ============================================================

function showCharacter(id) {

    const character =
        characters.find(
            item => item.id === id
        );

    if (!character) {

        alert("Персонаж не найден");

        return;

    }

    currentCharacter =
        character;


    const stats =
        character.stats || {};


    let statsHtml = "";

    for (
        const [name, value]
        of Object.entries(stats)
    ) {

        statsHtml += `

            <div class="stat">

                <div class="stat-name">
                    ${escapeHtml(name)}
                </div>

                <div class="stat-value">
                    ${value}/100
                </div>

            </div>

        `;

    }


    document.getElementById(
        "modalContent"
    ).innerHTML = `

        <img
            class="modal-image"
            src="${character.image}"
            alt="${escapeHtml(character.name)}"
        >

        <h2>
            ${escapeHtml(character.name)}
        </h2>

        <div class="modal-game">
            🎮 ${escapeHtml(character.game)}
        </div>

        <p>
            <b>Роль:</b>
            ${escapeHtml(character.role || "")}
        </p>

        <p class="description">
            ${escapeHtml(character.description || "")}
        </p>

        <div class="stats">
            ${statsHtml}
        </div>

        <div class="modal-buttons">

            <button
                class="play-game"
                onclick="launchGame()"
            >
                🎮 ИГРАТЬ
            </button>

            <button
                class="steam-button"
                onclick="openStore()"
            >
                🛒 МАГАЗИН
            </button>

            <button
                class="dance-button"
                onclick="startDance()"
            >
                💃 ТАНЦЕВАТЬ
            </button>

        </div>

    `;


    document
        .getElementById("modal")
        .classList.add("active");

}


// ============================================================
// CLOSE MODAL
// ============================================================

function closeModal() {

    document
        .getElementById("modal")
        .classList.remove("active");

}



// ============================================================
// LAUNCH GAME
// ============================================================

function launchGame() {

    if (!currentCharacter) {
        return;
    }

    const character = currentCharacter;


    // ========================================================
    // STEAM
    // ========================================================

    if (character.type === "steam") {

        window.location.href =
            character.launch_url;

        return;
    }


    // ========================================================
    // TLAUNCHER
    // ========================================================

    if (character.type === "tlauncher") {

        window.open(
            character.launch_url,
            "_blank"
        );

        return;
    }


    // ========================================================
    // MINECRAFT
    // ========================================================

    if (character.type === "minecraft") {

        window.open(
            character.launch_url,
            "_blank"
        );

        return;
    }


    // ========================================================
    // OTHER
    // ========================================================

    if (character.launch_url) {

        window.open(
            character.launch_url,
            "_blank"
        );

    }

}




// ============================================================
// OPEN STORE
// ============================================================

function openStore() {

    if (!currentCharacter) {

        return;

    }

    window.open(
        currentCharacter.store_url,
        "_blank"
    );

}


// ============================================================
// DANCE
// ============================================================

function startDance() {

    if (!currentCharacter) {

        return;

    }


    const images =
        document.querySelectorAll(
            ".character-image"
        );


    images.forEach(image => {

        image.classList.add(
            "dancing"
        );

    });


    setTimeout(() => {

        images.forEach(image => {

            image.classList.remove(
                "dancing"
            );

        });

    }, 5000);

}


// ============================================================
// MUSIC SEARCH
// ============================================================

async function searchMusic() {

    const input =
        document.getElementById(
            "musicSearch"
        );

    const results =
        document.getElementById(
            "musicResults"
        );


    const query =
        input.value.trim();


    if (!query) {

        results.innerHTML =
            "<p>Введите название музыки.</p>";

        return;

    }


    results.innerHTML =
        "<p>🔎 Ищу музыку...</p>";


    try {

        const response =
            await fetch(
                "/api/music?q=" +
                encodeURIComponent(query)
            );


        const data =
            await response.json();


        if (
            !data.success ||
            !data.tracks ||
            data.tracks.length === 0
        ) {

            results.innerHTML =
                "<p>❌ Ничего не найдено.</p>";

            return;

        }


        results.innerHTML = "";


        data.tracks.forEach(track => {

            const item =
                document.createElement("div");

            item.className =
                "track";


            item.innerHTML = `

                ${
                    track.cover
                    ?
                    `<img
                        src="${track.cover}"
                        alt=""
                    >`
                    :
                    ""
                }

                <div class="track-info">

                    <div class="track-title">
                        ${escapeHtml(track.title)}
                    </div>

                    <div class="track-artist">
                        ${escapeHtml(track.artist)}
                    </div>

                </div>

                ${
                    track.audio
                    ?
                    `<button
                        class="play-button"
                        onclick="
                            playMusic(
                                '${escapeJs(track.audio)}',
                                this
                            )
                        "
                    >
                        ▶
                    </button>`
                    :
                    ""
                }

            `;


            results.appendChild(item);

        });

    }

    catch(error) {

        console.error(error);

        results.innerHTML = `
            <p style="color:#ff6b6b">
                ❌ Ошибка поиска музыки
            </p>
        `;

    }

}


// ============================================================
// PLAY MUSIC
// ============================================================

function playMusic(url, button) {

    try {

        if (currentAudio) {

            currentAudio.pause();

            currentAudio = null;

        }


        currentAudio =
            new Audio(url);


        currentAudio.play()
            .then(() => {

                document
                    .querySelectorAll(".play-button")
                    .forEach(btn => {
                        btn.textContent = "▶";
                    });

                button.textContent = "⏸";

            })
            .catch(error => {

                console.error(error);

                alert(
                    "Не удалось воспроизвести трек."
                );

            });


        currentAudio.onended = () => {

            button.textContent = "▶";

        };

    }

    catch(error) {

        console.error(error);

    }

}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


// ============================================================
// ESCAPE JS
// ============================================================

function escapeJs(value) {

    return String(value)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"');

}


// ============================================================
// START
// ============================================================

loadCharacters();

</script>

</body>

</html>
"""


# ============================================================
# MAIN PAGE
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index():

    return HTMLResponse(
        content=HTML_PAGE
    )


# ============================================================
# CHARACTERS API
# ============================================================

@app.get("/api/characters")
async def get_characters():

    return {
        "success": True,
        "count": len(CHARACTERS),
        "characters": CHARACTERS
    }


# ============================================================
# GET ONE CHARACTER
# ============================================================

@app.get("/api/characters/{character_id}")
async def get_character(character_id: str):

    for character in CHARACTERS:

        if character["id"] == character_id:

            return {
                "success": True,
                "character": character
            }

    return JSONResponse(
        {
            "success": False,
            "error": "Персонаж не найден"
        },
        status_code=404
    )


# ============================================================
# LAUNCH GAME
# ============================================================

@app.get("/api/launch/{character_id}")
async def launch_game(character_id: str):

    for character in CHARACTERS:

        if character["id"] == character_id:

            return {
                "success": True,
                "character": character["name"],
                "game": character["game"],
                "type": character["type"],
                "launch_url": character["launch_url"],
                "store_url": character["store_url"]
            }

    return JSONResponse(
        {
            "success": False,
            "error": "Игра для персонажа не найдена"
        },
        status_code=404
    )


# ============================================================
# MUSIC SEARCH
# ============================================================

@app.get("/api/music")
async def search_music(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200
    )
):

    query = q.strip()

    if not query:

        return JSONResponse(
            {
                "success": False,
                "error": "Пустой запрос"
            },
            status_code=400
        )


    print()
    print("🎵 Поиск музыки:", query)


    url = "https://api.deezer.com/search/track"

    params = {
        "q": query,
        "limit": 20
    }


    try:

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True
        ) as client:

            response = await client.get(
                url,
                params=params
            )


        print(
            "Deezer status:",
            response.status_code
        )


        if response.status_code != 200:

            return JSONResponse(
                {
                    "success": False,
                    "error": "Deezer вернул ошибку",
                    "status": response.status_code
                },
                status_code=502
            )


        data = response.json()

        deezer_tracks =data.get("data", [])


        tracks = []


        for item in deezer_tracks:

            artist = item.get("artist") or {}

            album =item.get("album") or {}


            tracks.append({

                "id":
                    item.get("id"),

                "title":
                    item.get(
                        "title",
                        "Без названия"
                    ),

                "artist":
                    artist.get(
                        "name",
                        "Неизвестный исполнитель"
                    ),

                "album":
                    album.get(
                        "title",
                        ""
                    ),

                "cover":
                    (
                        album.get("cover_big")
                        or
                        album.get("cover_medium")
                        or
                        ""
                    ),

                "audio":
                    item.get(
                        "preview",
                        ""
                    ),

                "link":
                    item.get(
                        "link",
                        ""
                    ),

                "duration":
                    item.get(
                        "duration",
                        0
                    )

            })


        print(
            "🎵 Найдено треков:",
            len(tracks)
        )


        return {
            "success": True,
            "query": query,
            "count": len(tracks),
            "tracks": tracks
        }


    except httpx.TimeoutException:

        print(
            "❌ Тайм-аут Deezer"
        )

        return JSONResponse(
            {
                "success": False,
                "error":
                    "Deezer слишком долго отвечает"
            },
            status_code=504
        )


    except httpx.HTTPError as e:

        print(
            "❌ HTTP ошибка Deezer:",
            e
        )

        return JSONResponse(
            {
                "success": False,
                "error":
                    "Ошибка при обращении к Deezer"
            },
            status_code=502
        )


    except Exception as e:

        print(
            "❌ Ошибка:",
            e
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(e)
            },
            status_code=500
        )


# ============================================================
# OLD SEARCH API
# ============================================================

@app.get("/api/search")
async def old_search(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200
    )
):

    query = q.strip()

    if not query:

        return JSONResponse(
            {
                "success": False,
                "error": "Пустой запрос"
            },
            status_code=400
        )


    return {

        "success": True,

        "query": query,

        "google_url":
            "https://www.google.com/search?q="
            + quote_plus(
                query + " music"
            )

    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
async def health():

    return {

        "success": True,

        "status": "online",

        "message":
            "Game Music Dance работает!"

    }


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    import threading
    import time
    import webbrowser


    HOST = "127.0.0.1"

    PORT = 9012

    URL = f"http://{HOST}:{PORT}"


    print()
    print("=" * 60)
    print("🚀 GAME MUSIC DANCE")
    print("=" * 60)

    print("🌐 Адрес:", URL)

    print(
        "🎵 Музыка: /api/music?q=..."
    )

    print(
        "👤 Персонажи: /api/characters"
    )

    print(
        "🎮 Игры: /api/launch/{id}"
    )

    print(
        "❤️ Health: /api/health"
    )

    print("=" * 60)


    def open_browser():

        time.sleep(2)

        print(
            "🌐 Открываю браузер..."
        )

        try:

            webbrowser.open(URL)

            print(
                "✅ Браузер запущен"
            )

        except Exception as e:

            print(
                "❌ Не удалось открыть браузер:",
                e
            )


    threading.Thread(
        target=open_browser,
        daemon=True
    ).start()


    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False
    )
