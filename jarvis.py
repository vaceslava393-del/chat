import os
import json
import platform
import re
import shutil
import subprocess
import webbrowser
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
from dotenv import load_dotenv

from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse


# ============================================================
# CONFIG / .ENV
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

print("📁 Путь к проекту:", BASE_DIR)
print("📄 Ищу .env:", ENV_FILE)

if not ENV_FILE.is_file():
    raise FileNotFoundError(
        f"Файл .env не найден:\n{ENV_FILE}"
    )

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

GROQ_URL = os.getenv(
    "GROQ_URL",
    "https://api.groq.com/openai/v1/chat/completions"
)

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY не найден в .env"
    )

print("✅ .env успешно загружен")
print("🔑 GROQ_API_KEY найден")
print("🤖 Модель:", GROQ_MODEL)


# ============================================================
# OPTIONAL OPENCV
# ============================================================

try:
    import cv2
except ImportError:
    cv2 = None


# ============================================================
# OPTIONAL YOLO
# ============================================================

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


# ============================================================
# CAMERA GLOBALS
# ============================================================

camera = None
camera_lock = __import__("threading").Lock()
camera_enabled = False

model = None


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    print()
    print("🚀 JARVIS запускается...")

    yield

    print()
    print("🛑 Остановка JARVIS...")

    release_camera()

    print("✅ JARVIS остановлен.")


app = FastAPI(
    title="JARVIS AI",
    version="3.0",
    lifespan=lifespan
)


# ============================================================
# STARTUP
# ============================================================

print()
print("=" * 70)
print("🤖 JARVIS AI")
print("=" * 70)

print("Python:", platform.python_version())
print("Project:", BASE_DIR)
print("Groq model:", GROQ_MODEL)
print("Groq API key: найден")

print("=" * 70)
print()


# ============================================================
# YOLO
# ============================================================

def load_yolo():

    global model

    if YOLO is None:

        print(
            "⚠️ YOLO не установлен."
        )

        return

    try:

        model = YOLO(
            "yolov8n.pt"
        )

        print(
            "✅ YOLO модель загружена."
        )

    except Exception as e:

        print(
            "⚠️ YOLO модель не загружена:",
            e
        )

        model = None


load_yolo()


# ============================================================
# WINDOWS APPLICATIONS
# ============================================================

def get_start_menu_locations():

    locations = []

    appdata = os.environ.get(
        "APPDATA"
    )

    programdata = os.environ.get(
        "PROGRAMDATA"
    )

    if appdata:

        locations.append(
            Path(appdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
        )

    if programdata:

        locations.append(
            Path(programdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
        )

    locations.append(
        Path.home() / "Desktop"
    )

    return locations


def normalize_app_name(name: str):

    name = str(
        name
    ).lower().strip()

    for extension in (
        ".lnk",
        ".url",
        ".exe"
    ):

        if name.endswith(extension):

            name = name[
                :-len(extension)
            ]

    return name.strip()


def scan_installed_applications():

    applications = {}

    for location in get_start_menu_locations():

        if not location.exists():
            continue

        try:

            for item in location.rglob("*"):

                if not item.is_file():
                    continue

                if item.suffix.lower() in (
                    ".exe",
                    ".lnk",
                    ".url"
                ):

                    name = normalize_app_name(
                        item.stem
                    )

                    if name:
                        applications[name] = str(item)

        except (
            PermissionError,
            OSError
        ):

            continue

    return applications


SYSTEM_APPS = {

    "notepad": "notepad.exe",
    "блокнот": "notepad.exe",

    "calculator": "calc.exe",
    "калькулятор": "calc.exe",

    "explorer": "explorer.exe",
    "проводник": "explorer.exe",

    "paint": "mspaint.exe",
    "рисование": "mspaint.exe",

    "cmd": "cmd.exe",
}


ALLOWED_APPS = scan_installed_applications()
ALLOWED_APPS.update(SYSTEM_APPS)

print(
    "Найдено приложений:",
    len(ALLOWED_APPS)
)


# ============================================================
# FIND APPLICATION
# ============================================================

def find_application(application: str):

    application = str(
        application
    ).strip()

    if not application:
        return None

    name = application.lower().strip()

    if name.endswith(".exe"):
        name = name[:-4]

    if name in SYSTEM_APPS:
        return SYSTEM_APPS[name]

    for app_name, path in ALLOWED_APPS.items():

        clean_name = str(
            app_name
        ).lower().strip()

        if clean_name.endswith(".exe"):
            clean_name = clean_name[:-4]

        if name == clean_name:
            return path

    try:

        found = shutil.which(
            application
        )

        if found:
            return found

        found = shutil.which(
            application + ".exe"
        )

        if found:
            return found

    except Exception:
        pass

    locations = [

        Path(
            os.environ.get(
                "PROGRAMFILES",
                r"C:\Program Files"
            )
        ),

        Path(
            os.environ.get(
                "PROGRAMFILES(X86)",
                r"C:\Program Files (x86)"
            )
        ),

        Path.home()
        / "AppData"
        / "Local",

        Path.home()
        / "AppData"
        / "Roaming",

        Path.home()
        / "Desktop",

        Path(
            os.environ.get(
                "APPDATA",
                ""
            )
        )
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs",

        Path(
            os.environ.get(
                "PROGRAMDATA",
                ""
            )
        )
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs",
    ]

    for location in locations:

        if not location.exists():
            continue

        try:

            for exe in location.rglob(
                "*.exe"
            ):

                if (
                    exe.stem.lower()
                    == name
                ):

                    return str(exe)

        except (
            PermissionError,
            OSError
        ):

            continue

    return None


# ============================================================
# OPEN APPLICATION
# ============================================================

def open_application(
    application: str
):

    application = str(
        application
    ).strip()

    if not application:

        return {
            "success": False,
            "message":
                "Название приложения не указано."
        }

    program = find_application(
        application
    )

    if not program:

        return {
            "success": False,
            "message":
                f"Приложение '{application}' не найдено."
        }

    try:

        if str(program).lower().endswith(
            (".lnk", ".url")
        ):

            os.startfile(
                program
            )

        else:

            directory = os.path.dirname(
                program
            )

            subprocess.Popen(
                [program],
                cwd=directory or None,
                shell=False
            )

        return {
            "success": True,
            "application": application,
            "path": str(program),
            "message":
                f"Приложение '{application}' запущено."
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Не удалось запустить '{application}': {e}"
        }


# ============================================================
# APPLICATION LIST
# ============================================================

def get_applications():

    global ALLOWED_APPS

    ALLOWED_APPS = scan_installed_applications()
    ALLOWED_APPS.update(SYSTEM_APPS)

    return {
        "success": True,
        "count": len(ALLOWED_APPS),
        "applications":
            sorted(ALLOWED_APPS.keys())
    }


# ============================================================
# STEAM
# ============================================================

def open_steam():

    possible_paths = [

        Path(
            os.environ.get(
                "PROGRAMFILES(X86)",
                r"C:\Program Files (x86)"
            )
        )
        / "Steam"
        / "steam.exe",

        Path(
            os.environ.get(
                "PROGRAMFILES",
                r"C:\Program Files"
            )
        )
        / "Steam"
        / "steam.exe",

        Path.home()
        / "AppData"
        / "Local"
        / "Steam"
        / "steam.exe",
    ]

    steam_path = None

    for path in possible_paths:

        if path.is_file():

            steam_path = path
            break

    if steam_path is None:

        found = shutil.which(
            "steam.exe"
        )

        if found:
            steam_path = Path(found)

    if steam_path is None:

        return {
            "success": False,
            "message": "Steam не найден."
        }

    try:

        subprocess.Popen(
            [str(steam_path)],
            shell=False
        )

        return {
            "success": True,
            "application": "Steam",
            "path": str(steam_path),
            "message": "Steam запущен."
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Не удалось запустить Steam: {e}"
        }


# ============================================================
# PC INFO
# ============================================================

def get_pc_info():

    try:

        system_drive = os.environ.get(
            "SystemDrive",
            "C:"
        )

        total, used, free = shutil.disk_usage(
            system_drive + "\\"
        )

        return {

            "success": True,

            "system":
                platform.system(),

            "release":
                platform.release(),

            "version":
                platform.version(),

            "machine":
                platform.machine(),

            "processor":
                platform.processor(),

            "computer_name":
                platform.node(),

            "cpu_count":
                os.cpu_count(),

            "disk_total_gb":
                round(
                    total / 1024 ** 3,
                    2
                ),

            "disk_used_gb":
                round(
                    used / 1024 ** 3,
                    2
                ),

            "disk_free_gb":
                round(
                    free / 1024 ** 3,
                    2
                )
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# YOUTUBE
# ============================================================

def play_youtube(query: str):

    query = str(
        query
    ).strip()

    if not query:

        return {
            "success": False,
            "message":
                "Название видео не указано."
        }

    try:

        encoded_query = quote(
            query,
            safe=""
        )

        search_url = (
            "https://www.youtube.com/results?"
            "search_query="
            + encoded_query
        )

        with httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
            }
        ) as client:

            response = client.get(
                search_url
            )

        if response.status_code != 200:

            webbrowser.open(
                search_url,
                new=2
            )

            return {
                "success": True,
                "query": query,
                "url": search_url,
                "message":
                    f"Открываю YouTube: {query}"
            }

        video_ids = re.findall(
            r'"videoId":"([^"]+)"',
            response.text
        )

        unique_video_ids = []

        for video_id in video_ids:

            if video_id not in unique_video_ids:

                unique_video_ids.append(
                    video_id
                )

        if unique_video_ids:

            video_id = unique_video_ids[0]

            video_url = (
                "https://www.youtube.com/watch?v="
                + video_id
            )

            webbrowser.open(
                video_url,
                new=2
            )

            return {
                "success": True,
                "query": query,
                "video_id": video_id,
                "url": video_url,
                "message":
                    f"Открываю видео YouTube: {query}"
            }

        webbrowser.open(
            search_url,
            new=2
        )

        return {
            "success": True,
            "query": query,
            "url": search_url,
            "message":
                f"Открываю поиск YouTube: {query}"
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Ошибка YouTube: {e}"
        }


# ============================================================
# YANDEX
# ============================================================

def search_yandex(query: str):

    query = str(
        query
    ).strip()

    if not query:

        return {
            "success": False,
            "message":
                "Поисковый запрос пустой."
        }

    try:

        url = (
            "https://yandex.ru/search/?text="
            + quote(
                query,
                safe=""
            )
        )

        opened = webbrowser.open(
            url,
            new=2
        )

        if not opened:

            return {
                "success": False,
                "message":
                    "Не удалось открыть браузер."
            }

        return {
            "success": True,
            "query": query,
            "url": url,
            "message":
                f"Открываю поиск Яндекс: {query}"
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Ошибка Яндекса: {e}"
        }


# ============================================================
# MOVIE SEARCH
# ============================================================

def search_yandex_movie(query: str):

    query = str(
        query
    ).strip()

    if not query:

        return {
            "success": False,
            "message":
                "Название фильма не указано."
        }

    try:

        movie_query = (
            f"{query} смотреть фильм"
        )

        url = (
            "https://yandex.ru/search/?text="
            + quote(
                movie_query,
                safe=""
            )
        )

        webbrowser.open(
            url,
            new=2
        )

        return {
            "success": True,
            "query": query,
            "url": url,
            "message":
                f"Открываю поиск фильма: {query}"
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Ошибка поиска фильма: {e}"
        }


# ============================================================
# WEBSITES
# ============================================================

KNOWN_WEBSITES = {

    "youtube":
        "https://www.youtube.com",

    "ютуб":
        "https://www.youtube.com",

    "google":
        "https://www.google.com",

    "гугл":
        "https://www.google.com",

    "yandex":
        "https://yandex.ru",

    "яндекс":
        "https://yandex.ru",

    "vk":
        "https://vk.com",

    "вк":
        "https://vk.com",

    "telegram":
        "https://web.telegram.org",

    "телеграм":
        "https://web.telegram.org",
}


def open_website(url: str):

    url = str(
        url
    ).strip()

    if not url:

        return {
            "success": False,
            "message":
                "URL пустой."
        }

    if url.lower() in KNOWN_WEBSITES:

        url = KNOWN_WEBSITES[
            url.lower()
        ]

    if not url.startswith(
        (
            "http://",
            "https://"
        )
    ):

        url = "https://" + url

    try:

        opened = webbrowser.open(
            url,
            new=2
        )

        if not opened:

            return {
                "success": False,
                "message":
                    "Не удалось открыть браузер."
            }

        return {
            "success": True,
            "url": url,
            "message":
                f"Открыта страница: {url}"
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Ошибка открытия сайта: {e}"
        }


# ============================================================
# FOLDERS
# ============================================================

KNOWN_FOLDERS = {

    "downloads":
        Path.home() / "Downloads",

    "загрузки":
        Path.home() / "Downloads",

    "desktop":
        Path.home() / "Desktop",

    "рабочий стол":
        Path.home() / "Desktop",

    "documents":
        Path.home() / "Documents",

    "документы":
        Path.home() / "Documents",
}


def open_folder(path: str):

    path = os.path.expandvars(
        str(path)
    )

    path = os.path.expanduser(
        path
    )

    if path.lower() in KNOWN_FOLDERS:

        path = str(
            KNOWN_FOLDERS[
                path.lower()
            ]
        )

    if not path:

        return {
            "success": False,
            "message":
                "Путь не указан."
        }

    try:

        if not os.path.exists(path):

            return {
                "success": False,
                "message":
                    f"Путь не существует: {path}"
            }

        os.startfile(path)

        return {
            "success": True,
            "path": path,
            "message":
                f"Открыта папка: {path}"
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


# ============================================================
# DOWNLOADS
# ============================================================

def get_downloads():

    downloads = (
        Path.home()
        / "Downloads"
    )

    if not downloads.exists():

        return {
            "success": False,
            "message":
                "Папка Downloads не найдена."
        }

    try:

        files = []

        for item in downloads.iterdir():

            files.append({

                "name":
                    item.name,

                "type":
                    "folder"
                    if item.is_dir()
                    else "file"
            })

        return {

            "success": True,

            "path":
                str(downloads),

            "items":
                files[:100]
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


# ============================================================
# FIND FILE
# ============================================================

def find_file(filename: str):

    filename = str(
        filename
    ).lower().strip()

    if not filename:

        return {
            "success": False,
            "message":
                "Имя файла не указано."
        }

    search_locations = [

        Path.home()
        / "Downloads",

        Path.home()
        / "Desktop",

        Path.home()
        / "Documents",
    ]

    results = []

    for location in search_locations:

        if not location.exists():
            continue

        try:

            for path in location.rglob("*"):

                if (
                    filename
                    in path.name.lower()
                ):

                    results.append(
                        str(path)
                    )

                    if len(results) >= 30:

                        return {
                            "success": True,
                            "results": results
                        }

        except (
            PermissionError,
            OSError
        ):

            continue

    return {
        "success": True,
        "results": results
    }


# ============================================================
# DOWNLOAD FILE
# ============================================================

DOWNLOAD_DIR = (
    Path.home()
    / "Downloads"
)

MAX_DOWNLOAD_SIZE = (
    2 * 1024 ** 3
)


async def download_file(url: str):

    url = str(
        url
    ).strip()

    if not url:

        return {
            "success": False,
            "message":
                "URL не указан."
        }

    parsed = urlparse(url)

    if parsed.scheme not in (
        "http",
        "https"
    ):

        return {
            "success": False,
            "message":
                "Разрешены только HTTP и HTTPS."
        }

    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = Path(
        parsed.path
    ).name

    if not filename:
        filename = "download"

    filename = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        filename
    )

    destination = (
        DOWNLOAD_DIR
        / filename
    )

    try:

        async with httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True
        ) as client:

            async with client.stream(
                "GET",
                url,
                headers={
                    "User-Agent":
                        "Mozilla/5.0"
                }
            ) as response:

                response.raise_for_status()

                content_length = (
                    response.headers.get(
                        "content-length"
                    )
                )

                if content_length:

                    try:
                        size = int(
                            content_length
                        )
                    except ValueError:
                        size = 0

                    if size > MAX_DOWNLOAD_SIZE:

                        return {
                            "success": False,
                            "message":
                                "Файл слишком большой."
                        }

                downloaded = 0

                with open(
                    destination,
                    "wb"
                ) as file:

                    async for chunk in response.aiter_bytes(
                        1024 * 1024
                    ):

                        downloaded += len(
                            chunk
                        )

                        if downloaded > MAX_DOWNLOAD_SIZE:

                            destination.unlink(
                                missing_ok=True
                            )

                            return {
                                "success": False,
                                "message":
                                    "Файл больше 2 ГБ."
                            }

                        file.write(chunk)

        return {

            "success": True,

            "path":
                str(destination),

            "size_mb":
                round(
                    downloaded / 1024 ** 2,
                    2
                ),

            "message":
                f"Файл скачан: {filename}"
        }

    except Exception as e:

        destination.unlink(
            missing_ok=True
        )

        return {
            "success": False,
            "message":
                f"Ошибка загрузки: {e}"
        }


# ============================================================
# OPEN REQUESTED
# ============================================================

def open_requested(
    target: str,
    target_type: str = "auto"
):

    target = str(
        target
    ).strip()

    target_type = str(
        target_type
    ).lower().strip()

    if not target:

        return {
            "success": False,
            "message":
                "Не указано, что нужно открыть."
        }

    if target_type == "movie":

        return search_yandex_movie(
            target
        )

    if target_type == "application":

        if target.lower() in (
            "steam",
            "стим"
        ):

            return open_steam()

        return open_application(
            target
        )

    if target_type == "website":

        return open_website(
            target
        )

    if target_type == "youtube":

        return play_youtube(
            target
        )

    if target_type == "file":

        result = find_file(
            target
        )

        files = result.get(
            "results",
            []
        )

        if not files:

            return {
                "success": False,
                "message":
                    f"Файл '{target}' не найден."
            }

        try:

            os.startfile(
                files[0]
            )

            return {
                "success": True,
                "path": files[0],
                "message":
                    f"Файл '{target}' открыт."
            }

        except Exception as e:

            return {
                "success": False,
                "message":
                    f"Не удалось открыть файл: {e}"
            }

    if target_type == "folder":

        return open_folder(
            target
        )

    if target_type == "auto":

        lower = target.lower().strip()

        if lower in (
            "steam",
            "стим"
        ):

            return open_steam()

        if lower in KNOWN_FOLDERS:

            return open_folder(
                str(
                    KNOWN_FOLDERS[
                        lower
                    ]
                )
            )

        if lower in KNOWN_WEBSITES:

            return open_website(
                KNOWN_WEBSITES[
                    lower
                ]
            )

        youtube_prefixes = (

            "включи музыку ",
            "включи песню ",
            "включи видео ",
            "включи ролик ",
            "найди на youtube ",
            "найди на ютуб ",
            "play music ",
            "play song ",
            "play video ",
        )

        for prefix in youtube_prefixes:

            if lower.startswith(prefix):

                query = target[
                    len(prefix):
                ].strip()

                if query:
                    return play_youtube(
                        query
                    )

        application = find_application(
            target
        )

        if application:

            return open_application(
                target
            )

        file_result = find_file(
            target
        )

        files = file_result.get(
            "results",
            []
        )

        if files:

            try:

                os.startfile(
                    files[0]
                )

                return {
                    "success": True,
                    "path": files[0],
                    "message":
                        f"Файл '{target}' открыт."
                }

            except Exception:
                pass

        return {
            "success": False,
            "message":
                f"Не удалось определить, "
                f"что открыть: '{target}'."
        }

    return {
        "success": False,
        "message":
            f"Неизвестный тип объекта: {target_type}"
    }


# ============================================================
# CAMERA
# ============================================================

def get_camera():

    global camera

    if cv2 is None:
        return None

    with camera_lock:

        if (
            camera is None
            or not camera.isOpened()
        ):

            print(
                "📷 Открываем камеру..."
            )

            camera = cv2.VideoCapture(
                0,
                cv2.CAP_DSHOW
            )

            if not camera.isOpened():

                camera = cv2.VideoCapture(
                    0
                )

            if not camera.isOpened():

                print(
                    "❌ Камера не открылась."
                )

                camera = None

                return None

            camera.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                640
            )

            camera.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                480
            )

            print(
                "✅ Камера открыта."
            )

        return camera


def start_camera():

    global camera_enabled

    if cv2 is None:

        return {
            "success": False,
            "message":
                "OpenCV не установлен."
        }

    cam = get_camera()

    if cam is None:

        return {
            "success": False,
            "message":
                "Камера не найдена или не может быть открыта."
        }

    camera_enabled = True

    return {
        "success": True,
        "message":
            "Камера запущена."
    }


def release_camera():

    global camera
    global camera_enabled

    camera_enabled = False

    with camera_lock:

        if camera is not None:

            try:
                camera.release()
            except Exception:
                pass

            camera = None

    if cv2 is not None:

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    print(
        "📷 Камера освобождена."
    )


def stop_camera():

    release_camera()

    return {
        "success": True,
        "message":
            "Камера выключена."
    }


def generate_camera_frames():

    global camera_enabled

    while camera_enabled:

        cam = get_camera()

        if cam is None:
            break

        success, frame = cam.read()

        if not success:

            time.sleep(0.1)
            continue

        person_count = 0

        if model is not None:

            try:

                results = model(
                    frame,
                    verbose=False
                )

                for result in results:

                    boxes = result.boxes

                    if boxes is None:
                        continue

                    for box in boxes:

                        class_id = int(
                            box.cls[0]
                        )

                        # Только человек
                        if class_id != 0:
                            continue

                        confidence = float(
                            box.conf[0]
                        )

                        if confidence < 0.45:
                            continue

                        person_count += 1

                        x1, y1, x2, y2 = map(
                            int,
                            box.xyxy[0]
                        )

                        cv2.rectangle(
                            frame,
                            (x1, y1),
                            (x2, y2),
                            (0, 255, 0),
                            2
                        )

                        cv2.putText(
                            frame,
                            f"Person {confidence:.2f}",
                            (
                                x1,
                                max(
                                    y1 - 10,
                                    20
                                )
                            ),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 255, 0),
                            2
                        )

            except Exception as e:

                print(
                    "Ошибка YOLO:",
                    e
                )

        cv2.putText(
            frame,
            f"PEOPLE: {person_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

        ret, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )

    print(
        "📷 Видеопоток остановлен."
    )


@app.get("/camera")
def camera_stream():

    if cv2 is None:

        return JSONResponse(
            {
                "success": False,
                "message":
                    "OpenCV не установлен."
            },
            status_code=500
        )

    if not camera_enabled:

        return JSONResponse(
            {
                "success": False,
                "message":
                    "Камера выключена."
            },
            status_code=400
        )

    return StreamingResponse(
        generate_camera_frames(),
        media_type=(
            "multipart/x-mixed-replace;"
            " boundary=frame"
        )
    )


@app.post("/camera/stop")
def camera_stop_api():

    return JSONResponse(
        stop_camera()
    )


# ============================================================
# TOOLS FOR GROQ
# ============================================================

TOOLS = [

    {
        "type": "function",
        "function": {

            "name":
                "get_pc_info",

            "description":
                "Получить информацию о компьютере.",

            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {

            "name":
                "get_applications",

            "description":
                "Получить список установленных приложений.",

            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {

            "name":
                "open_requested",

            "description":
                "Открыть приложение, Steam, сайт, YouTube, фильм, файл или папку.",

            "parameters": {

                "type": "object",

                "properties": {

                    "target": {
                        "type": "string",
                        "description":
                            "Название или путь."
                    },

                    "target_type": {
                        "type": "string",
                        "enum": [
                            "auto",
                            "application",
                            "website",
                            "youtube",
                            "movie",
                            "file",
                            "folder"
                        ]
                    }
                },

                "required": [
                    "target",
                    "target_type"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {

            "name":
                "search_yandex",

            "description":
                "Открыть поиск Яндекс.",

            "parameters": {

                "type": "object",

                "properties": {

                    "query": {
                        "type": "string"
                    }
                },

                "required": [
                    "query"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {

            "name":
                "get_downloads",

            "description":
                "Получить содержимое папки Downloads.",

            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {

            "name":
                "find_file",

            "description":
                "Найти файл на компьютере.",

            "parameters": {

                "type": "object",

                "properties": {

                    "filename": {
                        "type": "string"
                    }
                },

                "required": [
                    "filename"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {

            "name":
                "download_file",

            "description":
                "Скачать файл по HTTP или HTTPS.",

            "parameters": {

                "type": "object",

                "properties": {

                    "url": {
                        "type": "string"
                    }
                },

                "required": [
                    "url"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {

            "name":
                "start_camera",

            "description":
                "Запустить локальную камеру компьютера.",

            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {

            "name":
                "stop_camera",

            "description":
                "Выключить локальную камеру компьютера.",

            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# ============================================================
# EXECUTE TOOL
# ============================================================

async def execute_tool(
    name: str,
    arguments: dict
):

    try:

        if name == "get_pc_info":

            return get_pc_info()

        if name == "get_applications":

            return get_applications()

        if name == "open_requested":

            return open_requested(
                arguments.get(
                    "target",
                    ""
                ),
                arguments.get(
                    "target_type",
                    "auto"
                )
            )

        if name == "search_yandex":

            return search_yandex(
                arguments.get(
                    "query",
                    ""
                )
            )

        if name == "get_downloads":

            return get_downloads()

        if name == "find_file":

            return find_file(
                arguments.get(
                    "filename",
                    ""
                )
            )

        if name == "download_file":

            return await download_file(
                arguments.get(
                    "url",
                    ""
                )
            )

        if name == "start_camera":

            return start_camera()

        if name == "stop_camera":

            return stop_camera()

        return {
            "success": False,
            "message":
                f"Неизвестный инструмент: {name}"
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Ошибка инструмента {name}: {e}"
        }


# ============================================================
# GROQ AI
# ============================================================

MAX_HISTORY = 10

conversation_history = []


async def ask_groq(text: str):

    if not GROQ_API_KEY:

        return {
            "answer":
                "GROQ_API_KEY не найден. Проверь .env",
            "action": "none",
            "query": ""
        }

    system_message = """
Ты JARVIS — интеллектуальный локальный AI-помощник.

Отвечай на языке пользователя.

Если пользователь пишет по-русски — отвечай по-русски.
Если пишет на английском — отвечай на английском.
Если пишет на казахском — отвечай на казахском.

Ты умеешь:
- разговаривать;
- отвечать на вопросы;
- переводить;
- управлять компьютером;
- запускать приложения;
- запускать Steam;
- открывать сайты;
- искать через Яндекс;
- открывать YouTube;
- искать музыку;
- искать видео;
- искать фильмы;
- искать файлы;
- открывать файлы;
- открывать папки;
- просматривать Downloads;
- скачивать файлы;
- включать камеру;
- выключать камеру.

ПРАВИЛА:

1. Если действие требует инструмента — используй инструмент.

2. Не говори, что действие выполнено,
   пока инструмент не вернул результат.

3. Если success=true — сообщи результат.

4. Если success=false — честно сообщи об ошибке.

5. Для информации о компьютере используй get_pc_info.

6. Для запуска приложений используй open_requested.

7. Для сайтов используй open_requested с target_type="website".

8. Для YouTube используй target_type="youtube".

9. Для фильмов используй target_type="movie".

10. Для файлов используй target_type="file".

11. Для папок используй target_type="folder".

12. Для обычной команды открытия используй target_type="auto".

13. Для скачивания используй download_file.

14. Для запуска камеры используй start_camera.

15. Для выключения камеры используй stop_camera.

16. Если пользователь говорит:
"включи камеру",
"запусти камеру",
"покажи камеру",
используй start_camera.

17. Если пользователь говорит:
"выключи камеру",
"останови камеру",
"закрой камеру",
используй stop_camera.

18. Если пользователь говорит:
"включи музыку",
"включи песню",
"включи видео",
используй YouTube.

19. Если пользователь просит перевод,
переводи точно и без лишних комментариев.

20. При переводе сохраняй смысл и стиль.

БЕЗОПАСНОСТЬ:

- Не распознавай личность человека.
- Не выполняй распознавание лиц.
- Не используй камеру для слежки.
- Не удаляй файлы.
- Не форматируй диски.
- Не отключай антивирус.
- Не выполняй опасные системные операции.

Отвечай кратко после выполнения команды.
"""

    messages = [
        {
            "role": "system",
            "content": system_message
        }
    ]

    messages.extend(
        conversation_history
    )

    messages.append(
        {
            "role": "user",
            "content": text
        }
    )

    headers = {
        "Authorization":
            f"Bearer {GROQ_API_KEY}",

        "Content-Type":
            "application/json"
    }

    data = {

        "model":
            GROQ_MODEL,

        "messages":
            messages,

        "tools":
            TOOLS,

        "tool_choice":
            "auto",

        "temperature":
            0.2
    }

    try:

        async with httpx.AsyncClient(
            timeout=60.0
        ) as client:

            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=data
            )

        print(
            "Groq status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "Groq error:",
                response.text
            )

            return {

                "answer":
                    f"Ошибка Groq "
                    f"{response.status_code}: "
                    f"{response.text[:500]}",

                "action":
                    "none",

                "query":
                    ""
            }

        try:

            result = response.json()

        except json.JSONDecodeError:

            return {
                "answer":
                    "Groq вернул некорректный JSON.",
                "action": "none",
                "query": ""
            }

        choices = result.get(
            "choices",
            []
        )

        if not choices:

            return {
                "answer":
                    "Groq не вернул ответ.",
                "action": "none",
                "query": ""
            }

        message = choices[0].get(
            "message",
            {}
        )

        if not message:

            return {
                "answer":
                    "Groq не вернул сообщение.",
                "action": "none",
                "query": ""
            }

        tool_calls = message.get(
            "tool_calls"
        ) or []

        # ====================================================
        # TOOLS
        # ====================================================

        if tool_calls:

            messages.append(
                message
            )

            for tool_call in tool_calls:

                function = tool_call.get(
                    "function",
                    {}
                )

                name = function.get(
                    "name",
                    ""
                )

                arguments_text = function.get(
                    "arguments",
                    "{}"
                )

                try:

                    arguments = json.loads(
                        arguments_text
                    )

                except (
                    json.JSONDecodeError,
                    TypeError
                ):

                    arguments = {}

                print()
                print(
                    "🔧 JARVIS TOOL:",
                    name
                )

                print(
                    "Arguments:",
                    arguments
                )

                tool_result = await execute_tool(
                    name,
                    arguments
                )

                print(
                    "Tool result:",
                    tool_result
                )

                messages.append(
                    {
                        "role":
                            "tool",

                        "tool_call_id":
                            tool_call.get(
                                "id",
                                ""
                            ),

                        "name":
                            name,

                        "content":
                            json.dumps(
                                tool_result,
                                ensure_ascii=False
                            )
                    }
                )

            # =================================================
            # SECOND GROQ REQUEST
            # =================================================

            second_data = {

                "model":
                    GROQ_MODEL,

                "messages":
                    messages,

                "tools":
                    TOOLS,

                "tool_choice":
                    "none",

                "temperature":
                    0.2
            }

            async with httpx.AsyncClient(
                timeout=60.0
            ) as client:

                second_response = await client.post(
                    GROQ_URL,
                    headers=headers,
                    json=second_data
                )

            print(
                "Groq second status:",
                second_response.status_code
            )

            if second_response.status_code != 200:

                return {
                    "answer":
                        "Команда выполнена, "
                        "но Groq не смог сформировать "
                        "финальный ответ.",
                    "action":
                        "none",
                    "query":
                        ""
                }

            try:

                second_result = (
                    second_response.json()
                )

            except json.JSONDecodeError:

                return {
                    "answer":
                        "Groq вернул некорректный ответ.",
                    "action":
                        "none",
                    "query":
                        ""
                }

            second_choices = second_result.get(
                "choices",
                []
            )

            if second_choices:

                second_message = (
                    second_choices[0]
                    .get(
                        "message",
                        {}
                    )
                )

                answer = (
                    second_message.get(
                        "content"
                    )
                    or "Команда выполнена."
                )

            else:

                answer = "Команда выполнена."

        else:

            answer = (
                message.get(
                    "content"
                )
                or "Не удалось получить ответ."
            )

        answer = answer.strip()

        # ====================================================
        # MEMORY
        # ====================================================

        conversation_history.append(
            {
                "role":
                    "user",
                "content":
                    text
            }
        )

        conversation_history.append(
            {
                "role":
                    "assistant",
                "content":
                    answer
            }
        )

        while len(
            conversation_history
        ) > MAX_HISTORY:

            conversation_history.pop(
                0
            )

        return {
            "answer":
                answer,
            "action":
                "none",
            "query":
                ""
        }

    except httpx.HTTPError as e:

        print(
            "HTTP error:",
            repr(e)
        )

        return {
            "answer":
                f"Ошибка подключения к Groq: {e}",
            "action":
                "none",
            "query":
                ""
        }

    except Exception as e:

        print(
            "ask_groq error:",
            repr(e)
        )

        return {
            "answer":
                f"Произошла ошибка: {e}",
            "action":
                "none",
            "query":
                ""
        }


# ============================================================
# CHAT API
# ============================================================

@app.post("/chat")
async def chat(
    text: str = Form(...)
):

    result = await ask_groq(
        text
    )

    return JSONResponse(
        result
    )


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def home():

    return HTMLResponse(
r"""
<!DOCTYPE html>

<html lang="ru">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>🤖 JARVIS AI</title>

<style>

:root {
    --blue: #00d9ff;
    --red: #ff1744;
    --bg: #02050a;
}

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    min-height: 100%;
    font-family: Arial, sans-serif;
    background: #02050a;
    color: white;
}

body {

    min-height: 100vh;

    background:
        radial-gradient(
            circle at 50% 30%,
            rgba(0, 150, 255, .15),
            transparent 30%
        ),

        linear-gradient(
            135deg,
            #02050a,
            #06101c,
            #02050a
        );
}

.container {

    width: min(
        1100px,
        calc(100% - 30px)
    );

    margin: auto;

    padding:
        25px 0 50px;
}

.header {

    text-align: center;

    padding: 30px;

    border:
        1px solid
        rgba(0,217,255,.4);

    border-radius: 20px;

    background:
        rgba(5,15,27,.9);
}

.robot {

    font-size: 70px;
}

h1 {

    margin: 10px 0;

    color: var(--blue);

    font-size: 60px;

    letter-spacing: 8px;

    text-shadow:
        0 0 10px var(--blue),
        0 0 30px var(--blue);
}

.subtitle {

    color: #8ba8b8;

    letter-spacing: 3px;
}

.status-panel {

    display: flex;

    justify-content: center;

    align-items: center;

    gap: 10px;

    margin: 20px;
}

.status-dot {

    width: 10px;

    height: 10px;

    border-radius: 50%;

    background: #00ff9d;

    box-shadow:
        0 0 12px #00ff9d;
}

.controls {

    display: grid;

    grid-template-columns:
        1fr
        auto
        auto
        auto;

    gap: 10px;

    margin-bottom: 15px;
}

input,
select {

    padding: 15px;

    border-radius: 12px;

    border:
        1px solid
        rgba(0,217,255,.35);

    background:
        rgba(3,13,23,.9);

    color: white;

    font-size: 16px;

    outline: none;
}

button {

    padding:
        12px 18px;

    border:
        1px solid
        rgba(0,217,255,.4);

    border-radius: 12px;

    color: white;

    cursor: pointer;

    font-size: 15px;

    transition: .2s;
}

button:hover {

    transform:
        translateY(-2px);

    box-shadow:
        0 0 20px
        rgba(0,217,255,.3);
}

#send {

    background:
        linear-gradient(
            135deg,
            #0066ff,
            #00a6ff
        );
}

#mic {

    background:
        linear-gradient(
            135deg,
            #9b001e,
            #ff1744
        );
}

#cameraButton {

    background:
        linear-gradient(
            135deg,
            #006b68,
            #00a99d
        );
}

.language-panel {

    display: flex;

    justify-content: center;

    align-items: center;

    gap: 10px;

    margin: 15px;
}

#chat {

    display: flex;

    flex-direction: column;

    gap: 15px;
}

.message {

    padding: 16px;

    border-radius: 15px;

    line-height: 1.5;

    white-space: pre-wrap;
}

.message b {

    display: block;

    margin-bottom: 6px;

    letter-spacing: 2px;
}

.user {

    align-self: flex-end;

    max-width: 80%;

    background:
        rgba(0,70,160,.8);

    border:
        1px solid
        rgba(0,150,255,.5);
}

.bot {

    align-self: flex-start;

    max-width: 90%;

    background:
        rgba(15,28,40,.95);

    border:
        1px solid
        rgba(0,217,255,.3);
}

.bot b {

    color:
        var(--blue);
}

.camera {

    display: none;

    margin-top: 25px;

    overflow: hidden;

    border:
        1px solid
        rgba(0,217,255,.4);

    border-radius: 18px;

    background: black;
}

.camera-title {

    padding: 12px;

    text-align: center;

    color:
        var(--blue);

    letter-spacing: 3px;

    background:
        rgba(0,25,40,.9);
}

.camera img {

    display: block;

    width: 100%;
}

.footer {

    text-align: center;

    color: #455a64;

    margin-top: 30px;

    font-size: 11px;

    letter-spacing: 2px;
}

@media(max-width:750px) {

    .controls {

        grid-template-columns:
            1fr 1fr;
    }

    .controls input {

        grid-column:
            1 / -1;
    }

    h1 {

        font-size: 45px;
    }

}

</style>

</head>

<body>

<div class="container">

<div class="header">

    <div class="robot">
        🤖
    </div>

    <h1>
        JARVIS
    </h1>

    <div class="subtitle">
        ARTIFICIAL INTELLIGENCE SYSTEM
    </div>

</div>

<div class="status-panel">

    <span class="status-dot"></span>

    <span id="status">
        SYSTEM ONLINE
    </span>

</div>

<div class="controls">

<input
    id="text"
    type="text"
    placeholder="Напиши команду или задай вопрос..."
    autocomplete="off"
>

<button id="send">
    ➤ SEND
</button>

<button id="mic">
    🎤 ВКЛ
</button>

<button id="cameraButton">
    📷 ВКЛ
</button>

</div>

<div class="language-panel">

    <span>
        🎤 Язык:
    </span>

    <select id="speechLanguage">

        <option value="auto">
            Авто
        </option>

        <option value="ru-RU">
            Русский
        </option>

        <option value="en-US">
            English
        </option>

        <option value="kk-KZ">
            Қазақша
        </option>

        <option value="uk-UA">
            Українська
        </option>

        <option value="de-DE">
            Deutsch
        </option>

        <option value="fr-FR">
            Français
        </option>

        <option value="es-ES">
            Español
        </option>

        <option value="it-IT">
            Italiano
        </option>

        <option value="zh-CN">
            中文
        </option>

        <option value="ja-JP">
            日本語
        </option>

    </select>

</div>

<div id="chat"></div>

<div
    id="cameraContainer"
    class="camera"
>

    <div class="camera-title">
        ◉ JARVIS VISION SYSTEM
    </div>

    <img
        id="cameraImage"
        src=""
        alt="JARVIS Camera"
    >

</div>

<div class="footer">

    JARVIS AI • LOCAL CONTROL SYSTEM

</div>

</div>


<script>

// ========================================================
// ELEMENTS
// ========================================================

const input =
    document.getElementById("text");

const chat =
    document.getElementById("chat");

const status =
    document.getElementById("status");

const cameraContainer =
    document.getElementById("cameraContainer");

const cameraImage =
    document.getElementById("cameraImage");

const cameraButton =
    document.getElementById("cameraButton");

const micButton =
    document.getElementById("mic");

const languageSelect =
    document.getElementById("speechLanguage");


// ========================================================
// STATES
// ========================================================

let isCameraOn = false;

let isListening = false;

let recognition = null;


// ========================================================
// ESCAPE
// ========================================================

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text;

    return div.innerHTML;
}


// ========================================================
// ADD MESSAGE
// ========================================================

function addMessage(
    type,
    name,
    text
) {

    chat.innerHTML += `

        <div class="message ${type}">

            <b>${escapeHtml(name)}</b>

            ${escapeHtml(text)}

        </div>

    `;

    window.scrollTo(
        0,
        document.body.scrollHeight
    );
}


// ========================================================
// SPEECH SYNTHESIS
// ========================================================

let availableVoices = [];


function loadVoices() {

    if (
        !("speechSynthesis" in window)
    ) {
        return;
    }

    availableVoices =
        speechSynthesis.getVoices();
}


if (
    "speechSynthesis" in window
) {

    loadVoices();

    speechSynthesis.onvoiceschanged =
        loadVoices;
}


// ========================================================
// LANGUAGE DETECTION
// ========================================================

function detectLanguage(text) {

    if (!text) {
        return "ru-RU";
    }

    if (
        /[ӘәҒғҚқҢңӨөҰұҮүҺһІі]/
        .test(text)
    ) {
        return "kk-KZ";
    }

    if (
        /[ЇїЄєҐґ]/
        .test(text)
    ) {
        return "uk-UA";
    }

    if (
        /[А-Яа-яЁё]/
        .test(text)
    ) {
        return "ru-RU";
    }

    if (
        /[\u0600-\u06FF]/
        .test(text)
    ) {
        return "ar-SA";
    }

    if (
        /[\u4E00-\u9FFF]/
        .test(text)
    ) {
        return "zh-CN";
    }

    if (
        /[\u3040-\u30FF]/
        .test(text)
    ) {
        return "ja-JP";
    }

    if (
        /[\uAC00-\uD7AF]/
        .test(text)
    ) {
        return "ko-KR";
    }

    return "en-US";
}


// ========================================================
// FIND VOICE
// ========================================================

function findVoice(lang) {

    loadVoices();

    const languageCode =
        lang
        .toLowerCase()
        .split("-")[0];

    let voice =
        availableVoices.find(
            v =>
                v.lang &&
                v.lang.toLowerCase()
                ===
                lang.toLowerCase()
        );

    if (voice) {
        return voice;
    }

    voice =
        availableVoices.find(
            v =>
                v.lang &&
                v.lang.toLowerCase()
                .startsWith(
                    languageCode
                )
        );

    return voice || null;
}


// ========================================================
// SPEAK
// ========================================================

function speak(text) {

    if (
        !text ||
        !text.trim()
    ) {
        return;
    }

    if (
        !("speechSynthesis" in window)
    ) {
        return;
    }

    speechSynthesis.cancel();

    const lang =
        detectLanguage(text);

    const utterance =
        new SpeechSynthesisUtterance(
            text
        );

    utterance.lang =
        lang;

    utterance.rate =
        0.95;

    utterance.pitch =
        1.0;

    utterance.volume =
        1.0;

    const voice =
        findVoice(lang);

    if (voice) {

        utterance.voice =
            voice;
    }

    utterance.onstart =
        function() {

            status.innerText =
                "🔊 JARVIS SPEAKING...";
        };

    utterance.onend =
        function() {

            if (!isListening) {

                status.innerText =
                    "SYSTEM ONLINE";
            }
        };

    setTimeout(
        function() {

            speechSynthesis.speak(
                utterance
            );

        },
        100
    );
}


// ========================================================
// SEND MESSAGE
// ========================================================

async function sendMessage() {

    const text =
        input.value.trim();

    if (!text) {
        return;
    }

    addMessage(
        "user",
        "YOU",
        text
    );

    input.value = "";

    status.innerText =
        "◉ JARVIS THINKING...";

    try {

        const response =
            await fetch(
                "/chat",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/x-www-form-urlencoded"
                    },

                    body:
                        "text=" +
                        encodeURIComponent(
                            text
                        )
                }
            );

        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );
        }

        const data =
            await response.json();

        const answer =
            data.answer ||
            "Нет ответа.";

        addMessage(
            "bot",
            "JARVIS",
            answer
        );

        status.innerText =
            "SYSTEM ONLINE";

        speak(answer);

        // Если AI выключил камеру
        if (
            text.toLowerCase()
                .includes("выключи камеру")
            ||
            text.toLowerCase()
                .includes("останови камеру")
        ) {

            isCameraOn = false;

            cameraImage.src = "";

            cameraContainer.style.display =
                "none";

            cameraButton.innerText =
                "📷 ВКЛ";
        }

        // Если AI включил камеру
        if (
            text.toLowerCase()
                .includes("включи камеру")
            ||
            text.toLowerCase()
                .includes("запусти камеру")
        ) {

            setTimeout(
                function() {

                    if (!isCameraOn) {

                        startCameraStream();
                    }

                },
                300
            );
        }

    }

    catch (error) {

        console.error(
            error
        );

        status.innerText =
            "❌ SYSTEM ERROR";

        addMessage(
            "bot",
            "JARVIS",
            "Ошибка соединения: "
            +
            error.message
        );
    }
}


// ========================================================
// SEND BUTTON
// ========================================================

document
    .getElementById("send")
    .addEventListener(
        "click",
        sendMessage
    );


// ========================================================
// ENTER
// ========================================================

input.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter"
        ) {

            sendMessage();
        }
    }
);


// ========================================================
// CAMERA START STREAM
// ========================================================

async function startCameraStream() {

    try {

        status.innerText =
            "📷 STARTING CAMERA...";

        const response =
            await fetch(
                "/chat",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/x-www-form-urlencoded"
                    },

                    body:
                        "text=" +
                        encodeURIComponent(
                            "запусти камеру"
                        )
                }
            );

        const data =
            await response.json();

        if (!data.answer) {

            throw new Error(
                "AI не вернул ответ"
            );
        }

        addMessage(
            "bot",
            "JARVIS",
            data.answer
        );

        speak(
            data.answer
        );

        cameraContainer.style.display =
            "block";

        // Cache busting
        cameraImage.src =
            "/camera?time=" +
            Date.now();

        isCameraOn =
            true;

        cameraButton.innerText =
            "📷 ВЫКЛ";

        status.innerText =
            "📷 CAMERA ACTIVE";

    }

    catch (error) {

        console.error(
            "Camera error:",
            error
        );

        isCameraOn =
            false;

        cameraImage.src =
            "";

        cameraContainer.style.display =
            "none";

        cameraButton.innerText =
            "📷 ВКЛ";

        status.innerText =
            "❌ CAMERA ERROR";

        addMessage(
            "bot",
            "JARVIS",
            "Не удалось запустить камеру."
        );
    }
}


// ========================================================
// CAMERA STOP
// ========================================================

async function stopCameraStream() {

    status.innerText =
        "📷 STOPPING CAMERA...";

    cameraImage.src =
        "";

    cameraContainer.style.display =
        "none";

    isCameraOn =
        false;

    cameraButton.innerText =
        "📷 ВКЛ";

    try {

        await fetch(
            "/camera/stop",
            {
                method:
                    "POST"
            }
        );

    }

    catch (error) {

        console.error(
            "Camera stop error:",
            error
        );
    }

    status.innerText =
        "SYSTEM ONLINE";

    addMessage(
        "bot",
        "JARVIS",
        "Камера выключена."
    );
}


// ========================================================
// CAMERA BUTTON
// ========================================================

cameraButton.addEventListener(
    "click",
    async function() {

        if (isCameraOn) {

            await stopCameraStream();

            return;
        }

        await startCameraStream();
    }
);


// ========================================================
// MICROPHONE
// ========================================================

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


if (SpeechRecognition) {

    recognition =
        new SpeechRecognition();

    recognition.continuous =
        false;

    recognition.interimResults =
        false;

    recognition.maxAlternatives =
        1;


    // ====================================================
    // MICROPHONE START
    // ====================================================

    recognition.onstart =
        function() {

            isListening =
                true;

            micButton.innerText =
                "🔴 ВЫКЛ";

            status.innerText =
                "🎤 JARVIS LISTENING...";

            console.log(
                "🎤 Микрофон включён"
            );
        };


    // ====================================================
    // MICROPHONE RESULT
    // ====================================================

    recognition.onresult =
        function(event) {

            if (
                !event.results ||
                !event.results.length
            ) {
                return;
            }

            const result =
                event.results[
                    event.results.length - 1
                ];

            if (
                !result ||
                !result[0]
            ) {
                return;
            }

            const text =
                result[0]
                    .transcript
                    .trim();

            console.log(
                "🎤 Распознано:",
                text
            );

            if (!text) {
                return;
            }

            input.value =
                text;

            sendMessage();
        };


    // ====================================================
    // MICROPHONE ERROR
    // ====================================================

    recognition.onerror =
        function(event) {

            console.error(
                "MIC ERROR:",
                event.error
            );

            isListening =
                false;

            micButton.innerText =
                "🎤 ВКЛ";

            let message =
                "Ошибка микрофона.";

            if (
                event.error
                ===
                "not-allowed"
            ) {

                message =
                    "Доступ к микрофону запрещён. Разреши микрофон в браузере.";
            }

            else if (
                event.error
                ===
                "no-speech"
            ) {

                message =
                    "Речь не обнаружена.";
            }

            else if (
                event.error
                ===
                "audio-capture"
            ) {

                message =
                    "Микрофон не найден или занят.";
            }

            status.innerText =
                "❌ " + message;
        };


    // ====================================================
    // MICROPHONE END
    // ====================================================

    recognition.onend =
        function() {

            isListening =
                false;

            micButton.innerText =
                "🎤 ВКЛ";

            console.log(
                "🎤 Микрофон выключен"
            );

            if (
                status.innerText
                    .includes(
                        "LISTENING"
                    )
            ) {

                status.innerText =
                    "SYSTEM ONLINE";
            }
        };


    // ====================================================
    // MICROPHONE BUTTON
    // ====================================================

    micButton.addEventListener(
        "click",
        function() {

            // ВЫКЛ
            if (isListening) {

                try {

                    recognition.stop();

                }

                catch (error) {

                    console.error(
                        error
                    );
                }

                return;
            }


            // ВКЛ
            try {

                const selected =
                    languageSelect.value;


                if (
                    selected === "auto"
                ) {

                    recognition.lang =
                        "ru-RU";

                }

                else {

                    recognition.lang =
                        selected;
                }


                console.log(
                    "🎤 Язык:",
                    recognition.lang
                );


                recognition.start();

            }

            catch (error) {

                console.error(
                    "Microphone start error:",
                    error
                );

                status.innerText =
                    "❌ MICROPHONE ERROR";
            }
        }
    );

}

else {

    micButton.disabled =
        true;

    micButton.innerText =
        "🎤 НЕТ";

    status.innerText =
        "❌ Speech Recognition не поддерживается";
}


// ========================================================
// PAGE CLOSE
// ========================================================

window.addEventListener(
    "beforeunload",
    function() {

        if (isCameraOn) {

            navigator.sendBeacon(
                "/camera/stop"
            );
        }
    }
);


// ========================================================
// INITIAL MESSAGE
// ========================================================

window.addEventListener(
    "load",
    function() {

        setTimeout(
            function() {

                addMessage(
                    "bot",
                    "JARVIS",
                    "Система JARVIS активна. Готов к работе."
                );

            },
            300
        );

    }
);

</script>

</body>

</html>
"""
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    print()
    print("=" * 70)
    print("🤖 JARVIS AI STARTING")
    print("=" * 70)
    print()
    print(
        "Открой:"
    )
    print(
        "http://127.0.0.1:9013"
    )
    print()
    print("=" * 70)
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9013,
        reload=False
    )

