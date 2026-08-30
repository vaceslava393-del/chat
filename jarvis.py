import os
import json
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote
import re
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from starlette.responses import HTMLResponse, JSONResponse


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

app = FastAPI(title="My Jarvis")

MAX_HISTORY = 10

conversation_history = []


# ============================================================
# ПРОВЕРКА GROQ
# ============================================================

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY не найден в .env")
else:
    print("Groq API key найден")


# ============================================================
# АВТОМАТИЧЕСКИЙ СПИСОК ПРИЛОЖЕНИЙ WINDOWS
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

    desktop = Path.home() / "Desktop"

    locations.append(desktop)

    return locations


def normalize_app_name(name: str):

    name = str(name).lower().strip()

    # Убираем расширения ярлыков
    for extension in [".lnk", ".url", ".exe"]:

        if name.endswith(extension):
            name = name[:-len(extension)]

    return name.strip()


def scan_installed_applications():

    applications = {}

    locations = get_start_menu_locations()

    for location in locations:

        if not location.exists():
            continue

        try:

            for item in location.rglob("*"):

                if not item.is_file():
                    continue

                # Обычные EXE
                if item.suffix.lower() == ".exe":

                    name = normalize_app_name(
                        item.stem
                    )

                    if name:
                        applications[name] = str(item)

                # Ярлыки Windows
                elif item.suffix.lower() == ".lnk":

                    name = normalize_app_name(
                        item.stem
                    )

                    if name:
                        applications[name] = str(item)

                # Интернет-ярлыки
                elif item.suffix.lower() == ".url":

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


# Кэш приложений.
# Он обновляется при запуске программы.
ALLOWED_APPS = scan_installed_applications()


# Дополнительные системные приложения
ALLOWED_APPS.update({
    "notepad": "notepad.exe",
    "блокнот": "notepad.exe",

    "calculator": "calc.exe",
    "калькулятор": "calc.exe",

    "explorer": "explorer.exe",
    "проводник": "explorer.exe",

    "paint": "mspaint.exe",
    "рисование": "mspaint.exe",

    "cmd": "cmd.exe",


})


print()
print(
    f"Найдено приложений: "
    f"{len(ALLOWED_APPS)}"
)
print()


# ============================================================
# ПОИСК ПРИЛОЖЕНИЯ
# ============================================================

def find_application(application: str):

    application = str(application).strip()

    if not application:
        return None

    name = application.lower()

    # Убираем .exe если пользователь его написал
    if name.endswith(".exe"):
        name = name[:-4]

    # ========================================================
    # 1. Уже найденные приложения
    # ========================================================

    for app_name, path in ALLOWED_APPS.items():

        clean_name = str(app_name).lower().strip()

        if clean_name.endswith(".exe"):
            clean_name = clean_name[:-4]

        if name == clean_name:
            return path

    # ========================================================
    # 2. Windows PATH
    # ========================================================

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

    # ========================================================
    # 3. Известные папки Windows
    # ========================================================

    search_locations = [

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

    # ========================================================
    # 4. Ищем EXE
    # ========================================================

    for location in search_locations:

        if not location:
            continue

        if not location.exists():
            continue

        try:

            for exe in location.rglob("*.exe"):

                exe_name = exe.stem.lower()

                # Точное совпадение
                if exe_name == name:

                    return str(exe)

                # Частичное совпадение
                if name in exe_name:

                    return str(exe)

        except (
            PermissionError,
            OSError
        ):

            continue

    return None


# ============================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================================

def open_application(application: str):

    application = str(
        application
    ).strip()

    if not application:

        return {
            "success": False,
            "message": "Название приложения не указано."
        }

    print()
    print("==============================")
    print("ПОИСК ПРИЛОЖЕНИЯ")
    print("Название:", application)
    print("==============================")

    # ========================================================
    # Специальные системные приложения
    # ========================================================

    system_apps = {

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

    normalized = application.lower()

    if normalized in system_apps:

        program = system_apps[
            normalized
        ]

        try:

            subprocess.Popen(
                [program],
                shell=False
            )

            return {
                "success": True,
                "application": application,
                "path": program,
                "message": (
                    f"Приложение "
                    f"'{application}' запущено."
                )
            }

        except Exception as e:

            return {
                "success": False,
                "message": str(e)
            }

    # ========================================================
    # Ищем приложение
    # ========================================================

    program = find_application(
        application
    )

    # ========================================================
    # Не нашли
    # ========================================================

    if not program:

        print(
            "Приложение не найдено:",
            application
        )

        return {
            "success": False,
            "message": (
                f"Приложение '{application}' "
                f"не найдено на компьютере."
            )
        }

    print(
        "Найдено:",
        program
    )

    # ========================================================
    # Запуск
    # ========================================================

    try:

        # ----------------------------------------------------
        # Ярлык Windows
        # ----------------------------------------------------

        if program.lower().endswith(
            (".lnk", ".url")
        ):

            os.startfile(
                program
            )

        # ----------------------------------------------------
        # EXE
        # ----------------------------------------------------

        else:

            subprocess.Popen(
                [program],
                cwd=os.path.dirname(program),
                shell=False
            )

        print(
            "УСПЕШНО ЗАПУЩЕНО:",
            program
        )

        return {
            "success": True,
            "application": application,
            "path": program,
            "message": (
                f"Приложение "
                f"'{application}' запущено."
            )
        }

    except Exception as e:

        print(
            "ОШИБКА ЗАПУСКА:",
            repr(e)
        )

        return {
            "success": False,
            "message": (
                f"Не удалось запустить "
                f"'{application}': {e}"
            )
        }


# ============================================================
# СПИСОК ДОСТУПНЫХ ПРИЛОЖЕНИЙ
# ============================================================

def get_applications():

    global ALLOWED_APPS

    ALLOWED_APPS = scan_installed_applications()

    ALLOWED_APPS.update({


        "notepad": "notepad.exe",
        "блокнот": "notepad.exe",

        "calculator": "calc.exe",
        "калькулятор": "calc.exe",

        "explorer": "explorer.exe",
        "проводник": "explorer.exe",

        "paint": "mspaint.exe",
        "рисование": "mspaint.exe",

        "cmd": "cmd.exe",


    })

    return {
        "success": True,
        "count": len(ALLOWED_APPS),
        "applications": sorted(
            ALLOWED_APPS.keys()
        )
    }

def open_steam():
    try:
        subprocess.Popen(
            ["steam.exe"],
            shell=False
        )

        return {
            "success": True,
            "message": "Steam запущен."
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Не удалось запустить Steam: {e}"
        }



# ============================================================
# ИНФОРМАЦИЯ О ПК
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

            "disk_total_gb": round(
                total / 1024 ** 3,
                2
            ),

            "disk_used_gb": round(
                used / 1024 ** 3,
                2
            ),

            "disk_free_gb": round(
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
# YOUTUBE — АВТОМАТИЧЕСКОЕ ОТКРЫТИЕ ПЕРВОГО ВИДЕО
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
            "https://www.youtube.com/results?search_query="
            + encoded_query
        )

        # Получаем страницу поиска YouTube
        with httpx.Client(
            timeout=15.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/131.0 Safari/537.36"
                )
            }
        ) as client:

            response = client.get(search_url)

        if response.status_code != 200:

            # Если YouTube не дал страницу,
            # хотя бы открываем обычный поиск
            webbrowser.open(
                search_url,
                new=2
            )

            return {
                "success": True,
                "query": query,
                "url": search_url,
                "message": (
                    f"Открываю поиск YouTube: {query}"
                )
            }

        html = response.text

        # ----------------------------------------------------
        # Ищем videoId в HTML
        # ----------------------------------------------------

        import re

        video_ids = re.findall(
            r'"videoId":"([^"]+)"',
            html
        )

        # Убираем дубликаты
        unique_video_ids = []

        for video_id in video_ids:

            if video_id not in unique_video_ids:

                unique_video_ids.append(
                    video_id
                )

        # ----------------------------------------------------
        # Нашли видео
        # ----------------------------------------------------

        if unique_video_ids:

            video_id = unique_video_ids[0]

            video_url = (
                "https://www.youtube.com/watch?v="
                + video_id
            )

            opened = webbrowser.open(
                video_url,
                new=2
            )

            if not opened:

                return {
                    "success": False,
                    "message": (
                        "Не удалось открыть видео YouTube."
                    )
                }

            return {
                "success": True,
                "query": query,
                "video_id": video_id,
                "url": video_url,
                "message": (
                    f"Открываю видео YouTube: {query}"
                )
            }

        # ----------------------------------------------------
        # Если videoId не нашли
        # ----------------------------------------------------

        opened = webbrowser.open(
            search_url,
            new=2
        )

        if not opened:

            return {
                "success": False,
                "message": (
                    "Не удалось открыть YouTube."
                )
            }

        return {
            "success": True,
            "query": query,
            "url": search_url,
            "message": (
                f"Открываю поиск YouTube: {query}"
            )
        }

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"Ошибка YouTube: {e}"
            )
        }


# ============================================================
# ЯНДЕКС
# ============================================================

def search_yandex(query: str):

    query = str(query).strip()

    if not query:
        return {
            "success": False,
            "message": "Поисковый запрос пустой."
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

        print("Открываю Яндекс:")
        print(url)

        opened = webbrowser.open(
            url,
            new=2
        )

        if not opened:
            return {
                "success": False,
                "message": (
                    "Windows не смог открыть браузер."
                )
            }

        return {
            "success": True,
            "query": query,
            "url": url,
            "message": (
                f"Открываю поиск Яндекс: {query}"
            )
        }

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"Ошибка открытия Яндекса: {e}"
            )
        }

# ============================================================
# ЯНДЕКС-ФИЛЬМЫ
# ============================================================
def search_yandex_movie(query: str):

    query = str(query).strip()

    if not query:
        return {
            "success": False,
            "message": "Название фильма не указано."
        }

    try:

        search_text = f"{query} смотреть фильм"

        encoded_query = quote(
            search_text,
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
                "message": "Не удалось открыть Яндекс."
            }

        return {
            "success": True,
            "query": query,
            "url": url,
            "message": f"Ищу фильм «{query}» в Яндексе."
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"Ошибка Яндекса: {e}"
        }


# ============================================================
# ОТКРЫТЬ САЙТ
# ============================================================

def open_website(url: str):

    url = str(url).strip()

    if not url:
        return {
            "success": False,
            "message": "URL пустой."
        }

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
                "message": (
                    "Не удалось открыть браузер."
                )
            }

        return {
            "success": True,
            "url": url,
            "message": (
                f"Открыта страница: {url}"
            )
        }

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"Ошибка открытия сайта: {e}"
            )
        }

# ============================================================
# STEAM
# ============================================================

def open_steam():

    possible_paths = [

        # Обычный Steam
        Path(
            os.environ.get(
                "PROGRAMFILES(X86)",
                r"C:\Program Files (x86)"
            )
        ) / "Steam" / "steam.exe",

        # 64-bit вариант
        Path(
            os.environ.get(
                "PROGRAMFILES",
                r"C:\Program Files"
            )
        ) / "Steam" / "steam.exe",

        # Если Steam установлен в AppData
        Path.home() / "AppData" / "Local" / "Steam" / "steam.exe",

    ]

    # --------------------------------------------------------
    # Ищем Steam
    # --------------------------------------------------------

    steam_path = None

    for path in possible_paths:

        if path.is_file():

            steam_path = path
            break

    # --------------------------------------------------------
    # Если не нашли по стандартному пути,
    # пробуем Windows PATH
    # --------------------------------------------------------

    if steam_path is None:

        import shutil

        found = shutil.which("steam.exe")

        if found:

            steam_path = Path(found)

    # --------------------------------------------------------
    # Steam не найден
    # --------------------------------------------------------

    if steam_path is None:

        return {
            "success": False,
            "message": (
                "Steam не найден. "
                "Проверь, установлен ли Steam."
            )
        }

    # --------------------------------------------------------
    # Запускаем Steam
    # --------------------------------------------------------

    try:

        print(
            "Запускаю Steam:"
        )

        print(
            steam_path
        )

        subprocess.Popen(
            [str(steam_path)],
            shell=False
        )

        return {
            "success": True,
            "application": "steam",
            "path": str(steam_path),
            "message": "Steam запущен."
        }

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"Не удалось запустить Steam: {e}"
            )
        }

    # ============================================================
    # УНИВЕРСАЛЬНОЕ ОТКРЫТИЕ
    # ============================================================

    def open_requested(target: str, target_type: str = "auto"):

        target = str(target).strip()
        target_type = str(target_type).lower().strip()

        if not target:
            return {
                "success": False,
                "message": "Не указано, что нужно открыть."
            }

        # --------------------------------------------------------
        # AUTO
        # --------------------------------------------------------

        if target_type == "auto":

            lower = target.lower()

            # YouTube / музыка / видео
            youtube_words = [
                "включи музыку",
                "включи песню",
                "включи видео",
                "включи ролик",
                "найди на youtube",
                "ютуб",
                "youtube",
            ]

            if any(word in lower for word in youtube_words):

                query = target

                for word in youtube_words:
                    query = query.replace(word, "").strip()

                if not query:
                    query = target

                return play_youtube(query)

            # Известные сайты
            websites = {
                "youtube": "https://www.youtube.com",
                "ютуб": "https://www.youtube.com",
                "google": "https://www.google.com",
                "гугл": "https://www.google.com",
                "yandex": "https://yandex.ru",
                "яндекс": "https://yandex.ru",
                "vk": "https://vk.com",
                "вк": "https://vk.com",
                "telegram web": "https://web.telegram.org",
            }

            if lower in websites:
                return open_website(websites[lower])

            # Папки
            folders = {
                "downloads": Path.home() / "Downloads",
                "загрузки": Path.home() / "Downloads",

                "desktop": Path.home() / "Desktop",
                "рабочий стол": Path.home() / "Desktop",

                "documents": Path.home() / "Documents",
                "документы": Path.home() / "Documents",
            }

            if lower in folders:
                return open_folder(str(folders[lower]))

            # В остальных случаях считаем приложением
            return open_application(target)

        # --------------------------------------------------------
        # APPLICATION
        # --------------------------------------------------------

        if target_type == "application":
            return open_application(target)

        # --------------------------------------------------------
        # WEBSITE
        # --------------------------------------------------------

        if target_type == "website":

            # Если пользователь передал название сайта
            websites = {
                "youtube": "https://www.youtube.com",
                "ютуб": "https://www.youtube.com",
                "google": "https://www.google.com",
                "гугл": "https://www.google.com",
                "yandex": "https://yandex.ru",
                "яндекс": "https://yandex.ru",
                "vk": "https://vk.com",
                "вк": "https://vk.com",
            }

            lower = target.lower()

            if lower in websites:
                return open_website(websites[lower])

            return open_website(target)

        # --------------------------------------------------------
        # YOUTUBE
        # --------------------------------------------------------

        if target_type == "youtube":
            return play_youtube(target)

        # --------------------------------------------------------
        # FILE
        # --------------------------------------------------------

        if target_type == "file":

            results = find_file(target)

            if not results.get("success"):
                return results

            files = results.get("results", [])

            if not files:
                return {
                    "success": False,
                    "message": f"Файл '{target}' не найден."
                }

            file_path = files[0]

            try:

                os.startfile(file_path)

                return {
                    "success": True,
                    "path": file_path,
                    "message": f"Файл '{target}' открыт."
                }

            except Exception as e:

                return {
                    "success": False,
                    "message": (
                        f"Не удалось открыть файл: {e}"
                    )
                }

        # --------------------------------------------------------
        # FOLDER
        # --------------------------------------------------------

        if target_type == "folder":

            folders = {
                "downloads": Path.home() / "Downloads",
                "загрузки": Path.home() / "Downloads",

                "desktop": Path.home() / "Desktop",
                "рабочий стол": Path.home() / "Desktop",

                "documents": Path.home() / "Documents",
                "документы": Path.home() / "Documents",
            }

            lower = target.lower()

            if lower in folders:
                return open_folder(str(folders[lower]))

            return open_folder(target)

        return {
            "success": False,
            "message": (
                f"Неизвестный тип объекта: {target_type}"
            )
        }

DOWNLOAD_DIR = Path.home() / "Downloads"


async def download_file(url: str):

    url = str(url).strip()

    if not url:
        return {
            "success": False,
            "message": "URL не указан."
        }

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return {
            "success": False,
            "message": "Разрешены только HTTP и HTTPS."
        }


# =====================
# DOWNLOAD_DIR
# =====================
    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = Path(
        parsed.path
    ).name

    if not filename:
        filename = "download"

    # Убираем потенциально опасные символы
    filename = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        filename
    )

    destination = DOWNLOAD_DIR / filename

    try:

        async with httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True
        ) as client:

            async with client.stream(
                "GET",
                url,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            ) as response:

                response.raise_for_status()

                content_length = response.headers.get(
                    "content-length"
                )

                # Ограничение 2 ГБ
                if content_length:

                    size = int(content_length)

                    if size > 2 * 1024 ** 3:
                        return {
                            "success": False,
                            "message": "Файл слишком большой."
                        }

                with open(
                    destination,
                    "wb"
                ) as file:

                    downloaded = 0

                    async for chunk in response.aiter_bytes(
                        1024 * 1024
                    ):

                        downloaded += len(chunk)

                        if downloaded > 2 * 1024 ** 3:

                            file.close()

                            destination.unlink(
                                missing_ok=True
                            )

                            return {
                                "success": False,
                                "message": (
                                    "Загрузка остановлена: "
                                    "файл больше 2 ГБ."
                                )
                            }

                        file.write(chunk)

        return {
            "success": True,
            "path": str(destination),
            "size_mb": round(
                downloaded / 1024 ** 2,
                2
            ),
            "message": (
                f"Файл скачан в Downloads: "
                f"{filename}"
            )
        }

    except Exception as e:

        destination.unlink(
            missing_ok=True
        )

        return {
            "success": False,
            "message": f"Ошибка загрузки: {e}"
        }


# ============================================================
# DOWNLOADS
# ============================================================

def get_downloads():

    downloads = Path.home() / "Downloads"

    if not downloads.exists():

        return {
            "success": False,
            "message": (
                "Папка Downloads не найдена."
            )
        }

    try:

        files = []

        for item in downloads.iterdir():

            files.append({
                "name": item.name,
                "type": (
                    "folder"
                    if item.is_dir()
                    else "file"
                )
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
# ПОИСК ФАЙЛА
# ============================================================

def find_file(filename: str):

    filename = str(filename).lower().strip()

    if not filename:
        return {
            "success": False,
            "message": "Имя файла не указано."
        }

    search_locations = [
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Documents"
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
# ОТКРЫТЬ ПАПКУ
# ============================================================

def open_folder(path: str):

    path = os.path.expandvars(path)
    path = os.path.expanduser(path)

    if not path:
        return {
            "success": False,
            "message": "Путь не указан."
        }

    try:

        if not os.path.exists(path):

            return {
                "success": False,
                "message": (
                    f"Путь не существует: {path}"
                )
            }

        os.startfile(path)

        return {
            "success": True,
            "message": (
                f"Открыта папка: {path}"
            )
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


# ============================================================
# WINDOWS COMMAND
# ============================================================

def run_windows_command(command: str):

    command = str(command).strip()

    if not command:

        return {
            "success": False,
            "message": "Команда пустая."
        }

    # ВАЖНО:
    # Этот инструмент позволяет выполнять произвольные
    # команды Windows. Не передавайте сюда команды,
    # которые могут удалить/повредить данные.

    try:

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:5000]
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "message": (
                "Команда выполнялась слишком долго."
            )
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


# ============================================================
# TOOL DEFINITIONS
# ============================================================
TOOLS=[
{
    "type": "function",

    "function": {

        "name": "open_requested",

        "description": (
            "Универсальный инструмент открытия объектов. "
            "Используй его, когда пользователь просит открыть, "
            "запустить или включить приложение, сайт, файл, "
            "папку или YouTube."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "target": {
                    "type": "string",
                    "description": (
                        "Название или путь объекта, "
                        "который нужно открыть."
                    )
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
                    ],
                    "description": (
                        "Тип объекта. "
                        "Используй auto, если тип можно определить автоматически."
                    )
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

        "name": "download_file",

        "description": (
            "Скачать файл по прямой HTTP или HTTPS ссылке "
            "в папку Downloads. Не запускать скачанный файл."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "url": {
                    "type": "string",
                    "description": (
                        "Прямая HTTP или HTTPS ссылка на файл."
                    )
                }

            },

            "required": [
                "url"
            ]
        }
    }
}
    ]



# ============================================================
# UNIVERSAL OPEN
# ============================================================

def open_requested(target: str, target_type: str = "auto"):

    target = str(target).strip()
    target_type = str(target_type).lower().strip()

    if not target:
        return {
            "success": False,
            "message": "Не указано, что нужно открыть."
        }
    if target_type == "movie":
        return search_yandex_movie(target)

    # ========================================================
    # APPLICATION
    # ========================================================

    if target_type == "application":

        return open_application(target)

    # ========================================================
    # WEBSITE
    # ========================================================

    if target_type == "website":

        websites = {
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

        url = websites.get(
            target.lower(),
            target
        )

        return open_website(url)

    # ========================================================
    # YOUTUBE
    # ========================================================

    if target_type == "youtube":

        return play_youtube(target)

    # ========================================================
    # FILE
    # ========================================================

    if target_type == "file":

        result = find_file(target)

        if not result.get("success"):
            return result

        files = result.get("results", [])

        if not files:

            return {
                "success": False,
                "message": (
                    f"Файл '{target}' не найден."
                )
            }

        file_path = files[0]

        try:

            os.startfile(file_path)

            return {
                "success": True,
                "path": file_path,
                "message": (
                    f"Файл '{target}' открыт."
                )
            }

        except Exception as e:

            return {
                "success": False,
                "message": (
                    f"Не удалось открыть файл: {e}"
                )
            }

    # ========================================================
    # FOLDER
    # ========================================================

    if target_type == "folder":

        folders = {

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

        folder = folders.get(
            target.lower()
        )

        if folder:

            return open_folder(
                str(folder)
            )

        return open_folder(target)

    # ========================================================
    # AUTO
    # ========================================================

    if target_type == "auto":

        lower = target.lower().strip()

        # ----------------------------------------------------
        # Папки
        # ----------------------------------------------------

        folders = {

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

        if lower in folders:

            return open_folder(
                str(folders[lower])
            )

        # ----------------------------------------------------
        # Сайты
        # ----------------------------------------------------

        websites = {

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

        }

        if lower in websites:

            return open_website(
                websites[lower]
            )

        # ----------------------------------------------------
        # Музыка / видео
        # ----------------------------------------------------

        youtube_prefixes = [

            "включи музыку ",
            "включи песню ",
            "включи видео ",
            "включи ролик ",
            "найди на youtube ",
            "найди на ютуб ",

        ]

        for prefix in youtube_prefixes:

            if lower.startswith(prefix):

                query = target[
                    len(prefix):
                ].strip()

                return play_youtube(
                    query
                )

        # ----------------------------------------------------
        # Файл
        # ----------------------------------------------------

        file_result = find_file(target)

        if file_result.get("success"):

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
                        "message": (
                            f"Файл '{target}' открыт."
                        )
                    }

                except Exception:
                    pass

        # ----------------------------------------------------
        # В последнюю очередь приложение
        # ----------------------------------------------------

        return open_application(
            target
        )

    # ========================================================
    # UNKNOWN TYPE
    # ========================================================

    return {
        "success": False,
        "message": (
            f"Неизвестный тип объекта: "
            f"{target_type}"
        )
    }

# ============================================================
# ВЫПОЛНЕНИЕ TOOL
# ============================================================
async def execute_tool(name: str, arguments: dict):

    try:

        if name == "get_pc_info":
            return get_pc_info()

        elif name == "open_application":
            return open_application(
                arguments.get("application", "")
            )

        elif name == "open_website":
            return open_website(
                arguments.get("url", "")
            )

        elif name == "search_yandex":
            return search_yandex(
                arguments.get("query", "")
            )

        elif name == "play_youtube":
            return play_youtube(
                arguments.get("query", "")
            )

        elif name == "search_yandex_movie":
            return search_yandex_movie(
                arguments.get("query", "")
            )

        elif name == "get_downloads":
            return get_downloads()

        elif name == "find_file":
            return find_file(
                arguments.get("filename", "")
            )

        elif name == "open_folder":
            return open_folder(
                arguments.get("path", "")
            )

        elif name == "run_windows_command":
            return run_windows_command(
                arguments.get("command", "")
            )

        elif name == "open_requested":
            return open_requested(
                arguments.get("target", ""),
                arguments.get("target_type", "auto")
            )

        elif name == "download_file":
            return await download_file(
                arguments.get("url", "")
            )

        else:
            return {
                "success": False,
                "message": f"Неизвестный инструмент: {name}"
            }

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"Ошибка инструмента {name}: {e}"
            )
        }
# ============================================================

async def ask_groq(text: str):

    if not GROQ_API_KEY:

        return {
            "answer": (
                "Ошибка: GROQ_API_KEY не найден. "
                "Проверь файл .env."
            ),
            "action": "none",
            "query": ""
        }

    system_message = """
Ты Jarvis — умный локальный помощник пользователя.

Ты можешь:

- отвечать на обычные вопросы;
- получать информацию о компьютере;
- запускать разрешённые приложения;
- открывать сайты;
- искать через Яндекс;
- смотреть Downloads;
- искать файлы;
- открывать папки;
- выполнять безопасные команды Windows.

ВАЖНЫЕ ПРАВИЛА:

1. Если для выполнения просьбы нужен инструмент —
   используй соответствующий инструмент.

2. Не говори, что действие выполнено,
   пока инструмент действительно не вернул результат.

3. Не выдумывай информацию о компьютере.

4. Если пользователь спрашивает характеристики ПК —
   используй get_pc_info.
   
5. Если пользователь просит открыть или запустить
приложение — используй open_application.

6. Разрешено запускать любое приложение,
установленное на компьютере пользователя.

7. Не говори, что приложение запущено,
пока open_application не вернул success=true.

8. Если пользователь спрашивает про Downloads —
   используй get_downloads.

9. Если пользователь просит найти файл —
   используй find_file.

10. Если пользователь просит открыть папку —
    используй open_folder.

11. Отвечай на русском языке.

12. Будь кратким, но полезным.

13. Не выполняй опасные команды,
    связанные с удалением файлов, форматированием,
    отключением защиты Windows или повреждением системы.
    
14. Если пользователь просит найти видео, музыку,
фильм, сериал или мультфильм на YouTube —
используй play_youtube.

15. Если пользователь просит найти фильм,
сериал или мультфильм через Яндекс —
используй search_yandex_movie.

16. Если пользователь говорит:
"включи музыку", "включи видео", "включи ролик",
"посмотри фильм" и явно указывает название —
не задавай лишних вопросов, а используй
соответствующий инструмент.

17. После выполнения инструмента сообщай только
то, что реально произошло.

18. Не говори "видео запущено", если инструмент
только открыл страницу поиска.
19. Steam является разрешённым приложением.

20. Если пользователь просит:
"открой Steam",
"запусти Steam",
"включи Steam",
"открой стим",
"запусти стим",
используй open_application с:
application="steam".

21. Не используй run_windows_command для запуска Steam,
если можно использовать open_application.

22. Если пользователь просит открыть, запустить или включить
что-либо, используй open_requested.

23. open_requested является главным универсальным инструментом
для открытия объектов.

24. Для приложения используй:
target_type="application"

25. Для сайта используй:
target_type="website"

26. Для YouTube, музыки, видео или песни используй:
target_type="youtube"

27. Для файла используй:
target_type="file"

28. Для папки используй:
target_type="folder"

29. Если тип объекта очевиден, не задавай уточняющих вопросов.

30. Если пользователь говорит "открой X", используй
open_requested с target="X" и максимально подходящим
target_type.

31. После выполнения инструмента сообщай только результат
инструмента.

32. Если success=true, сообщай, что объект действительно
открыт или запущен.

33. Если success= false, не утверждай, что объект был открыт.

31. После выполнения инструмента сообщай только результат инструмента.

32. Если инструмент вернул success = true, сообщай, что объект открыт или запущен.

33. Если инструмент вернул success = false,не говори, что объект был открыт.
"""

    messages = [
        {
            "role": "system",
            "content": system_message
        }
    ]

    # Добавляем историю
    messages.extend(
        conversation_history
    )

    # Добавляем текущий запрос
    messages.append({
        "role": "user",
        "content": text
    })

    headers = {
        "Authorization": (
            f"Bearer {GROQ_API_KEY}"
        ),
        "Content-Type": "application/json"
    }

    data = {
        "model": GROQ_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2
    }

    try:

        # ====================================================
        # ПЕРВЫЙ ЗАПРОС
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
            print("Статус Groq:", response.status_code)
            print("Ответ Groq:")
            print(response.text)

            return {
                "answer": (
                    f"Ошибка Groq: {response.status_code}"
                ),
                "action": "none",
                "query": ""
            }

        # ====================================================
        # JSON
        # ====================================================

        try:

            result = response.json()

        except json.JSONDecodeError:

            print(
                "Groq вернул не JSON:"
            )

            print(
                response.text
            )

            return {
                "answer": (
                    "Groq вернул некорректный ответ."
                ),
                "action": "none",
                "query": ""
            }

        # ====================================================
        # ПРОВЕРКА CHOICES
        # ====================================================

        choices = result.get(
            "choices",
            []
        )

        if not choices:

            print(
                "В ответе Groq нет choices:"
            )

            print(result)

            return {
                "answer": (
                    "Groq не вернул сообщение."
                ),
                "action": "none",
                "query": ""
            }

        message = choices[0].get(
            "message",
            {}
        )

        if not message:

            print(
                "В ответе Groq нет message:"
            )

            print(result)

            return {
                "answer": (
                    "Groq не вернул корректное сообщение."
                ),
                "action": "none",
                "query": ""
            }

        # ====================================================
        # TOOL CALLS
        # ====================================================

        tool_calls = message.get(
            "tool_calls",
            []
        )

        # ====================================================
        # ЕСЛИ НУЖЕН TOOL
        # ====================================================

        if tool_calls:

            # Обязательно добавляем assistant message
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

                    print(
                        "Некорректные arguments:"
                    )

                    print(
                        arguments_text
                    )

                    arguments = {}

                print(
                    "Jarvis вызывает:",
                    name,
                    arguments
                )

                # --------------------------------------------
                # Выполнение инструмента
                # --------------------------------------------

                tool_result = await execute_tool(
                    name,
                    arguments
                )

                print(
                    "Результат:",
                    tool_result
                )

                # --------------------------------------------
                # Возвращаем результат Groq
                # --------------------------------------------

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get(
                        "id",
                        ""
                    ),
                    "name": name,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False
                    )
                })

            # =================================================
            # ВТОРОЙ ЗАПРОС GROQ
            # =================================================

            second_data = {
                "model": GROQ_MODEL,
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
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
                "Статус второго Groq:",
                second_response.status_code
            )

            if second_response.status_code != 200:

                print(
                    "Ответ второго Groq:",
                    second_response.text
                )

                return {
                    "answer": (
                        "Ошибка Groq после "
                        "выполнения инструмента: "
                        f"{second_response.status_code}"
                    ),
                    "action": "none",
                    "query": ""
                }

            # ----------------------------------------------
            # JSON второго ответа
            # ----------------------------------------------

            try:

                second_result = (
                    second_response.json()
                )

            except json.JSONDecodeError:

                return {
                    "answer": (
                        "Groq вернул "
                        "некорректный второй ответ."
                    ),
                    "action": "none",
                    "query": ""
                }

            second_choices = (
                second_result.get(
                    "choices",
                    []
                )
            )

            if not second_choices:

                print(
                    "Второй ответ без choices:"
                )

                print(
                    second_result
                )

                answer = (
                    "Команда выполнена."
                )

            else:

                second_message = (
                    second_choices[0]
                    .get("message", {})
                )

                answer = (
                    second_message
                    .get("content")
                    or "Команда выполнена."
                )

        # ====================================================
        # ОБЫЧНЫЙ ОТВЕТ БЕЗ TOOL
        # ====================================================

        else:

            answer = (
                message.get("content")
                or "Не удалось получить ответ."
            )

        # ====================================================
        # ПАМЯТЬ
        # ====================================================

        conversation_history.append({
            "role": "user",
            "content": text
        })

        conversation_history.append({
            "role": "assistant",
            "content": answer
        })

        while len(
            conversation_history
        ) > MAX_HISTORY:

            conversation_history.pop(0)

        # ====================================================
        # RETURN
        # ====================================================

        return {
            "answer": answer.strip(),
            "action": "none",
            "query": ""
        }

    # ========================================================
    # HTTP ERROR
    # ========================================================

    except httpx.HTTPError as e:

        print(
            "HTTP ошибка:",
            repr(e)
        )

        return {
            "answer": (
                "Не удалось подключиться к Groq."
            ),
            "action": "none",
            "query": ""
        }

    # ========================================================
    # OTHER ERROR
    # ========================================================

    except Exception as e:

        print(
            "Ошибка ask_groq:",
            repr(e)
        )

        return {
            "answer": (
                f"Произошла ошибка: {e}"
            ),
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

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

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

    max-width: 900px;

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

</style>

</head>

<body>

<h1>🤖 My Jarvis</h1>

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


<script>

const input =
    document.getElementById("text");

const chat =
    document.getElementById("chat");

const status =
    document.getElementById("status");


// ========================================================
// HTML ESCAPE
// ========================================================

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text;

    return div.innerHTML;
}


// ========================================================
// ОТПРАВКА
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
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/x-www-form-urlencoded"
                    },

                    body:
                        "text=" +
                        encodeURIComponent(text)
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

        status.innerText = "";

        chat.innerHTML += `
            <div class="bot">
                <b>Jarvis:</b>
                ${escapeHtml(
                    data.answer || ""
                )}
            </div>
        `;

        chat.scrollTop =
            chat.scrollHeight;

        speak(
            data.answer || ""
        );

    }

    catch (error) {

        console.error(error);

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
// SEND
// ========================================================

document
    .getElementById("send")
    .onclick =
    sendMessage;


// ========================================================
// ENTER
// ========================================================

input.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

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
        .getElementById("mic")
        .onclick =
        function() {

            try {

                recognition.start();

            }

            catch (error) {

                console.log(error);

            }

        };

}

else {

    document
        .getElementById("mic")
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
    print("==============================")
    print("       JARVIS STARTING")
    print("==============================")
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9013
    )

