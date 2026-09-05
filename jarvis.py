import os
import json
import platform
import re
import shutil
import subprocess
import webbrowser
import threading
import time

from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
from dotenv import load_dotenv

from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse

import warnings

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning
)


# ============================================================
# OPTIONAL: OPENCV
# ============================================================

try:
    import cv2
except ImportError:
    cv2 = None


# ============================================================
# OPTIONAL: YOLO
# ============================================================

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

GROQ_URL = os.getenv(
    "GROQ_URL",
    "https://api.groq.com/openai/v1/chat/completions"
)

MAX_HISTORY = 10

conversation_history = []

app = FastAPI(
    title="JARVIS AI",
    version="2.0"
)


# ============================================================
# STARTUP
# ============================================================

print()
print("=" * 70)
print("🤖 JARVIS AI")
print("=" * 70)

print(
    "Python:",
    platform.python_version()
)

print(
    "Project:",
    BASE_DIR
)

print(
    "Groq model:",
    GROQ_MODEL
)

if GROQ_API_KEY:
    print("Groq API key: найден")
else:
    print("WARNING: GROQ_API_KEY не найден в .env")

print("=" * 70)
print()


# ============================================================
# CAMERA
# ============================================================

camera = None
camera_lock = threading.Lock()


# ============================================================
# YOLO
# ============================================================

model = None


def load_yolo():
    global model

    if YOLO is None:
        print("YOLO: ultralytics не установлен.")
        return

    try:
        model = YOLO("yolov8n.pt")
        print("YOLO: модель загружена.")
    except Exception as e:
        print("YOLO: модель не загружена:", e)
        model = None


load_yolo()


# ============================================================
# WINDOWS APPLICATIONS
# ============================================================

def get_start_menu_locations():

    locations = []

    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")

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

    name = str(name).lower().strip()

    for extension in (
        ".lnk",
        ".url",
        ".exe"
    ):
        if name.endswith(extension):
            name = name[:-len(extension)]

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

                    name = normalize_app_name(item.stem)

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

    application = str(application).strip()

    if not application:
        return None

    name = application.lower().strip()

    if name.endswith(".exe"):
        name = name[:-4]

    if name in SYSTEM_APPS:
        return SYSTEM_APPS[name]

    for app_name, path in ALLOWED_APPS.items():

        clean_name = (
            str(app_name)
            .lower()
            .strip()
        )

        if clean_name.endswith(".exe"):
            clean_name = clean_name[:-4]

        if name == clean_name:
            return path

    try:

        found = shutil.which(application)

        if found:
            return found

        found = shutil.which(application + ".exe")

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

        Path.home() / "AppData" / "Local",

        Path.home() / "AppData" / "Roaming",

        Path.home() / "Desktop",

        Path(
            os.environ.get(
                "APPDATA",
                ""
            )
        ) / "Microsoft" / "Windows" / "Start Menu" / "Programs",

        Path(
            os.environ.get(
                "PROGRAMDATA",
                ""
            )
        ) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]

    for location in locations:

        if not location.exists():
            continue

        try:

            for exe in location.rglob("*.exe"):

                if exe.stem.lower() == name:
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

def open_application(application: str):

    application = str(application).strip()

    if not application:

        return {
            "success": False,
            "message": "Название приложения не указано."
        }

    print("Поиск приложения:", application)

    program = find_application(application)

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

            os.startfile(program)

        else:

            directory = os.path.dirname(program)

            if directory:

                subprocess.Popen(
                    [program],
                    cwd=directory,
                    shell=False
                )

            else:

                subprocess.Popen(
                    [program],
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
        "applications": sorted(ALLOWED_APPS.keys())
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
        ) / "Steam" / "steam.exe",

        Path(
            os.environ.get(
                "PROGRAMFILES",
                r"C:\Program Files"
            )
        ) / "Steam" / "steam.exe",

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

        found = shutil.which("steam.exe")

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

            "system": platform.system(),

            "release": platform.release(),

            "version": platform.version(),

            "machine": platform.machine(),

            "processor": platform.processor(),

            "computer_name": platform.node(),

            "cpu_count": os.cpu_count(),

            "disk_total_gb":
                round(total / 1024 ** 3, 2),

            "disk_used_gb":
                round(used / 1024 ** 3, 2),

            "disk_free_gb":
                round(free / 1024 ** 3, 2)
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

    query = str(query).strip()

    if not query:

        return {
            "success": False,
            "message": "Название видео не указано."
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
                "User-Agent": "Mozilla/5.0"
            }
        ) as client:

            response = client.get(search_url)

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
                unique_video_ids.append(video_id)

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

    query = str(query).strip()

    if not query:

        return {
            "success": False,
            "message": "Поисковый запрос пустой."
        }

    try:

        url = (
            "https://yandex.ru/search/?text="
            + quote(query, safe="")
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

    query = str(query).strip()

    if not query:

        return {
            "success": False,
            "message": "Название фильма не указано."
        }

    try:

        movie_query = f"{query} смотреть фильм"

        url = (
            "https://yandex.ru/search/?text="
            + quote(movie_query, safe="")
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

    "youtube": "https://www.youtube.com",
    "ютуб": "https://www.youtube.com",

    "google": "https://www.google.com",
    "гугл": "https://www.google.com",

    "yandex": "https://yandex.ru",
    "яндекс": "https://yandex.ru",

    "vk": "https://vk.com",
    "вк": "https://vk.com",

    "telegram": "https://web.telegram.org",
    "телеграм": "https://web.telegram.org",
}


def open_website(url: str):

    url = str(url).strip()

    if not url:

        return {
            "success": False,
            "message": "URL пустой."
        }

    if url.lower() in KNOWN_WEBSITES:

        url = KNOWN_WEBSITES[
            url.lower()
        ]

    if not url.startswith(
        ("http://", "https://")
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

    path = os.path.expanduser(path)

    if path.lower() in KNOWN_FOLDERS:

        path = str(
            KNOWN_FOLDERS[
                path.lower()
            ]
        )

    if not path:

        return {
            "success": False,
            "message": "Путь не указан."
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

                "name": item.name,

                "type":
                    "folder"
                    if item.is_dir()
                    else "file"
            })

        return {

            "success": True,

            "path": str(downloads),

            "items": files[:100]
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

    filename = (
        str(filename)
        .lower()
        .strip()
    )

    if not filename:

        return {
            "success": False,
            "message":
                "Имя файла не указано."
        }

    search_locations = [

        Path.home() / "Downloads",

        Path.home() / "Desktop",

        Path.home() / "Documents",
    ]

    results = []

    for location in search_locations:

        if not location.exists():
            continue

        try:

            for path in location.rglob("*"):

                if filename in path.name.lower():

                    results.append(str(path))

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

    url = str(url).strip()

    if not url:

        return {
            "success": False,
            "message": "URL не указан."
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

                content_length = response.headers.get(
                    "content-length"
                )

                if content_length:

                    try:
                        size = int(content_length)
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

                        downloaded += len(chunk)

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

    target = str(target).strip()
    target_type = str(target_type).lower().strip()

    if not target:

        return {
            "success": False,
            "message":
                "Не указано, что нужно открыть."
        }

    if target_type == "movie":

        return search_yandex_movie(target)

    if target_type == "application":

        if target.lower() in (
            "steam",
            "стим"
        ):
            return open_steam()

        return open_application(target)

    if target_type == "website":

        return open_website(target)

    if target_type == "youtube":

        return play_youtube(target)

    if target_type == "file":

        result = find_file(target)

        if not result.get("success"):
            return result

        files = result.get("results", [])

        if not files:

            return {
                "success": False,
                "message":
                    f"Файл '{target}' не найден."
            }

        try:

            os.startfile(files[0])

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

        return open_folder(target)

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
                    return play_youtube(query)

        application = find_application(target)

        if application:

            return open_application(target)

        file_result = find_file(target)

        if file_result.get("success"):

            files = file_result.get(
                "results",
                []
            )

            if files:

                try:

                    os.startfile(files[0])

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

        if camera is None or not camera.isOpened():

            print("Открываем камеру...")

            camera = cv2.VideoCapture(
                0,
                cv2.CAP_DSHOW
            )

            if not camera.isOpened():

                camera = cv2.VideoCapture(0)

            if not camera.isOpened():

                print("Камера не открылась.")

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

            print("Камера открыта.")

        return camera


def release_camera():

    global camera

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

    print("Камера освобождена.")


def start_camera():

    cam = get_camera()

    if cam is None:

        return {
            "success": False,
            "message":
                "Камера не найдена или не может быть открыта."
        }

    return {
        "success": True,
        "message":
            "Камера запущена. Открой раздел камеры."
    }


def generate_camera_frames():

    while True:

        cam = get_camera()

        if cam is None:

            time.sleep(1)
            continue

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
                                max(y1 - 10, 20)
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

    return StreamingResponse(
        generate_camera_frames(),
        media_type=(
            "multipart/x-mixed-replace;"
            " boundary=frame"
        )
    )


# ============================================================
# TOOLS
# ============================================================

TOOLS = [

    {
        "type": "function",

        "function": {

            "name": "get_pc_info",

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

            "name": "get_applications",

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

            "name": "open_requested",

            "description":
                "Открыть приложение, Steam, сайт, "
                "YouTube, фильм, файл или папку.",

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

            "name": "search_yandex",

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

            "name": "get_downloads",

            "description":
                "Получить содержимое Downloads.",

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

            "name": "find_file",

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

            "name": "download_file",

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

            "name": "start_camera",

            "description":
                "Запустить локальную камеру компьютера.",

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
# GROQ
# ============================================================

async def ask_groq(text: str):

    if not GROQ_API_KEY:

        return {
            "answer":
                "GROQ_API_KEY не найден. "
                "Проверь файл .env.",
            "action": "none",
            "query": ""
        }

    system_message = """
Ты JARVIS — интеллектуальный локальный AI-помощник.

Ты должен вести себя как современный голосовой ассистент.

ГЛАВНОЕ:

1. Отвечай на языке пользователя.

2. Если пользователь пишет по-русски — отвечай по-русски.

3. Если пользователь пишет на английском — отвечай на английском.

4. Если пользователь использует другой язык — отвечай на этом языке,
   если ты способен его поддерживать.

5. Пользователь может попросить тебя ПЕРЕВЕСТИ текст.
   В таком случае переводи максимально точно.

6. Поддерживай перевод между любыми языками,
   которые поддерживает используемая AI-модель.

7. При переводе не добавляй лишних объяснений,
   если пользователь их не просил.

8. Сохраняй смысл, стиль и структуру оригинала.

9. Если пользователь явно указывает язык перевода,
   переводи именно на него.

10. Если пользователь говорит:
    "переведи на английский",
    "translate to English",
    "переведи на китайский",
    "translate this to Spanish"
    и т.п. — выполняй перевод.

11. Если пользователь просит произнести текст,
    просто верни текст, который нужно произнести.

ВОЗМОЖНОСТИ:

- обычный разговор;
- ответы на вопросы;
- перевод;
- многоязычное общение;
- информация о компьютере;
- запуск приложений;
- запуск Steam;
- открытие сайтов;
- поиск через Яндекс;
- YouTube;
- музыка;
- видео;
- фильмы;
- поиск файлов;
- открытие файлов;
- открытие папок;
- просмотр Downloads;
- скачивание файлов;
- локальная камера.

ПРАВИЛА ИНСТРУМЕНТОВ:

1. Если для действия нужен инструмент — используй инструмент.

2. Не говори, что действие выполнено,
   пока инструмент не вернул результат.

3. Если success=true — сообщи результат.

4. Если success=false — не говори,
   что действие выполнено.

5. Для информации о компьютере используй get_pc_info.

6. Для запуска приложения используй open_requested
   с target_type="application".

7. Для сайта используй target_type="website".

8. Для YouTube используй target_type="youtube".

9. Для фильма используй target_type="movie".

10. Для файла используй target_type="file".

11. Для папки используй target_type="folder".

12. Если пользователь говорит "открой X",
    используй open_requested с target_type="auto".

13. Для Steam используй open_requested
    или target_type="application".

14. Для музыки, песни, видео или ролика
    используй YouTube.
15. Если пользователь просит посмотреть, найти или открыть фильм,
используй open_requested с target_type="movie".

16. Если пользователь говорит:
"включи фильм X",
"запусти фильм X",
"найди фильм X",
"хочу посмотреть X",
"покажи фильм X",
то используй open_requested с target_type="movie".

17. Для фильма обязательно передавай только название фильма
в параметре target, без слов "фильм", "посмотреть" и т.п.

18. Для скачивания используй download_file.

19. Для камеры используй start_camera.

20. Камера является локальной камерой компьютера.

БЕЗОПАСНОСТЬ:

- Не выполняй распознавание личности.
- Не выполняй распознавание лиц.
- Не используй камеру для слежки.
- Не удаляй файлы.
- Не форматируй диски.
- Не отключай антивирус.
- Не выполняй опасные системные операции.

После выполнения инструмента отвечай кратко.
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

    messages.append({

        "role": "user",
        "content": text

    })


    headers = {

        "Authorization":
            f"Bearer {GROQ_API_KEY}",

        "Content-Type":
            "application/json"
    }


    data = {

        "model": GROQ_MODEL,

        "messages": messages,

        "tools": TOOLS,

        "tool_choice": "auto",

        "temperature": 0.2
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

                "action": "none",

                "query": ""
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
            "tool_calls",
            []
        )


        # ====================================================
        # TOOL CALL
        # ====================================================

        if tool_calls:

            messages.append(message)

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

                except json.JSONDecodeError:

                    arguments = {}


                print()
                print(
                    "JARVIS TOOL:",
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


                messages.append({

                    "role": "tool",

                    "tool_call_id":
                        tool_call.get(
                            "id",
                            ""
                        ),

                    "name": name,

                    "content":
                        json.dumps(
                            tool_result,
                            ensure_ascii=False
                        )
                })


            # =================================================
            # SECOND GROQ REQUEST
            # =================================================

            second_data = {

                "model": GROQ_MODEL,

                "messages": messages,

                "tools": TOOLS,

                "tool_choice": "none",

                "temperature": 0.2
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
                        "Инструмент выполнен, "
                        "но Groq не смог сформировать "
                        "финальный ответ.",

                    "action": "none",

                    "query": ""
                }


            try:

                second_result = (
                    second_response.json()
                )

            except json.JSONDecodeError:

                return {

                    "answer":
                        "Groq вернул некорректный ответ.",

                    "action": "none",

                    "query": ""
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
                message.get("content")
                or "Не удалось получить ответ."
            )


        answer = answer.strip()


        # ====================================================
        # MEMORY
        # ====================================================

        conversation_history.append({

            "role": "user",

            "content": text
        })


        conversation_history.append({

            "role": "assistant",

            "content": answer
        })


        while len(conversation_history) > MAX_HISTORY:

            conversation_history.pop(0)


        return {

            "answer": answer,

            "action": "none",

            "query": ""
        }


    except httpx.HTTPError as e:

        print(
            "HTTP error:",
            repr(e)
        )

        return {

            "answer":
                f"Ошибка подключения к Groq: {e}",

            "action": "none",

            "query": ""
        }


    except Exception as e:

        print(
            "ask_groq error:",
            repr(e)
        )

        return {

            "answer":
                f"Произошла ошибка: {e}",

            "action": "none",

            "query": ""
        }


# ============================================================
# CHAT API
# ============================================================

@app.post("/chat")
async def chat(
    text: str = Form(...)
):

    result = await ask_groq(text)

    return JSONResponse(result)


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

<link
    rel="icon"
    href="data:image/svg+xml,
    <svg xmlns='http://www.w3.org/2000/svg'
    viewBox='0 0 100 100'>
    <text y='.9em' font-size='90'>🤖</text>
    </svg>"
>

<style>

/* =========================================================
   JARVIS / IRON MAN STYLE
   ========================================================= */

:root {

    --blue: #00d9ff;
    --blue2: #008cff;

    --red: #ff1744;
    --red2: #ff4b2b;

    --cyan: #00ffff;

    --bg: #02050a;

    --panel:
        rgba(5, 15, 27, 0.88);

    --border:
        rgba(0, 217, 255, .45);
}


/* =========================================================
   GLOBAL
   ========================================================= */

* {
    box-sizing: border-box;
}


html,
body {

    margin: 0;

    width: 100%;

    min-height: 100%;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background:
        #02050a;

    color: white;
}


/* =========================================================
   IRON MAN BACKGROUND
   ========================================================= */

body {

    min-height: 100vh;

    overflow-x: hidden;

    background:

        radial-gradient(
            circle at 50% 30%,
            rgba(0, 150, 255, .15),
            transparent 30%
        ),

        radial-gradient(
            circle at 15% 80%,
            rgba(255, 0, 50, .08),
            transparent 30%
        ),

        radial-gradient(
            circle at 85% 80%,
            rgba(0, 200, 255, .08),
            transparent 30%
        ),

        linear-gradient(
            135deg,
            #02050a,
            #06101c 50%,
            #02050a
        );
}


/* =========================================================
   GRID
   ========================================================= */

body::before {

    content: "";

    position: fixed;

    inset: 0;

    pointer-events: none;

    opacity: .16;

    background-image:

        linear-gradient(
            rgba(0, 217, 255, .12) 1px,
            transparent 1px
        ),

        linear-gradient(
            90deg,
            rgba(0, 217, 255, .12) 1px,
            transparent 1px
        );

    background-size:
        45px 45px;

    mask-image:
        linear-gradient(
            to bottom,
            black,
            transparent
        );

    z-index: 0;
}


/* =========================================================
   SCANLINE
   ========================================================= */

body::after {

    content: "";

    position: fixed;

    left: 0;
    right: 0;

    height: 2px;

    background:
        linear-gradient(
            90deg,
            transparent,
            rgba(0, 217, 255, .7),
            transparent
        );

    animation:
        scan 5s linear infinite;

    pointer-events: none;

    z-index: 50;
}


@keyframes scan {

    0% {
        top: 0;
    }

    100% {
        top: 100%;
    }
}


/* =========================================================
   CONTAINER
   ========================================================= */

.container {

    position: relative;

    z-index: 2;

    width: min(
        1100px,
        calc(100% - 30px)
    );

    margin: 0 auto;

    padding:
        25px 0 50px;
}


/* =========================================================
   HEADER
   ========================================================= */

.header {

    position: relative;

    text-align: center;

    padding: 25px;

    margin-bottom: 20px;

    border:
        1px solid
        var(--border);

    border-radius: 20px;

    background:
        linear-gradient(
            135deg,
            rgba(0, 25, 45, .9),
            rgba(2, 8, 15, .9)
        );

    box-shadow:

        0 0 30px
        rgba(0, 217, 255, .15),

        inset 0 0 30px
        rgba(0, 217, 255, .03);
}


/* =========================================================
   ROBOT ICON
   ========================================================= */

.robot {

    font-size: 75px;

    line-height: 1;

    margin-bottom: 10px;

    filter:
        drop-shadow(
            0 0 15px
            rgba(0, 217, 255, .8)
        );

    animation:
        robotPulse 2s ease-in-out infinite;
}


@keyframes robotPulse {

    0%,
    100% {
        transform: scale(1);
    }

    50% {
        transform: scale(1.06);
    }
}


/* =========================================================
   TITLE
   ========================================================= */

h1 {

    margin: 0;

    color: var(--blue);

    font-size:
        clamp(35px, 6vw, 60px);

    letter-spacing: 8px;

    text-shadow:

        0 0 8px
        var(--blue),

        0 0 25px
        rgba(0, 217, 255, .8);
}


.subtitle {

    margin-top: 10px;

    color: #8ba8b8;

    letter-spacing: 3px;

    text-transform: uppercase;

    font-size: 13px;
}


/* =========================================================
   STATUS
   ========================================================= */

.status-panel {

    display: flex;

    justify-content: center;

    align-items: center;

    gap: 10px;

    margin: 15px 0;

    color: #8ea6b6;

    font-size: 13px;
}


.status-dot {

    width: 10px;

    height: 10px;

    border-radius: 50%;

    background: #00ff9d;

    box-shadow:
        0 0 12px #00ff9d;

    animation:
        statusPulse 1.5s infinite;
}


@keyframes statusPulse {

    0%,
    100% {
        opacity: 1;
    }

    50% {
        opacity: .35;
    }
}


/* =========================================================
   CONTROLS
   ========================================================= */

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

    width: 100%;

    padding: 16px;

    border-radius: 12px;

    border:
        1px solid
        rgba(0, 217, 255, .35);

    background:
        rgba(3, 13, 23, .9);

    color: white;

    font-size: 16px;

    outline: none;

    transition: .2s;
}


input:focus,
select:focus {

    border-color:
        var(--blue);

    box-shadow:
        0 0 18px
        rgba(0, 217, 255, .2);
}


select {

    max-width: 170px;

    cursor: pointer;
}


/* =========================================================
   BUTTONS
   ========================================================= */

button {

    padding:
        12px 18px;

    border: 1px solid
        rgba(0, 217, 255, .4);

    border-radius: 12px;

    color: white;

    cursor: pointer;

    font-size: 15px;

    background:
        rgba(0, 40, 65, .8);

    transition:
        transform .15s,
        box-shadow .15s,
        background .15s;
}


button:hover {

    transform:
        translateY(-2px);

    box-shadow:
        0 0 20px
        rgba(0, 217, 255, .25);
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


/* =========================================================
   LANGUAGE PANEL
   ========================================================= */

.language-panel {

    display: flex;

    justify-content: center;

    align-items: center;

    gap: 10px;

    margin:
        10px 0 20px;

    color: #78909c;

    font-size: 13px;
}


.language-panel select {

    width: auto;

    max-width: 220px;

    padding: 9px 12px;

    font-size: 13px;
}


/* =========================================================
   CHAT
   ========================================================= */

#chat {

    display: flex;

    flex-direction: column;

    gap: 15px;

    min-height: 150px;
}


.message {

    position: relative;

    padding: 16px 18px;

    border-radius: 15px;

    line-height: 1.55;

    white-space: pre-wrap;

    animation:
        messageIn .25s ease-out;
}


@keyframes messageIn {

    from {
        opacity: 0;
        transform:
            translateY(8px);
    }

    to {
        opacity: 1;
        transform:
            translateY(0);
    }
}


.message b {

    display: block;

    margin-bottom: 6px;

    font-size: 12px;

    letter-spacing: 2px;

    text-transform: uppercase;
}


.user {

    align-self: flex-end;

    max-width: 80%;

    background:
        linear-gradient(
            135deg,
            rgba(0, 78, 170, .8),
            rgba(0, 40, 90, .8)
        );

    border:
        1px solid
        rgba(0, 150, 255, .45);

    box-shadow:
        0 0 20px
        rgba(0, 100, 255, .08);
}


.user b {

    color: #58c7ff;
}


.bot {

    align-self: flex-start;

    max-width: 90%;

    background:
        linear-gradient(
            135deg,
            rgba(15, 28, 40, .95),
            rgba(5, 15, 25, .95)
        );

    border:
        1px solid
        rgba(0, 217, 255, .3);

    box-shadow:
        0 0 25px
        rgba(0, 217, 255, .08);
}


.bot b {

    color: var(--blue);
}


/* =========================================================
   CAMERA
   ========================================================= */

.camera {

    display: none;

    margin-top: 25px;

    overflow: hidden;

    border:
        1px solid
        rgba(0, 217, 255, .4);

    border-radius: 18px;

    background: #000;

    box-shadow:
        0 0 35px
        rgba(0, 217, 255, .12);
}


.camera-title {

    padding: 12px;

    text-align: center;

    color: var(--blue);

    background:
        rgba(0, 25, 40, .9);

    letter-spacing: 3px;
}


.camera img {

    display: block;

    width: 100%;
}


/* =========================================================
   ARC REACTOR
   ========================================================= */

.reactor {

    width: 80px;

    height: 80px;

    margin:
        20px auto 0;

    border-radius: 50%;

    border:
        3px solid
        rgba(0, 217, 255, .6);

    box-shadow:

        0 0 10px
        #00d9ff,

        0 0 30px
        rgba(0, 217, 255, .6),

        inset 0 0 20px
        rgba(0, 217, 255, .6);

    position: relative;

    animation:
        reactor 2s linear infinite;
}


.reactor::before {

    content: "";

    position: absolute;

    inset: 12px;

    border-radius: 50%;

    border:
        3px solid
        #ffffff;

    box-shadow:
        0 0 20px
        #00d9ff;
}


@keyframes reactor {

    from {
        transform:
            rotate(0deg);
    }

    to {
        transform:
            rotate(360deg);
    }
}


/* =========================================================
   FOOTER
   ========================================================= */

.footer {

    text-align: center;

    color: #455a64;

    font-size: 11px;

    margin-top: 30px;

    letter-spacing: 2px;
}


/* =========================================================
   MOBILE
   ========================================================= */

@media (max-width: 750px) {

    .controls {

        grid-template-columns:
            1fr 1fr;
    }

    .controls input {

        grid-column:
            1 / -1;
    }

    select {

        max-width: none;
    }

    .user,
    .bot {

        max-width: 95%;
    }
}

</style>

</head>


<body>


<div class="container">


<!-- =====================================================
     HEADER
     ===================================================== -->

<div class="header">

    <div class="robot">
        🤖
    </div>

    <h1>
        JARVIS
    </h1>

    <div class="subtitle">
        Artificial Intelligence System
    </div>

    <div class="reactor"></div>

</div>


<!-- =====================================================
     STATUS
     ===================================================== -->

<div class="status-panel">

    <span class="status-dot"></span>

    <span id="status">
        SYSTEM ONLINE
    </span>

</div>


<!-- =====================================================
     CONTROLS
     ===================================================== -->

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
    🎤
</button>


<button id="cameraButton">
    📷
</button>


</div>


<!-- =====================================================
     LANGUAGE
     ===================================================== -->

<div class="language-panel">

    <span>
        🎤 Язык микрофона:
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

        <option value="pt-PT">
            Português
        </option>

        <option value="zh-CN">
            中文
        </option>

        <option value="ja-JP">
            日本語
        </option>

        <option value="ko-KR">
            한국어
        </option>

        <option value="tr-TR">
            Türkçe
        </option>

        <option value="ar-SA">
            العربية
        </option>

        <option value="hi-IN">
            हिन्दी
        </option>

    </select>

</div>


<!-- =====================================================
     CHAT
     ===================================================== -->

<div id="chat"></div>


<!-- =====================================================
     CAMERA
     ===================================================== -->

<div
    id="cameraContainer"
    class="camera"
>

    <div class="camera-title">
        ◉ JARVIS VISION SYSTEM
    </div>

    <img
        id="cameraImage"
        src="/camera"
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
    document.getElementById(
        "text"
    );


const chat =
    document.getElementById(
        "chat"
    );


const status =
    document.getElementById(
        "status"
    );


const cameraContainer =
    document.getElementById(
        "cameraContainer"
    );


const cameraButton =
    document.getElementById(
        "cameraButton"
    );


const languageSelect =
    document.getElementById(
        "speechLanguage"
    );


// ========================================================
// ESCAPE HTML
// ========================================================

function escapeHtml(text) {

    const div =
        document.createElement(
            "div"
        );

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
// LANGUAGE DETECTION FOR TTS
// ========================================================

function detectLanguage(text) {

    if (!text) {
        return "ru-RU";
    }


    // Cyrillic
    if (/[А-Яа-яЁё]/.test(text)) {

        if (/[ӘәҒғҚқҢңӨөҰұҮүІі]/.test(text)) {
            return "kk-KZ";
        }

        if (/[ЇїІіЄєҐґ]/.test(text)) {
            return "uk-UA";
        }

        return "ru-RU";
    }


    // Arabic
    if (/[\u0600-\u06FF]/.test(text)) {
        return "ar-SA";
    }


    // Chinese
    if (/[\u4E00-\u9FFF]/.test(text)) {
        return "zh-CN";
    }


    // Japanese
    if (/[\u3040-\u30FF]/.test(text)) {
        return "ja-JP";
    }


    // Korean
    if (/[\uAC00-\uD7AF]/.test(text)) {
        return "ko-KR";
    }


    // Hindi
    if (/[\u0900-\u097F]/.test(text)) {
        return "hi-IN";
    }


    // Greek
    if (/[\u0370-\u03FF]/.test(text)) {
        return "el-GR";
    }


    // Hebrew
    if (/[\u0590-\u05FF]/.test(text)) {
        return "he-IL";
    }


    // Latin languages:
    // Browser voice selection will choose the closest voice.

    return "en-US";
}


// ========================================================
// SPEECH SYNTHESIS
// ========================================================

let availableVoices = [];


function loadVoices() {

    if (!("speechSynthesis" in window)) {
        return;
    }

    availableVoices =
        speechSynthesis.getVoices();

    console.log(
        "Доступные голоса:",
        availableVoices
    );
}


if ("speechSynthesis" in window) {

    loadVoices();

    speechSynthesis.onvoiceschanged =
        loadVoices;
}


function detectLanguage(text) {

    if (!text) {
        return "ru-RU";
    }


    if (/[А-Яа-яЁё]/.test(text)) {

        if (
            /[ӘәҒғҚқҢңӨөҰұҮүІі]/.test(text)
        ) {
            return "kk-KZ";
        }

        if (
            /[ЇїІіЄєҐґ]/.test(text)
        ) {
            return "uk-UA";
        }

        return "ru-RU";
    }


    if (/[\u0600-\u06FF]/.test(text)) {
        return "ar-SA";
    }


    if (/[\u4E00-\u9FFF]/.test(text)) {
        return "zh-CN";
    }


    if (/[\u3040-\u30FF]/.test(text)) {
        return "ja-JP";
    }


    if (/[\uAC00-\uD7AF]/.test(text)) {
        return "ko-KR";
    }


    if (/[\u0900-\u097F]/.test(text)) {
        return "hi-IN";
    }


    return "en-US";
}


function speak(text) {

    if (!("speechSynthesis" in window)) {

        console.error(
            "Speech Synthesis не поддерживается."
        );

        return;
    }


    if (!text || !text.trim()) {
        return;
    }


    console.log(
        "JARVIS говорит:",
        text
    );


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


    // Обновляем список голосов
    loadVoices();


    const languageCode =
        lang
            .toLowerCase()
            .split("-")[0];


    let voice =
        availableVoices.find(
            v =>
                v.lang &&
                v.lang
                    .toLowerCase()
                    .startsWith(
                        languageCode
                    )
        );


    // Если русского голоса нет,
    // пробуем любой доступный голос
    if (!voice) {

        voice =
            availableVoices.find(
                v =>
                    v.lang &&
                    v.lang
                        .toLowerCase()
                        .startsWith("ru")
            );
    }


    if (voice) {

        console.log(
            "Выбран голос:",
            voice.name,
            voice.lang
        );

        utterance.voice =
            voice;

    } else {

        console.warn(
            "Русский голос не найден."
        );
    }


    utterance.onstart =
        function() {

            console.log(
                "JARVIS начал говорить"
            );

            status.innerText =
                "🔊 JARVIS SPEAKING...";
        };


    utterance.onend =
        function() {

            console.log(
                "JARVIS закончил говорить"
            );

            status.innerText =
                "SYSTEM ONLINE";
        };


    utterance.onerror =
        function(event) {

            console.error(
                "Ошибка TTS:",
                event
            );

            status.innerText =
                "❌ TTS ERROR";
        };


    speechSynthesis.speak(
        utterance
    );
}


// ========================================================
// LOAD VOICES
// ========================================================

if ("speechSynthesis" in window) {

    speechSynthesis.onvoiceschanged =
        function() {

            speechSynthesis.getVoices();

        };
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


        // Автоматически говорит ответ
        speak(answer);


    }

    catch (error) {

        console.error(error);


        status.innerText =
            "❌ SYSTEM ERROR";


        addMessage(
            "bot",
            "JARVIS",
            "Ошибка соединения: " +
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
// SPEECH RECOGNITION
// ========================================================

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


let recognition = null;


if (SpeechRecognition) {

    recognition =
        new SpeechRecognition();


    recognition.continuous =
        false;


    recognition.interimResults =
        false;


    recognition.onstart =
        function() {

            status.innerText =
                "🎤 JARVIS LISTENING...";

        };


    recognition.onresult =
        function(event) {

            const text =
                event
                    .results[0][0]
                    .transcript;


            input.value =
                text;


            sendMessage();

        };


    recognition.onerror =
        function(event) {

            console.error(
                event.error
            );


            status.innerText =
                "❌ MICROPHONE ERROR";

        };


    recognition.onend =
        function() {

            if (
                status.innerText ===
                "🎤 JARVIS LISTENING..."
            ) {

                status.innerText =
                    "SYSTEM ONLINE";

            }

        };


    document
        .getElementById("mic")
        .addEventListener(
            "click",
            function() {

                try {

                    const selected =
                        languageSelect.value;


                    if (
                        selected === "auto"
                    ) {

                        recognition.lang =
                            navigator.language ||
                            "en-US";

                    }

                    else {

                        recognition.lang =
                            selected;

                    }


                    recognition.start();

                }

                catch (error) {

                    console.log(
                        error
                    );

                }

            }
        );

}

else {

    document
        .getElementById("mic")
        .disabled = true;

    status.innerText =
        "Speech Recognition недоступен в этом браузере";

}


// ========================================================
// CAMERA
// ========================================================

cameraButton.addEventListener(
    "click",
    async function() {

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
                                "запусти камеру"
                            )
                    }
                );


            const data =
                await response.json();


            if (data.answer) {

                addMessage(
                    "bot",
                    "JARVIS",
                    data.answer
                );

                speak(
                    data.answer
                );

            }


            cameraContainer.style.display =
                "block";


        }

        catch (error) {

            console.error(
                error
            );

            cameraContainer.style.display =
                "block";

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
# SHUTDOWN
# ============================================================

@app.on_event("shutdown")
def shutdown_event():

    print()
    print("Остановка JARVIS...")

    release_camera()

    print("JARVIS остановлен.")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    import uvicorn

    print()
    print("=" * 70)
    print("🤖 JARVIS AI STARTING")
    print("=" * 70)
    print()
    print("Адрес:")
    print("http://127.0.0.1:9013")
    print()
    print("Открой этот адрес в браузере.")
    print("=" * 70)
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9013,
        reload=False
    )
