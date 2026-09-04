import os
import json
import platform
import re
import shutil
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
import cv2

from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse
from starlette.responses import HTMLResponse, JSONResponse

from ultralytics import YOLO


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

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

app = FastAPI(title="My Jarvis")


# ============================================================
# GROQ CHECK
# ============================================================

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY не найден в .env")
else:
    print("Groq API key найден")


# ============================================================
# CAMERA + YOLO
# ============================================================

import cv2
from ultralytics import YOLO


# Загружаем модель YOLO
# При первом запуске модель автоматически скачается.
YOLO_MODEL = "yolo11n.pt"

try:
    model = YOLO(YOLO_MODEL)
    print("YOLO модель загружена:", YOLO_MODEL)
except Exception as e:
    model = None
    print("Ошибка загрузки YOLO:", repr(e))


def find_working_camera():

    print()
    print("==============================")
    print("ПОИСК КАМЕРЫ")
    print("==============================")

    # Пробуем индексы камер от 0 до 4
    for camera_index in range(5):

        print(
            f"Проверяю камеру {camera_index}..."
        )

        # Сначала обычный backend
        try:

            cap = cv2.VideoCapture(
                camera_index
            )

            if cap.isOpened():

                ret, frame = cap.read()

                if ret and frame is not None:

                    print(
                        f"КАМЕРА НАЙДЕНА: {camera_index}"
                    )

                    return cap

                cap.release()

        except Exception as e:

            print(
                f"Обычный backend ошибка: {e}"
            )

        # Затем DirectShow
        try:

            cap = cv2.VideoCapture(
                camera_index,
                cv2.CAP_DSHOW
            )

            if cap.isOpened():

                ret, frame = cap.read()

                if ret and frame is not None:

                    print(
                        f"КАМЕРА НАЙДЕНА "
                        f"(DSHOW): {camera_index}"
                    )

                    return cap

                cap.release()

        except Exception as e:

            print(
                f"DSHOW ошибка: {e}"
            )

    print()
    print("КАМЕРА НЕ НАЙДЕНА")
    print()

    return None


def start_camera():

    if model is None:

        return {
            "success": False,
            "message": (
                "YOLO модель не загрузилась."
            )
        }

    camera = find_working_camera()

    if camera is None:

        return {
            "success": False,
            "message": (
                "Камера не найдена. "
                "Проверь подключение камеры "
                "и разрешения Windows."
            )
        }

    print()
    print("==============================")
    print("КАМЕРА ЗАПУЩЕНА")
    print("Нажми Q для выхода")
    print("==============================")
    print()

    try:

        while True:

            ret, frame = camera.read()

            if not ret or frame is None:

                print(
                    "Не удалось получить кадр."
                )

                break

            # ------------------------------------------------
            # YOLO
            # ------------------------------------------------

            results = model(
                frame,
                verbose=False
            )

            person_count = 0

            # ------------------------------------------------
            # ОБРАБОТКА РЕЗУЛЬТАТОВ
            # ------------------------------------------------

            for result in results:

                boxes = result.boxes

                if boxes is None:
                    continue

                for box in boxes:

                    # Класс объекта
                    class_id = int(
                        box.cls[0]
                    )

                    # В COCO:
                    # 0 = person
                    if class_id != 0:
                        continue

                    confidence = float(
                        box.conf[0]
                    )

                    # Можно изменить порог
                    if confidence < 0.45:
                        continue

                    person_count += 1

                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0]
                    )

                    # ------------------------------------------------
                    # РАМКА ЧЕЛОВЕКА
                    # ------------------------------------------------

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    label = (
                        f"Person "
                        f"{confidence:.0%}"
                    )

                    cv2.putText(
                        frame,
                        label,
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )

            # ------------------------------------------------
            # СЧЁТЧИК ЛЮДЕЙ
            # ------------------------------------------------

            cv2.putText(
                frame,
                f"People: {person_count}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2
            )

            # ------------------------------------------------
            # ПОКАЗ КАМЕРЫ
            # ------------------------------------------------

            cv2.imshow(
                "Jarvis Camera",
                frame
            )

            # Q = выход
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):

                break

            # ESC = выход
            if key == 27:

                break

        return {
            "success": True,
            "message": (
                f"Камера работает. "
                f"Последний кадр: "
                f"обнаружено людей — "
                f"{person_count}."
            )
        }

    except Exception as e:

        print(
            "Ошибка камеры:",
            repr(e)
        )

        return {
            "success": False,
            "message": (
                f"Ошибка камеры: {e}"
            )
        }

    finally:

        camera.release()

        cv2.destroyAllWindows()

        print(
            "Камера освобождена."
        )
# ============================================================
# GET CAMERA
# ============================================================

def get_camera():

    print()
    print("==============================")
    print("ПОИСК КАМЕРЫ")
    print("==============================")

    # Пробуем камеры 0-4
    for camera_index in range(5):

        print(
            f"Проверяю камеру {camera_index}..."
        )

        # --------------------------------------------
        # Обычный OpenCV backend
        # --------------------------------------------

        try:

            cam = cv2.VideoCapture(
                camera_index
            )

            if cam.isOpened():

                ret, frame = cam.read()

                if ret and frame is not None:

                    print(
                        f"Камера найдена: {camera_index}"
                    )

                    return cam

                cam.release()

        except Exception as e:

            print(
                f"Ошибка камеры {camera_index}: "
                f"{e}"
            )

        # --------------------------------------------
        # Windows DirectShow
        # --------------------------------------------

        try:

            cam = cv2.VideoCapture(
                camera_index,
                cv2.CAP_DSHOW
            )

            if cam.isOpened():

                ret, frame = cam.read()

                if ret and frame is not None:

                    print(
                        f"Камера найдена через DSHOW: "
                        f"{camera_index}"
                    )

                    return cam

                cam.release()

        except Exception as e:

            print(
                f"DSHOW ошибка {camera_index}: "
                f"{e}"
            )

    print(
        "Рабочая камера не найдена."
    )

    return None


# ============================================================
# CAMERA STATUS
# ============================================================

@app.get("/camera/status")
def camera_status():

    cam = get_camera()

    return {
        "camera_available": (
            cam.isOpened()
        ),
        "yolo_available": (
            camera_model is not None
        )
    }


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
        Path.home()
        / "Desktop"
    )

    return locations


def normalize_app_name(name: str):

    name = str(
        name
    ).lower().strip()

    for extension in [
        ".lnk",
        ".url",
        ".exe"
    ]:

        if name.endswith(extension):

            name = name[
                :-len(extension)
            ]

    return name.strip()


def scan_installed_applications():

    applications = {}

    for location in (
        get_start_menu_locations()
    ):

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

                        applications[name] = (
                            str(item)
                        )

        except (
            PermissionError,
            OSError
        ):

            continue

    return applications


SYSTEM_APPS = {

    "notepad":
        "notepad.exe",

    "блокнот":
        "notepad.exe",

    "calculator":
        "calc.exe",

    "калькулятор":
        "calc.exe",

    "explorer":
        "explorer.exe",

    "проводник":
        "explorer.exe",

    "paint":
        "mspaint.exe",

    "рисование":
        "mspaint.exe",

    "cmd":
        "cmd.exe",
}


ALLOWED_APPS = (
    scan_installed_applications()
)

ALLOWED_APPS.update(
    SYSTEM_APPS
)

print()
print(
    f"Найдено приложений: "
    f"{len(ALLOWED_APPS)}"
)
print()


# ============================================================
# FIND APPLICATION
# ============================================================

def find_application(
    application: str
):

    application = str(
        application
    ).strip()

    if not application:
        return None

    name = (
        application
        .lower()
        .strip()
    )

    if name.endswith(".exe"):

        name = name[:-4]

    # SYSTEM APPS

    if name in SYSTEM_APPS:

        return SYSTEM_APPS[name]

    # SCANNED APPS

    for app_name, path in (
        ALLOWED_APPS.items()
    ):

        clean_name = (
            str(app_name)
            .lower()
            .strip()
        )

        if clean_name.endswith(
            ".exe"
        ):

            clean_name = (
                clean_name[:-4]
            )

        if name == clean_name:

            return path

    # WINDOWS PATH

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

    # COMMON LOCATIONS

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

    # SEARCH

    for location in locations:

        if not location.exists():
            continue

        try:

            for exe in (
                location.rglob("*.exe")
            ):

                exe_name = (
                    exe.stem.lower()
                )

                if exe_name == name:

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

    print()
    print(
        "=============================="
    )
    print(
        "ПОИСК ПРИЛОЖЕНИЯ"
    )
    print(
        "Название:",
        application
    )
    print(
        "=============================="
    )

    program = find_application(
        application
    )

    if not program:

        return {
            "success": False,
            "message":
                f"Приложение '{application}' "
                f"не найдено на компьютере."
        }

    print(
        "Найдено:",
        program
    )

    try:

        if str(program).lower().endswith(
            (".lnk", ".url")
        ):

            os.startfile(
                program
            )

        else:

            if os.path.dirname(
                program
            ):

                subprocess.Popen(
                    [program],
                    cwd=os.path.dirname(
                        program
                    ),
                    shell=False
                )

            else:

                subprocess.Popen(
                    [program],
                    shell=False
                )

        return {
            "success": True,
            "application":
                application,
            "path":
                str(program),
            "message":
                f"Приложение "
                f"'{application}' запущено."
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Не удалось запустить "
                f"'{application}': {e}"
        }


# ============================================================
# APPLICATION LIST
# ============================================================

def get_applications():

    global ALLOWED_APPS

    ALLOWED_APPS = (
        scan_installed_applications()
    )

    ALLOWED_APPS.update(
        SYSTEM_APPS
    )

    return {
        "success": True,
        "count":
            len(ALLOWED_APPS),
        "applications":
            sorted(
                ALLOWED_APPS.keys()
            )
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

            steam_path = Path(
                found
            )

    if steam_path is None:

        return {
            "success": False,
            "message":
                "Steam не найден."
        }

    try:

        subprocess.Popen(
            [str(steam_path)],
            shell=False
        )

        return {
            "success": True,
            "application":
                "Steam",
            "path":
                str(steam_path),
            "message":
                "Steam запущен."
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Не удалось запустить "
                f"Steam: {e}"
        }


# ============================================================
# PC INFO
# ============================================================

def get_pc_info():

    try:

        system_drive = (
            os.environ.get(
                "SystemDrive",
                "C:"
            )
        )

        total, used, free = (
            shutil.disk_usage(
                system_drive + "\\"
            )
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
            "error":
                str(e)
        }


# ============================================================
# YOUTUBE
# ============================================================

def play_youtube(
    query: str
):

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
                "query":
                    query,
                "url":
                    search_url,
                "message":
                    f"Открываю поиск "
                    f"YouTube: {query}"
            }

        html = response.text

        video_ids = re.findall(
            r'"videoId":"([^"]+)"',
            html
        )

        unique_video_ids = []

        for video_id in video_ids:

            if video_id not in (
                unique_video_ids
            ):

                unique_video_ids.append(
                    video_id
                )

        if unique_video_ids:

            video_id = (
                unique_video_ids[0]
            )

            video_url = (
                "https://www.youtube.com/watch?v="
                + video_id
            )

            opened = webbrowser.open(
                video_url,
                new=2
            )

            if opened:

                return {
                    "success": True,
                    "query":
                        query,
                    "video_id":
                        video_id,
                    "url":
                        video_url,
                    "message":
                        f"Открываю видео "
                        f"YouTube: {query}"
                }

        opened = webbrowser.open(
            search_url,
            new=2
        )

        if opened:

            return {
                "success": True,
                "query":
                    query,
                "url":
                    search_url,
                "message":
                    f"Открываю поиск "
                    f"YouTube: {query}"
            }

        return {
            "success": False,
            "message":
                "Не удалось открыть YouTube."
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Ошибка YouTube: {e}"
        }


# ============================================================
# YANDEX SEARCH
# ============================================================

def search_yandex(
    query: str
):

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

        encoded_query = quote(
            query,
            safe=""
        )

        url = (
            "https://yandex.ru/search/?text="
            + encoded_query
        )

        opened = webbrowser.open(
            url,
            new=2
        )

        if not opened:

            return {
                "success": False,
                "message":
                    "Windows не смог "
                    "открыть браузер."
            }

        return {
            "success": True,
            "query":
                query,
            "url":
                url,
            "message":
                f"Открываю поиск "
                f"Яндекс: {query}"
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Ошибка открытия Яндекса: {e}"
        }


# ============================================================
# YANDEX MOVIE SEARCH
# ============================================================

def search_yandex_movie(
    query: str
):

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

        search_text = (
            f"{query} фильм"
        )

        encoded_query = quote(
            search_text,
            safe=""
        )

        search_url = (
            "https://yandex.ru/search/?text="
            + encoded_query
        )

        opened = webbrowser.open(
            search_url,
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
            "query":
                query,
            "url":
                search_url,
            "message":
                f"Открываю поиск фильма "
                f"«{query}» в Яндексе."
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


def open_website(
    url: str
):

    url = str(
        url
    ).strip()

    if not url:

        return {
            "success": False,
            "message":
                "URL пустой."
        }

    if url.lower() in (
        KNOWN_WEBSITES
    ):

        url = KNOWN_WEBSITES[
            url.lower()
        ]

    if not url.startswith(
        (
            "http://",
            "https://"
        )
    ):

        url = (
            "https://"
            + url
        )

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
            "url":
                url,
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


def open_folder(
    path: str
):

    path = os.path.expandvars(
        path
    )

    path = os.path.expanduser(
        path
    )

    if not path:

        return {
            "success": False,
            "message":
                "Путь не указан."
        }

    if path.lower() in (
        KNOWN_FOLDERS
    ):

        path = str(
            KNOWN_FOLDERS[
                path.lower()
            ]
        )

    try:

        if not os.path.exists(
            path
        ):

            return {
                "success": False,
                "message":
                    f"Путь не существует: {path}"
            }

        os.startfile(
            path
        )

        return {
            "success": True,
            "path":
                path,
            "message":
                f"Открыта папка: {path}"
        }

    except Exception as e:

        return {
            "success": False,
            "message":
                str(e)
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
                    (
                        "folder"
                        if item.is_dir()
                        else "file"
                    )
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
            "message":
                str(e)
        }


# ============================================================
# FIND FILE
# ============================================================

def find_file(
    filename: str
):

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
                            "results":
                                results
                        }

        except (
            PermissionError,
            OSError
        ):

            continue

    return {
        "success": True,
        "results":
            results
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


async def download_file(
    url: str
):

    url = str(
        url
    ).strip()

    if not url:

        return {
            "success": False,
            "message":
                "URL не указан."
        }

    parsed = urlparse(
        url
    )

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

                    if (
                        size
                        > MAX_DOWNLOAD_SIZE
                    ):

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

                    async for chunk in (
                        response.aiter_bytes(
                            1024 * 1024
                        )
                    ):

                        downloaded += len(
                            chunk
                        )

                        if (
                            downloaded
                            > MAX_DOWNLOAD_SIZE
                        ):

                            file.close()

                            destination.unlink(
                                missing_ok=True
                            )

                            return {
                                "success": False,
                                "message":
                                    "Загрузка остановлена: "
                                    "файл больше 2 ГБ."
                            }

                        file.write(
                            chunk
                        )

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
                f"Файл скачан в Downloads: "
                f"{filename}"
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
# UNIVERSAL OPEN
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

        if not result.get(
            "success"
        ):

            return result

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

        file_path = files[0]

        try:

            os.startfile(
                file_path
            )

            return {
                "success": True,
                "path":
                    file_path,
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

        lower = (
            target
            .lower()
            .strip()
        )

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

        youtube_prefixes = [

            "включи музыку ",

            "включи песню ",

            "включи видео ",

            "включи ролик ",

            "найди на youtube ",

            "найди на ютуб ",
        ]

        for prefix in (
            youtube_prefixes
        ):

            if lower.startswith(
                prefix
            ):

                query = target[
                    len(prefix):
                ].strip()

                if query:

                    return play_youtube(
                        query
                    )

        application = (
            find_application(
                target
            )
        )

        if application:

            return open_application(
                target
            )

        file_result = find_file(
            target
        )

        if file_result.get(
            "success"
        ):

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
                        "path":
                            files[0],
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
            f"Неизвестный тип объекта: "
            f"{target_type}"
    }


# ============================================================
# TOOL DEFINITIONS
# ============================================================

TOOLS = [

    {
        "type": "function",

        "function": {

            "name":
                "get_pc_info",

            "description":
                "Получить информацию "
                "о компьютере пользователя.",

            "parameters": {

                "type":
                    "object",

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
                "Получить список приложений, "
                "найденных на компьютере.",

            "parameters": {

                "type":
                    "object",

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
                "Главный универсальный инструмент "
                "для открытия или запуска объекта. "
                "Используй для приложений, Steam, "
                "сайтов, YouTube, фильмов, файлов "
                "и папок.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "target": {

                        "type":
                            "string",

                        "description":
                            "Название или путь объекта."
                    },

                    "target_type": {

                        "type":
                            "string",

                        "enum": [

                            "auto",

                            "application",

                            "website",

                            "youtube",

                            "movie",

                            "file",

                            "folder"
                        ],

                        "description":
                            "Тип объекта."
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
                "Открыть поиск Яндекс "
                "по заданному запросу.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "query": {

                        "type":
                            "string"
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
                "Получить список файлов "
                "и папок в Downloads.",

            "parameters": {

                "type":
                    "object",

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
                "Найти файл в Downloads, "
                "Desktop или Documents.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "filename": {

                        "type":
                            "string",

                        "description":
                            "Имя или часть имени файла."
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
                "Скачать файл по прямой HTTP "
                "или HTTPS ссылке в Downloads. "
                "Не запускать скачанный файл.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "url": {

                        "type":
                            "string",

                        "description":
                            "HTTP или HTTPS URL."
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

        "description": (
            "Включить камеру компьютера "
            "и обнаруживать людей через YOLO."
        ),

        "parameters": {

            "type": "object",

            "properties": {},

            "required": []
        }
    }
},
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
                f"Ошибка инструмента "
                f"{name}: {e}"
        }


# ============================================================
# GROQ
# ============================================================

async def ask_groq(
    text: str
):

    if not GROQ_API_KEY:

        return {

            "answer":
                "Ошибка: GROQ_API_KEY "
                "не найден в .env.",

            "action":
                "none",

            "query":
                ""
        }

    system_message = """

Ты Jarvis — локальный AI-помощник пользователя.

Отвечай только на русском языке.

Ты умеешь:

- отвечать на обычные вопросы;
- получать информацию о компьютере;
- запускать приложения;
- запускать Steam;
- открывать сайты;
- искать через Яндекс;
- искать и открывать файлы;
- открывать папки;
- смотреть Downloads;
- открывать YouTube;
- искать видео и музыку на YouTube;
- искать фильмы через Яндекс;
- скачивать файлы по HTTP/HTTPS.

ПРАВИЛА:

1. Если для выполнения запроса нужен инструмент —
   обязательно используй инструмент.

2. Не говори, что действие выполнено,
   пока инструмент не вернул результат.

3. Если инструмент вернул success=true,
   сообщи пользователю реальный результат.

4. Если инструмент вернул success=false,
   не утверждай, что действие выполнено.

5. Не выдумывай характеристики компьютера.
   Для информации о ПК используй get_pc_info.

6. Если пользователь просит открыть, запустить
   или включить приложение, используй open_requested.

7. Для приложения:
   target_type="application"

8. Для сайта:
   target_type="website"

9. Для YouTube, песни, музыки или видео:
   target_type="youtube"

10. Для фильма, сериала или мультфильма:
    target_type="movie"

11. Для файла:
    target_type="file"

12. Для папки:
    target_type="folder"

13. Если пользователь говорит просто
    "открой X", используй open_requested.

14. Steam является разрешённым приложением.

15. Если пользователь просит включить музыку,
    песню, видео или ролик и указывает название,
    используй YouTube.

16. Если пользователь просит найти фильм,
    сериал или мультфильм через Яндекс,
    используй target_type="movie".

17. Если пользователь спрашивает содержимое Downloads,
    используй get_downloads.

18. Если пользователь просит найти файл,
    используй find_file.

19. Если пользователь просит открыть папку,
    используй open_requested.

20. Не выполняй опасные системные операции.

21. Не удаляй файлы.

22. Не форматируй диски.

23. Не отключай антивирус или защиту Windows.

24. Не используй shell-команды для опасных действий.

25. После инструмента отвечай кратко.

26. Если инструмент только открыл страницу поиска,
    не говори "видео запущено".

27. Если приложение успешно запущено,
    сообщи об этом.

28. Если папка успешно открыта,
    сообщи об этом.

29. Не задавай лишних уточняющих вопросов,
    если команда понятна.

30. Камера компьютера доступна через интерфейс
    Jarvis. Она используется только для изображения
    с локальной камеры и обнаружения объектов,
    например людей.

31. Не используй камеру для установления личности
    человека, распознавания лица или слежки.

"""


    messages = [

        {
            "role":
                "system",

            "content":
                system_message
        }

    ]

    messages.extend(
        conversation_history
    )

    messages.append({

        "role":
            "user",

        "content":
            text
    })

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

        # ====================================================
        # FIRST REQUEST
        # ====================================================

        async with httpx.AsyncClient(
            timeout=60.0
        ) as client:

            response = await client.post(

                GROQ_URL,

                headers=headers,

                json=data
            )

        print(
            "Статус Groq:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                response.text
            )

            return {

                "answer":
                    f"Ошибка Groq: "
                    f"{response.status_code}",

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
                    "Groq вернул "
                    "некорректный JSON.",

                "action":
                    "none",

                "query":
                    ""
            }

        choices = result.get(
            "choices",
            []
        )

        if not choices:

            return {

                "answer":
                    "Groq не вернул ответ.",

                "action":
                    "none",

                "query":
                    ""
            }

        message = choices[0].get(
            "message",
            {}
        )

        if not message:

            return {

                "answer":
                    "Groq не вернул "
                    "корректное сообщение.",

                "action":
                    "none",

                "query":
                    ""
            }

        tool_calls = message.get(
            "tool_calls",
            []
        )

        # ====================================================
        # TOOL CALL
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

                arguments_text = (
                    function.get(
                        "arguments",
                        "{}"
                    )
                )

                try:

                    arguments = json.loads(
                        arguments_text
                    )

                except json.JSONDecodeError:

                    arguments = {}

                print()
                print(
                    "Jarvis вызывает:",
                    name
                )

                print(
                    "Аргументы:",
                    arguments
                )

                tool_result = (
                    await execute_tool(
                        name,
                        arguments
                    )
                )

                print(
                    "Результат:",
                    tool_result
                )

                messages.append({

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
                })

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

                second_response = (
                    await client.post(

                        GROQ_URL,

                        headers=headers,

                        json=second_data
                    )
                )

            print(
                "Статус второго Groq:",
                second_response.status_code
            )

            if (
                second_response.status_code
                != 200
            ):

                print(
                    second_response.text
                )

                return {

                    "answer":
                        "Инструмент выполнен, "
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
                        "Инструмент выполнен, "
                        "но Groq вернул "
                        "некорректный ответ.",

                    "action":
                        "none",

                    "query":
                        ""
                }

            second_choices = (
                second_result.get(
                    "choices",
                    []
                )
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

                answer = (
                    "Команда выполнена."
                )

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

        conversation_history.append({

            "role":
                "user",

            "content":
                text
        })

        conversation_history.append({

            "role":
                "assistant",

            "content":
                answer
        })

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
            "HTTP ошибка:",
            repr(e)
        )

        return {

            "answer":
                "Не удалось подключиться к Groq.",

            "action":
                "none",

            "query":
                ""
        }

    except Exception as e:

        print(
            "Ошибка ask_groq:",
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
# HTML
# ============================================================

@app.get("/")
def home():

    return HTMLResponse("""

<!DOCTYPE html>

<html lang="ru">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>My Jarvis</title>

<style>

* {
    box-sizing: border-box;
}

body {

    background:
        radial-gradient(
            circle at top,
            #18243a,
            #080b10 60%
        );

    color: white;

    font-family: Arial, sans-serif;

    max-width: 1000px;

    margin: 0 auto;

    padding: 30px 20px;
}

h1 {

    text-align: center;

    color: #4fc3f7;

    text-shadow:
        0 0 20px
        rgba(79,195,247,.5);
}

.subtitle {

    text-align: center;

    color: #888;

    margin-bottom: 25px;
}

.controls {

    display: flex;

    gap: 8px;

    margin-bottom: 20px;
}

input {

    flex: 1;

    padding: 14px;

    font-size: 17px;

    border-radius: 10px;

    border: 1px solid #333;

    background: #171b22;

    color: white;

    outline: none;
}

input:focus {

    border-color: #1976d2;
}

button {

    padding: 12px 18px;

    font-size: 16px;

    border: none;

    border-radius: 10px;

    cursor: pointer;

    color: white;
}

#send {

    background: #1976d2;
}

#mic {

    background: #b00020;
}

button:hover {

    opacity: .85;
}

button:disabled {

    opacity: .4;

    cursor: not-allowed;
}

#status {

    text-align: center;

    min-height: 24px;

    color: #aaa;

    margin-bottom: 15px;
}

#chat {

    display: flex;

    flex-direction: column;

    gap: 10px;
}

.user,
.bot {

    padding: 14px;

    border-radius: 14px;

    line-height: 1.5;

    white-space: pre-wrap;
}

.user {

    background: #174ea6;

    align-self: flex-end;

    max-width: 80%;
}

.bot {

    background: #20252d;

    align-self: flex-start;

    max-width: 90%;
}


/* ==========================================================
   CAMERA
   ========================================================== */

.camera-panel {

    margin-top: 30px;

    padding: 18px;

    background:
        rgba(21, 26, 33, .95);

    border: 1px solid #29313d;

    border-radius: 16px;

    box-shadow:
        0 0 30px
        rgba(0, 0, 0, .3);
}

.camera-title {

    display: flex;

    justify-content: space-between;

    align-items: center;

    margin-bottom: 15px;
}

.camera-title h2 {

    color: #4fc3f7;

    margin: 0;
}

.camera-status {

    color: #55efc4;

    font-size: 14px;
}

.camera-container {

    position: relative;

    width: 100%;

    overflow: hidden;

    border-radius: 12px;

    background: black;

    border: 2px solid #1976d2;
}

#camera {

    display: block;

    width: 100%;

    height: auto;

    min-height: 300px;

    object-fit: contain;

    background: #000;
}

.camera-info {

    margin-top: 10px;

    color: #888;

    font-size: 13px;

    text-align: center;
}

</style>

</head>

<body>


<h1>🤖 Jarvis</h1>

<div class="subtitle">
    Локальный AI-помощник
</div>


<div class="controls">

<input
    id="text"
    placeholder="Скажи или напиши команду..."
    autocomplete="off"
>

<button id="send">
    Отправить
</button>

<button id="mic">
    🎤
</button>

</div>


<div id="status"></div>


<div id="chat"></div>


<!-- ========================================================
     CAMERA
     ======================================================== -->

<div class="camera-panel">

    <div class="camera-title">

        <h2>
            📷 Камера Jarvis
        </h2>

        <div
            class="camera-status"
            id="cameraStatus"
        >
            Проверка...
        </div>

    </div>

    <div class="camera-container">

        <img
            id="camera"
            src="/camera"
            alt="Камера Jarvis"
        >

    </div>

    <div class="camera-info">

        Локальная камера компьютера.
        Зелёные рамки показывают обнаруженных людей.

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

const cameraStatus =
    document.getElementById(
        "cameraStatus"
    );


// ========================================================
// HTML ESCAPE
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
// SEND MESSAGE
// ========================================================

async function sendMessage() {

    const text =
        input.value.trim();

    if (!text) {

        return;

    }

    chat.innerHTML += `

        <div class="user">

            <b>Вы:</b>

            ${escapeHtml(text)}

        </div>

    `;

    input.value = "";

    status.innerText =
        "🤖 Думаю...";


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


        status.innerText =
            "";


        chat.innerHTML += `

            <div class="bot">

                <b>Jarvis:</b>

                ${escapeHtml(
                    data.answer || ""
                )}

            </div>

        `;


        window.scrollTo(
            0,
            document.body.scrollHeight
        );


        speak(
            data.answer || ""
        );


    }

    catch (error) {

        console.error(
            error
        );


        status.innerText =
            "❌ Ошибка";


        chat.innerHTML += `

            <div class="bot">

                <b>Jarvis:</b>

                Не удалось выполнить запрос.

            </div>

        `;


        speak(
            "Произошла ошибка."
        );

    }

}


// ========================================================
// SEND BUTTON
// ========================================================

document
    .getElementById(
        "send"
    )
    .onclick =
    sendMessage;


// ========================================================
// ENTER
// ========================================================

input.addEventListener(

    "keydown",

    function(event) {

        if (
            event.key ===
            "Enter"
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

let recognition;


if (SpeechRecognition) {

    recognition =
        new SpeechRecognition();


    recognition.lang =
        "ru-RU";


    recognition.continuous =
        false;


    recognition.interimResults =
        false;


    recognition.onstart =
        function() {

            status.innerText =
                "🎤 Слушаю...";

        };


    recognition.onresult =
        function(event) {

            const text =
                event.results[0][0]
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
                "Не удалось распознать речь";

        };


    recognition.onend =
        function() {

            setTimeout(

                function() {

                    if (
                        status.innerText ===
                        "🎤 Слушаю..."
                    ) {

                        status.innerText =
                            "";

                    }

                },

                500
            );

        };


    document
        .getElementById(
            "mic"
        )
        .onclick =
        function() {

            try {

                recognition.start();

            }

            catch (error) {

                console.log(
                    error
                );

            }

        };

}

else {

    document
        .getElementById(
            "mic"
        )
        .disabled =
        true;


    status.innerText =
        "Браузер не поддерживает голосовой ввод";

}


// ========================================================
// TEXT TO SPEECH
// ========================================================

function speak(text) {

    if (
        !("speechSynthesis" in window)
    ) {

        return;

    }


    if (!text) {

        return;

    }


    speechSynthesis.cancel();


    const utterance =
        new SpeechSynthesisUtterance(
            text
        );


    utterance.lang =
        "ru-RU";


    utterance.rate =
        1;


    utterance.pitch =
        1;


    speechSynthesis.speak(
        utterance
    );

}


// ========================================================
// CAMERA STATUS
// ========================================================

async function checkCamera() {

    try {

        const response =
            await fetch(
                "/camera/status"
            );


        const data =
            await response.json();


        if (
            data.camera_available
            && data.yolo_available
        ) {

            cameraStatus.innerText =
                "● Камера работает";

            cameraStatus.style.color =
                "#55efc4";

        }

        else if (
            data.camera_available
        ) {

            cameraStatus.innerText =
                "● Камера работает / YOLO недоступна";

            cameraStatus.style.color =
                "#ffe66d";

        }

        else {

            cameraStatus.innerText =
                "● Камера недоступна";

            cameraStatus.style.color =
                "#ff7675";

        }

    }

    catch (error) {

        cameraStatus.innerText =
            "● Ошибка камеры";

        cameraStatus.style.color =
            "#ff7675";

    }

}


checkCamera();


setInterval(
    checkCamera,
    5000
);


</script>

</body>

</html>

""")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    import uvicorn

    print()
    print(
        "=============================="
    )
    print(
        "       JARVIS STARTING"
    )
    print(
        "=============================="
    )
    print()

    print(
        "Камера: "
        "http://127.0.0.1:9013/camera"
    )

    print(
        "Jarvis: "
        "http://127.0.0.1:9013"
    )

    print()

    uvicorn.run(

        app,

        host="127.0.0.1",

        port=9013
    )