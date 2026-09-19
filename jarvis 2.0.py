import asyncio
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote

import httpx
import numpy as np
import pyttsx3
import sounddevice as sd
import soundfile as sf
import uvicorn

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse

from faster_whisper import WhisperModel


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

# Основная локальная модель
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")

# Для слабого ноутбука:
# OLLAMA_MODEL = "qwen3:1.7b"


# ============================================================
# VOICE CONFIG
# ============================================================

SAMPLE_RATE = 16000

# Сколько секунд слушать за один раз
RECORD_SECONDS = 6

# Голос
TTS_RATE = 175

# Если True — JARVIS реагирует только на слово "джарвис"
# Если False — отвечает на любую услышанную речь
WAKE_WORD_REQUIRED = True

WAKE_WORDS = [
    "джарвис",
    "джарвис",
    "jarvis",
]


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="JARVIS LOCAL AI",
    version="4.0"
)


# ============================================================
# GLOBALS
# ============================================================

conversation = []

voice_enabled = True
voice_thread = None

tts_lock = threading.Lock()

whisper_model = None


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
Ты JARVIS — локальный голосовой ИИ-помощник пользователя.

Ты работаешь непосредственно на компьютере пользователя.
Отвечай на русском языке, если пользователь говорит по-русски.

Правила:
- Отвечай понятно и естественно.
- Не говори слишком длинно без необходимости.
- Не придумывай, что ты выполнил действие, если Python действительно его не выполнил.
- Ты можешь помогать с программированием, компьютером, играми, учёбой и обычными вопросами.
- Если пользователь просит открыть сайт, приложение или папку, Python может выполнить это действие.
- Для обычного разговора отвечай как обычный голосовой помощник.
"""


# ============================================================
# TEXT TO SPEECH
# ============================================================

def create_tts_engine():
    engine = pyttsx3.init()

    engine.setProperty("rate", TTS_RATE)
    engine.setProperty("volume", 1.0)

    # Пытаемся найти русский голос Windows
    try:
        voices = engine.getProperty("voices")

        for voice in voices:
            name = str(getattr(voice, "name", "")).lower()
            voice_id = str(getattr(voice, "id", "")).lower()

            if (
                "russian" in name
                or "russia" in name
                or "ru-ru" in voice_id
                or "рус" in name
            ):
                engine.setProperty("voice", voice.id)
                break

    except Exception:
        pass

    return engine


def speak(text: str):
    if not text:
        return

    text = clean_for_voice(text)

    print(f"\n🤖 JARVIS: {text}\n")

    try:
        with tts_lock:
            engine = create_tts_engine()
            engine.say(text)
            engine.runAndWait()
            engine.stop()

    except Exception as e:
        print("Ошибка TTS:", e)


def clean_for_voice(text: str):
    # Убираем markdown и технические символы
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

    return text.strip()


# ============================================================
# SPEECH TO TEXT
# ============================================================

def load_whisper():
    global whisper_model

    if whisper_model is not None:
        return whisper_model

    print("🎤 Загружаю модель распознавания речи...")

    try:
        whisper_model = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8"
        )

        print("✅ Whisper загружен")

    except Exception as e:
        print("Ошибка загрузки Whisper:", e)

        print("Пробую более лёгкую модель tiny...")

        whisper_model = WhisperModel(
            "tiny",
            device="cpu",
            compute_type="int8"
        )

    return whisper_model


def record_audio():
    print("\n🎤 Слушаю...")

    try:
        audio = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32"
        )

        sd.wait()

        return audio

    except Exception as e:
        print("Ошибка микрофона:", e)
        return None


def speech_to_text(audio):
    if audio is None:
        return ""

    temp_file = None

    try:
        model = load_whisper()

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as f:
            temp_file = f.name

        sf.write(
            temp_file,
            audio,
            SAMPLE_RATE
        )

        segments, info = model.transcribe(
            temp_file,
            language="ru",
            vad_filter=True,
            beam_size=5
        )

        text = " ".join(
            segment.text for segment in segments
        ).strip()

        return text

    except Exception as e:
        print("Ошибка распознавания:", e)
        return ""

    finally:
        if temp_file:
            try:
                os.remove(temp_file)
            except Exception:
                pass


# ============================================================
# OLLAMA
# ============================================================

async def ask_ollama(user_text: str):
    global conversation

    conversation.append({
        "role": "user",
        "content": user_text
    })

    # Не даём истории становиться бесконечной
    if len(conversation) > 20:
        conversation = conversation[-20:]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(conversation)

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.7
        }
    }

    try:
        async with httpx.AsyncClient(
            timeout=180
        ) as client:

            response = await client.post(
                OLLAMA_URL,
                json=payload
            )

            response.raise_for_status()

            data = response.json()

        answer = (
            data
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            answer = "Я не получил ответ от локальной модели."

        conversation.append({
            "role": "assistant",
            "content": answer
        })

        return answer

    except httpx.ConnectError:
        return (
            "Ollama не запущен. "
            "Открой Ollama и попробуй ещё раз."
        )

    except Exception as e:
        print("Ollama error:", e)

        return f"Ошибка локального ИИ: {e}"


# ============================================================
# SYNC VERSION FOR VOICE
# ============================================================

def ask_ollama_sync(text: str):
    try:
        return asyncio.run(
            ask_ollama(text)
        )
    except Exception as e:
        print("Ошибка AI:", e)
        return "Произошла ошибка локального ИИ."


# ============================================================
# WINDOWS APPLICATIONS
# ============================================================

def open_application(name: str):
    name = name.lower().strip()

    aliases = {
        "блокнот": "notepad.exe",
        "нотпад": "notepad.exe",
        "notepad": "notepad.exe",

        "калькулятор": "calc.exe",
        "calculator": "calc.exe",

        "проводник": "explorer.exe",
        "explorer": "explorer.exe",

        "cmd": "cmd.exe",
        "командная строка": "cmd.exe",

        "paint": "mspaint.exe",
        "паинт": "mspaint.exe",
        "рисование": "mspaint.exe",
    }

    program = aliases.get(name)

    if program:
        try:
            subprocess.Popen(program)
            return f"Открываю {name}."

        except Exception as e:
            return f"Не удалось открыть {name}: {e}"

    # Попытка открыть приложение через Windows
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", name],
            shell=False
        )

        return f"Пытаюсь открыть {name}."

    except Exception as e:
        return f"Не удалось открыть {name}: {e}"


# ============================================================
# WEBSITES
# ============================================================

WEBSITES = {
    "ютуб": "https://www.youtube.com",
    "youtube": "https://www.youtube.com",

    "гугл": "https://www.google.com",
    "google": "https://www.google.com",

    "яндекс": "https://ya.ru",
    "yandex": "https://ya.ru",

    "вк": "https://vk.com",
    "вконтакте": "https://vk.com",

    "телеграм": "https://web.telegram.org",
    "telegram": "https://web.telegram.org",
}


def open_website(name: str):
    name = name.lower().strip()

    if name in WEBSITES:
        webbrowser.open(WEBSITES[name])
        return f"Открываю {name}."

    return None


# ============================================================
# SEARCH
# ============================================================

def search_yandex(query: str):
    url = (
        "https://yandex.ru/search/?text="
        + quote(query)
    )

    webbrowser.open(url)

    return f"Ищу в Яндексе: {query}"


def search_youtube(query: str):
    url = (
        "https://www.youtube.com/results?search_query="
        + quote(query)
    )

    webbrowser.open(url)

    return f"Ищу на YouTube: {query}"


# ============================================================
# FOLDERS
# ============================================================

def open_folder(folder_name: str):
    home = Path.home()

    folders = {
        "загрузки": home / "Downloads",
        "downloads": home / "Downloads",

        "рабочий стол": home / "Desktop",
        "desktop": home / "Desktop",

        "документы": home / "Documents",
        "documents": home / "Documents",
    }

    folder_name = folder_name.lower().strip()

    folder = folders.get(folder_name)

    if folder and folder.exists():
        os.startfile(folder)
        return f"Открываю папку {folder_name}."

    return None


# ============================================================
# PC INFO
# ============================================================

def get_pc_info():
    system = platform.system()
    version = platform.version()
    machine = platform.machine()
    processor = platform.processor()

    try:
        disk = shutil.disk_usage(Path.home().anchor)

        total_gb = disk.total / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)

        disk_info = (
            f"Свободно {free_gb:.1f} ГБ "
            f"из {total_gb:.1f} ГБ."
        )

    except Exception:
        disk_info = "Информацию о диске получить не удалось."

    return (
        f"Система: {system}. "
        f"Версия: {version}. "
        f"Процессор: {processor}. "
        f"Архитектура: {machine}. "
        f"{disk_info}"
    )


# ============================================================
# COMMAND ROUTER
# ============================================================

def handle_local_command(text: str):
    command = text.lower().strip()

    # -----------------------------
    # Открыть сайт
    # -----------------------------

    match = re.match(
        r"^(?:открой|запусти)\s+(.+)$",
        command
    )

    if match:
        target = match.group(1).strip()

        website_result = open_website(target)

        if website_result:
            return website_result

        folder_result = open_folder(target)

        if folder_result:
            return folder_result

        if target in [
            "калькулятор",
            "блокнот",
            "нотпад",
            "проводник",
            "cmd",
            "paint",
            "паинт",
        ]:
            return open_application(target)

    # -----------------------------
    # YouTube
    # -----------------------------

    if command.startswith("найди на ютубе "):
        query = command.replace(
            "найди на ютубе ",
            "",
            1
        )

        return search_youtube(query)

    if command.startswith("включи на ютубе "):
        query = command.replace(
            "включи на ютубе ",
            "",
            1
        )

        return search_youtube(query)

    # -----------------------------
    # Yandex
    # -----------------------------

    if command.startswith("найди в яндексе "):
        query = command.replace(
            "найди в яндексе ",
            "",
            1
        )

        return search_yandex(query)

    # -----------------------------
    # PC info
    # -----------------------------

    if (
        "характеристик" in command
        or "информация о компьютере" in command
        or "что за компьютер" in command
    ):
        return get_pc_info()

    # -----------------------------
    # Steam
    # -----------------------------

    if "открой steam" in command:
        steam_paths = [
            Path(os.environ.get(
                "PROGRAMFILES(X86)",
                "C:\\Program Files (x86)"
            )) / "Steam" / "steam.exe",

            Path(os.environ.get(
                "PROGRAMFILES",
                "C:\\Program Files"
            )) / "Steam" / "steam.exe",

            Path.home()
            / "AppData"
            / "Local"
            / "Steam"
            / "steam.exe",
        ]

        for steam in steam_paths:
            if steam.exists():
                subprocess.Popen([str(steam)])
                return "Открываю Steam."

        return "Steam не найден."

    return None


# ============================================================
# PROCESS USER MESSAGE
# ============================================================

def process_text(text: str):
    text = text.strip()

    if not text:
        return "Я не расслышал команду."

    print(f"\n👤 Ты: {text}")

    # Сначала локальные команды Windows
    command_result = handle_local_command(text)

    if command_result:
        print(f"🤖 JARVIS: {command_result}")
        return command_result

    # Если это обычный вопрос — отправляем в Ollama
    answer = ask_ollama_sync(text)

    return answer


# ============================================================
# WAKE WORD
# ============================================================

def has_wake_word(text: str):
    text = text.lower()

    for word in WAKE_WORDS:
        if word in text:
            return True

    return False


def remove_wake_word(text: str):
    result = text

    for word in WAKE_WORDS:
        result = re.sub(
            word,
            "",
            result,
            flags=re.IGNORECASE
        )

    return result.strip(" ,.!?-")


# ============================================================
# VOICE LOOP
# ============================================================

def voice_loop():
    global voice_enabled

    print("\n" + "=" * 60)
    print("🎙️ JARVIS VOICE MODE")
    print("=" * 60)

    print("Микрофон включён.")

    if WAKE_WORD_REQUIRED:
        print("Скажи: «Джарвис ...»")
    else:
        print("JARVIS реагирует на любую речь.")

    print("=" * 60)

    while voice_enabled:

        try:
            audio = record_audio()

            if audio is None:
                time.sleep(1)
                continue

            text = speech_to_text(audio)

            if not text:
                continue

            print(f"🎤 Распознано: {text}")

            # Если нужен wake word
            if WAKE_WORD_REQUIRED:

                if not has_wake_word(text):
                    continue

                text = remove_wake_word(text)

                if not text:
                    speak("Да, я слушаю.")
                    continue

            answer = process_text(text)

            if answer:
                speak(answer)

        except KeyboardInterrupt:
            break

        except Exception as e:
            print("Voice loop error:", e)
            time.sleep(2)

    print("🎙️ Голосовой режим остановлен.")


# ============================================================
# START VOICE
# ============================================================

def start_voice():
    global voice_thread

    if voice_thread is not None:
        return

    voice_thread = threading.Thread(
        target=voice_loop,
        daemon=True
    )

    voice_thread.start()


# ============================================================
# WEB INTERFACE
# ============================================================

HTML = """
<!DOCTYPE html>
<html lang="ru">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>JARVIS LOCAL AI</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0b0f14;
    color: white;
    font-family: Arial, sans-serif;
}

.container {
    width: min(900px, 94%);
    margin: 40px auto;
}

h1 {
    text-align: center;
    font-size: 38px;
    margin-bottom: 10px;
}

.status {
    text-align: center;
    color: #00ff9d;
    margin-bottom: 20px;
}

#chat {
    height: 550px;
    overflow-y: auto;
    background: #111820;
    border-radius: 18px;
    padding: 20px;
    border: 1px solid #263241;
}

.message {
    padding: 13px 16px;
    border-radius: 15px;
    margin-bottom: 12px;
    max-width: 80%;
    line-height: 1.5;
    white-space: pre-wrap;
}

.user {
    background: #174ea6;
    margin-left: auto;
}

.jarvis {
    background: #202a35;
    margin-right: auto;
}

.input-area {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

input {
    flex: 1;
    padding: 16px;
    border: none;
    outline: none;
    border-radius: 12px;
    background: #18212b;
    color: white;
    font-size: 16px;
}

button {
    border: none;
    border-radius: 12px;
    padding: 0 22px;
    background: #00b894;
    color: white;
    font-size: 16px;
    cursor: pointer;
}

button:hover {
    background: #00a383;
}

.info {
    margin-top: 15px;
    color: #8e9baa;
    text-align: center;
    font-size: 14px;
}

</style>

</head>

<body>

<div class="container">

<h1>🤖 JARVIS</h1>

<div class="status">
● LOCAL AI ONLINE
</div>

<div id="chat">

<div class="message jarvis">
JARVIS запущен.
Я работаю локально на этом компьютере.
</div>

</div>

<div class="input-area">

<input
    id="message"
    placeholder="Напиши команду..."
    autocomplete="off"
>

<button onclick="sendMessage()">
Отправить
</button>

</div>

<div class="info">
Голосовой режим работает через микрофон компьютера.
</div>

</div>


<script>

const input = document.getElementById("message");
const chat = document.getElementById("chat");

input.addEventListener(
    "keydown",
    function(event) {
        if (event.key === "Enter") {
            sendMessage();
        }
    }
);


function addMessage(text, type) {

    const div = document.createElement("div");

    div.className = "message " + type;

    div.textContent = text;

    chat.appendChild(div);

    chat.scrollTop = chat.scrollHeight;
}


async function sendMessage() {

    const text = input.value.trim();

    if (!text) {
        return;
    }

    addMessage(text, "user");

    input.value = "";

    try {

        const formData = new FormData();

        formData.append("message", text);

        const response = await fetch(
            "/chat",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        addMessage(
            data.answer,
            "jarvis"
        );

        // Браузер тоже может произнести ответ
        if ("speechSynthesis" in window) {

            const speech =
                new SpeechSynthesisUtterance(
                    data.answer
                );

            speech.lang = "ru-RU";
            speech.rate = 1.0;

            window.speechSynthesis.speak(
                speech
            );
        }

    } catch (error) {

        addMessage(
            "Ошибка соединения с JARVIS.",
            "jarvis"
        );

    }
}

</script>

</body>

</html>
"""


# ============================================================
# ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML


@app.post("/chat")
async def chat(message: str = Form(...)):

    answer = await ask_ollama(message)

    return JSONResponse({
        "answer": answer
    })


@app.get("/status")
async def status():

    return {
        "status": "online",
        "ai": "local",
        "model": OLLAMA_MODEL,
        "ollama": OLLAMA_URL,
        "voice": voice_enabled,
        "system": platform.system()
    }


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("                 🤖 JARVIS LOCAL AI")
    print("=" * 60)
    print()
    print(f"Модель: {OLLAMA_MODEL}")
    print("Ollama: LOCAL")
    print("Голос: ENABLED")
    print()
    print("Веб-интерфейс:")
    print("http://127.0.0.1:9013")
    print()
    print("Голосовой режим запускается автоматически.")
    print()
    print("=" * 60)

    # Запускаем голос
    start_voice()

    # Запускаем сервер
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9013
    )