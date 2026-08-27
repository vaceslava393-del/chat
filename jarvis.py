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


# ============================================================
# ПРОВЕРКА GROQ
# ============================================================

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY не найден в .env")

else:
    print("Groq API key найден")


# ============================================================
# ПАМЯТЬ ДИАЛОГА
# ============================================================

conversation_history = []

MAX_HISTORY = 20


# ============================================================
# СИСТЕМНЫЕ ИНСТРУМЕНТЫ
# ============================================================

def get_pc_info():
    """
    Возвращает информацию о компьютере.
    """

    try:
        total, used, free = shutil.disk_usage("C:\\")

        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "computer_name": platform.node(),
            "cpu_count": os.cpu_count(),
            "disk_c_total_gb": round(total / 1024**3, 2),
            "disk_c_used_gb": round(used / 1024**3, 2),
            "disk_c_free_gb": round(free / 1024**3, 2)
        }

    except Exception as e:
        return {
            "error": str(e)
        }


# ============================================================
# ЗАПУСК ПРИЛОЖЕНИЙ
# ============================================================

ALLOWED_APPS = {
    "notepad": "notepad.exe",
    "блокнот": "notepad.exe",

    "calculator": "calc.exe",
    "калькулятор": "calc.exe",

    "explorer": "explorer.exe",
    "проводник": "explorer.exe",

    "paint": "mspaint.exe",
    "paint": "mspaint.exe",
    "рисование": "mspaint.exe",

    "cmd": "cmd.exe",

    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",

    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",

    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe"
}


def open_application(application: str):

    application = application.lower().strip()

    if application not in ALLOWED_APPS:
        return {
            "success": False,
            "message": (
                f"Приложение '{application}' не находится "
                f"в списке разрешённых."
            )
        }

    program = ALLOWED_APPS[application]

    try:

        if program.endswith(".exe") and "\\" not in program:
            subprocess.Popen(program)

        else:

            if not os.path.exists(program):
                return {
                    "success": False,
                    "message": f"Файл приложения не найден: {program}"
                }

            subprocess.Popen(program)

        return {
            "success": True,
            "message": f"{application} запущен."
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"Не удалось запустить приложение: {e}"
        }


# ============================================================
# ОТКРЫТИЕ САЙТА
# ============================================================

def open_website(url: str):

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:

        webbrowser.open(url)

        return {
            "success": True,
            "url": url,
            "message": f"Открыт сайт {url}"
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


# ============================================================
# ПОИСК В ЯНДЕКСЕ
# ============================================================

def search_yandex(query: str):

    query = query.strip()

    url = (
        "https://yandex.ru/search/?text="
        + quote(query)
    )

    try:

        webbrowser.open(url)

        return {
            "success": True,
            "query": query,
            "url": url,
            "message": f"Поиск в Яндексе: {query}"
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

    downloads = Path.home() / "Downloads"

    if not downloads.exists():

        return {
            "success": False,
            "message": "Папка Downloads не найдена."
        }

    try:

        files = []

        for item in downloads.iterdir():

            files.append({
                "name": item.name,
                "type": "folder" if item.is_dir() else "file"
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

    filename = filename.lower().strip()

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

        except (PermissionError, OSError):
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

    try:

        if not os.path.exists(path):

            return {
                "success": False,
                "message": f"Путь не существует: {path}"
            }

        os.startfile(path)

        return {
            "success": True,
            "message": f"Открыта папка: {path}"
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
                "процессор, система, имя компьютера, "
                "количество CPU и свободное место на диске C."
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
                "Запустить разрешённое приложение "
                "на компьютере пользователя."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": (
                            "Название приложения. "
                            "Например: Chrome, Edge, Firefox, "
                            "Блокнот, Калькулятор."
                        )
                    }
                },
                "required": ["application"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": (
                "Открыть сайт в браузере пользователя."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL сайта"
                    }
                },
                "required": ["url"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "search_yandex",
            "description": (
                "Выполнить поиск пользователя через Яндекс."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос"
                    }
                },
                "required": ["query"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_downloads",
            "description": (
                "Показать содержимое папки Downloads "
                "пользователя."
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
                "Найти файл в Downloads, Desktop или Documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Имя или часть имени файла"
                    }
                },
                "required": ["filename"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": (
                "Открыть существующую папку Windows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Путь к папке"
                    }
                },
                "required": ["path"]
            }
        }
    }
]


# ============================================================
# ВЫПОЛНЕНИЕ TOOL
# ============================================================

def execute_tool(name, arguments):

    try:

        if name == "get_pc_info":
            return get_pc_info()

        if name == "open_application":
            return open_application(
                arguments["application"]
            )

        if name == "open_website":
            return open_website(
                arguments["url"]
            )

        if name == "search_yandex":
            return search_yandex(
                arguments["query"]
            )

        if name == "get_downloads":
            return get_downloads()

        if name == "find_file":
            return find_file(
                arguments["filename"]
            )

        if name == "open_folder":
            return open_folder(
                arguments["path"]
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

async def ask_groq(text):

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
- открывать папки.

ВАЖНЫЕ ПРАВИЛА:

1. Если для выполнения просьбы нужен инструмент — используй его.

2. Не говори, что ты выполнил действие, пока инструмент
   действительно не вернул результат.

3. Не выдумывай информацию о компьютере.

4. Если пользователь спрашивает характеристики ПК,
   используй get_pc_info.

5. Если пользователь просит открыть приложение,
   используй open_application.

6. Если пользователь просит открыть сайт,
   используй open_website.

7. Если пользователь говорит "найди в Яндексе",
   используй search_yandex.

8. Если пользователь спрашивает про Downloads,
   используй get_downloads.

9. Если пользователь просит найти файл,
   используй find_file.

10. Отвечай на русском языке.

11. Будь кратким, но полезным.

12. Никогда не выполняй опасные действия,
    которых нет среди разрешённых инструментов.
"""

    messages = [
        {
            "role": "system",
            "content": system_message
        }
    ]

    messages.extend(conversation_history)

    messages.append({
        "role": "user",
        "content": text
    })

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
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
                "Ответ Groq:",
                response.text
            )

            return {
                "answer": (
                    f"Ошибка Groq: "
                    f"{response.status_code}"
                ),
                "action": "none",
                "query": ""
            }

        result = response.json()

        message = result["choices"][0]["message"]

        # ====================================================
        # TOOL CALLS
        # ====================================================

        tool_calls = message.get("tool_calls", [])

        if tool_calls:

            messages.append(message)

            for tool_call in tool_calls:

                function = tool_call["function"]

                name = function["name"]

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

                print(
                    "Jarvis вызывает:",
                    name,
                    arguments
                )

                tool_result = execute_tool(
                    name,
                    arguments
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": name,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False
                    )
                })

            # ================================================
            # ПОВТОРНЫЙ ЗАПРОС К GROQ
            # ================================================

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

            if second_response.status_code != 200:

                print(
                    "Ошибка второго запроса:",
                    second_response.text
                )

                return {
                    "answer": (
                        "Действие выполнено, "
                        "но я не смог сформировать ответ."
                    ),
                    "action": "none",
                    "query": ""
                }

            second_result = second_response.json()

            answer = (
                second_result["choices"][0]
                ["message"]
                ["content"]
            )

        else:

            answer = message.get(
                "content",
                "Не удалось получить ответ."
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

        while len(conversation_history) > MAX_HISTORY:

            conversation_history.pop(0)

        return {
            "answer": answer.strip(),
            "action": "none",
            "query": ""
        }

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
# CHAT
# ============================================================

@app.post("/chat")
async def chat(text: str = Form(...)):

    result = await ask_groq(text)

    return JSONResponse(result)


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

    font-family:
        Arial,
        sans-serif;

    max-width: 900px;

    margin:
        0 auto;

    padding:
        30px 20px;
}

h1 {

    text-align: center;

    color:
        #4fc3f7;

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

    border:
        1px solid #333;

    background:
        #171b22;

    color: white;

    outline: none;
}

input:focus {

    border-color:
        #1976d2;
}

button {

    padding:
        12px 18px;

    font-size: 16px;

    border: none;

    border-radius: 10px;

    cursor: pointer;

    color: white;
}

#send {

    background:
        #1976d2;
}

#mic {

    background:
        #b00020;
}

button:hover {

    opacity: .85;
}

#status {

    text-align:
        center;

    min-height:
        24px;

    color:
        #aaa;

    margin-bottom:
        15px;
}

#chat {

    display:
        flex;

    flex-direction:
        column;

    gap:
        10px;
}

.user,
.bot {

    padding:
        14px;

    border-radius:
        14px;

    line-height:
        1.5;

    white-space:
        pre-wrap;
}

.user {

    background:
        #174ea6;

    align-self:
        flex-end;

    max-width:
        80%;
}

.bot {

    background:
        #20252d;

    align-self:
        flex-start;

    max-width:
        90%;
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

    div.textContent = text;

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
            await fetch("/chat", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/x-www-form-urlencoded"
                },

                body:
                    "text=" +
                    encodeURIComponent(text)
            });

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
                ${escapeHtml(data.answer)}
            </div>
        `;

        chat.scrollTop =
            chat.scrollHeight;

        speak(data.answer);

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
    .onclick = sendMessage;


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
        .disabled = true;

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
    print(
        "Open in browser:"
    )
    print(
        "http://127.0.0.1:9013"
    )
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9013
    )