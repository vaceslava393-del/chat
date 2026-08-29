import os
import json
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote

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

    application = str(
        application
    ).lower().strip()

    if not application:

        return None

    # Точное совпадение
    if application in ALLOWED_APPS:

        return ALLOWED_APPS[
            application
        ]

    # Частичное совпадение
    matches = []

    for name, path in ALLOWED_APPS.items():

        if application in name:

            matches.append(
                (name, path)
            )

    if len(matches) == 1:

        return matches[0][1]

    return None


# ============================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================================

def open_application(application: str):

    application = str(
        application
    ).lower().strip()

    if not application:

        return {
            "success": False,
            "message": (
                "Название приложения "
                "не указано."
            )
        }

    program = find_application(
        application
    )

    if not program:

        # Обновляем список,
        # если приложение появилось после запуска Jarvis
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

        program = find_application(
            application
        )

    if not program:

        return {
            "success": False,
            "message": (
                f"Приложение '{application}' "
                f"не найдено."
            )
        }

    try:

        print(
            "Запускаю приложение:",
            application
        )

        print(
            "Путь:",
            program
        )

        # .lnk и .url лучше открывать
        # через Windows shell
        if program.lower().endswith(
            (".lnk", ".url")
        ):

            os.startfile(program)

        # Системные команды
        elif (
            program.lower() in
            [
                "notepad.exe",
                "calc.exe",
                "explorer.exe",
                "mspaint.exe",
                "cmd.exe",
            ]
        ):

            subprocess.Popen(
                [program],
                shell=False
            )

        # Полный путь к EXE
        else:

            if not os.path.isfile(program):

                return {
                    "success": False,
                    "message": (
                        "Файл приложения "
                        f"не найден: {program}"
                    )
                }

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

TOOLS = [

    {
        "type": "function",

        "function": {

            "name": "get_pc_info",

            "description": (
                "Получить информацию о компьютере Windows: "
                "операционная система, версия, процессор, "
                "количество CPU, имя компьютера и место "
                "на системном диске."
            ),

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

            "name": "open_application",

            "description": (
                "Запустить любое приложение, установленное "
                "на компьютере Windows. Можно использовать "
                "название приложения: Chrome, Edge, Firefox, "
                "Telegram, Discord, Steam, VS Code, Photoshop, "
                "Minecraft, Notepad, Calculator и другие."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "application": {
                        "type": "string",

                        "description": (
                            "Название приложения, которое "
                            "нужно запустить."
                        )
                    }

                },

                "required": [
                    "application"
                ]
            }
        }
    },

    {
        "type": "function",

        "function": {

            "name": "open_website",

            "description": (
                "Открыть указанный сайт "
                "в браузере Windows."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "url": {
                        "type": "string",

                        "description": (
                            "Адрес сайта, например "
                            "https://google.com"
                        )
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

            "name": "search_yandex",

            "description": (
                "Открыть поиск Яндекс "
                "с указанным поисковым запросом."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "query": {
                        "type": "string",

                        "description": (
                            "Поисковый запрос."
                        )
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

            "description": (
                "Получить список файлов и папок "
                "в папке Downloads пользователя."
            ),

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

            "description": (
                "Найти файл по имени или части имени "
                "в папках Downloads, Desktop и Documents."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "filename": {
                        "type": "string",

                        "description": (
                            "Имя или часть имени файла."
                        )
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

            "name": "open_folder",

            "description": (
                "Открыть папку или директорию "
                "Windows по указанному пути."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "path": {
                        "type": "string",

                        "description": (
                            "Полный путь к папке, например "
                            "C:\\Users\\User\\Downloads"
                        )
                    }

                },

                "required": [
                    "path"
                ]
            }
        }
    },

    {
        "type": "function",

        "function": {

            "name": "run_windows_command",

            "description": (
                "Выполнить команду Windows CMD для "
                "системного действия. Использовать только "
                "когда для задачи нет отдельного инструмента."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "command": {
                        "type": "string",

                        "description": (
                            "Команда Windows CMD."
                        )
                    }

                },

                "required": [
                    "command"
                ]
            }
        }
    },

    {
        "type": "function",

        "function": {

            "name": "play_youtube",

            "description": (
                "Найти видео, музыку, фильм, сериал "
                "или мультфильм на YouTube и открыть "
                "результат в браузере."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "query": {
                        "type": "string",

                        "description": (
                            "Что найти на YouTube."
                        )
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

            "name": "search_yandex_movie",

            "description": (
                "Найти фильм, сериал или мультфильм "
                "через поиск Яндекс."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "query": {
                        "type": "string",

                        "description": (
                            "Название фильма, сериала "
                            "или мультфильма."
                        )
                    }

                },

                "required": [
                    "query"
                ]
            }
        }
    }

]












# ============================================================
# ВЫПОЛНЕНИЕ TOOL
# ============================================================

def execute_tool(name: str, arguments: dict):

    try:

        if name == "get_pc_info":
            return get_pc_info()

        if name == "open_application":
            return open_application(
                arguments.get("application", "")
            )

        if name == "open_website":
            return open_website(
                arguments.get("url", "")
            )
        if name == "open_steam":
            return open_steam()

        if name == "search_yandex":
            return search_yandex(
                arguments.get("query", "")
            )

        if name == "play_youtube":
            return play_youtube(
                arguments.get("query", "")
            )
        if name == "search_yandex_movie":
            return search_yandex_movie(
            arguments.get("query", "")
        )


        return {
            "success": False,
            "message": f"Неизвестный инструмент: {name}"
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"Ошибка инструмента {name}: {e}"
        }

# ============================================================
# GROQ
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

                tool_result = execute_tool(
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

