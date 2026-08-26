import os
from dotenv import load_dotenv
import json
import httpx

from fastapi import FastAPI, Form
from starlette.responses import HTMLResponse, JSONResponse

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
GROQ_URL = os.getenv("GROQ_URL")



app = FastAPI()



@app.get("/")
def home():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="ru">

<head>
    <meta charset="UTF-8">
    <title>My Jarvis</title>

    <style>
        body {
            background: #101010;
            color: white;
            font-family: Arial;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
        }

        h1 {
            text-align: center;
        }

        #chat {
            margin-top: 30px;
        }

        .user {
            background: #174ea6;
            padding: 12px;
            margin: 10px 0;
            border-radius: 12px;
        }

        .bot {
            background: #252525;
            padding: 12px;
            margin: 10px 0;
            border-radius: 12px;
        }

        input {
            width: 70%;
            padding: 12px;
            font-size: 18px;
            border-radius: 8px;
            border: none;
        }

        button {
            padding: 12px 18px;
            font-size: 18px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin-left: 5px;
        }

        #mic {
            background: #b00020;
            color: white;
        }

        #send {
            background: #1976d2;
            color: white;
        }

        #status {
            text-align: center;
            margin-top: 15px;
            color: #aaa;
        }
    </style>
</head>

<body>

<h1>🤖 My Jarvis</h1>

<div>
    <input
        id="text"
        placeholder="Скажи или напиши команду..."
    >

    <button id="send">Отправить</button>
    <button id="mic">🎤</button>
</div>

<div id="status"></div>

<div id="chat"></div>


<script>

const input = document.getElementById("text");
const chat = document.getElementById("chat");
const status = document.getElementById("status");


// ============================
// ОТПРАВКА СООБЩЕНИЯ
// ============================

async function sendMessage() {

    const text = input.value.trim();

    if (!text) {
        return;
    }

    chat.innerHTML += `
        <div class="user">
            <b>Вы:</b> ${escapeHtml(text)}
        </div>
    `;

    input.value = "";

    status.innerText = "🤖 Думаю...";

    try {

        const response = await fetch("/chat", {
            method: "POST",

            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },

            body: "text=" + encodeURIComponent(text)
        });

        const data = await response.json();

        status.innerText = "";

        chat.innerHTML += `
            <div class="bot">
                <b>Jarvis:</b> ${escapeHtml(data.answer)}
            </div>
        `;


        // ============================
        // ОТКРЫТИЕ ЯНДЕКСА
        // ============================

        if (data.action === "yandex") {

            const query = data.query;

            const yandexUrl =
                "https://yandex.ru/search/?text="
                + encodeURIComponent(query);

            window.open(yandexUrl, "_blank");

            speak(
                "Открываю Яндекс и ищу " + query
            );

        } else {

            // Обычный ответ голосом
            speak(data.answer);
        }

    } catch (error) {

        status.innerText = "Ошибка";

        console.error(error);

        speak("Произошла ошибка.");
    }
}


// ============================
// КНОПКА ОТПРАВИТЬ
// ============================

document.getElementById("send").onclick = sendMessage;


// Enter
input.addEventListener("keydown", function(event) {

    if (event.key === "Enter") {
        sendMessage();
    }

});


// ============================
// ГОЛОСОВОЙ ВВОД
// ============================

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

let recognition;

if (SpeechRecognition) {

    recognition = new SpeechRecognition();

    recognition.lang = "ru-RU";

    recognition.continuous = false;

    recognition.interimResults = false;


    recognition.onstart = function() {

        status.innerText = "🎤 Слушаю...";

    };


    recognition.onresult = function(event) {

        const text =
            event.results[0][0].transcript;

        input.value = text;

        status.innerText =
            "Вы сказали: " + text;

        sendMessage();
    };


    recognition.onerror = function(event) {

        console.error(event.error);

        status.innerText =
            "Не удалось распознать речь";
    };


    recognition.onend = function() {

        if (
            status.innerText === "🎤 Слушаю..."
        ) {
            status.innerText = "";
        }

    };


    document.getElementById("mic").onclick =
        function() {

            recognition.start();

        };

} else {

    document.getElementById("mic").disabled = true;

    status.innerText =
        "Ваш браузер не поддерживает голосовой ввод";
}


// ============================
// ОЗВУЧКА
// ============================

function speak(text) {

    if (!("speechSynthesis" in window)) {
        return;
    }

    speechSynthesis.cancel();

    const utterance =
        new SpeechSynthesisUtterance(text);

    utterance.lang = "ru-RU";

    utterance.rate = 1;

    utterance.pitch = 1;

    speechSynthesis.speak(utterance);
}


// ============================
// ЗАЩИТА HTML
// ============================

function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}

</script>

</body>
</html>
""")


# =====================================
# GROQ
# =====================================

async def ask_groq(text):
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": GROQ_MODEL,

            "messages": [
                {
                    "role": "system",
                    "content": """
    Ты Jarvis — дружелюбный голосовой помощник.

    Отвечай обычным текстом на обычные вопросы.

    Если пользователь хочет что-то найти через Яндекс,
    ответь СТРОГО в таком формате:

    YANDEX: поисковый запрос

    Например:

    Пользователь: найди на Яндексе котиков
    Ответ:
    YANDEX: котики

    Пользователь: поищи в Яндексе Python FastAPI
    Ответ:
    YANDEX: Python FastAPI

    Если пользователь не просит искать через Яндекс,
    не используй YANDEX:.
    """
                },

                {
                    "role": "user",
                    "content": text
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=data
            )

        print("Статус Groq:", response.status_code)
        print("Ответ Groq:", response.text)

        response.raise_for_status()

        result = response.json()

        return result["choices"][0]["message"]["content"]


# =====================================
# CHAT
# =====================================

@app.post("/chat")
async def chat(text: str = Form(...)):

    result = await ask_groq(text)

    result = result.strip()

    # ============================
    # ЯНДЕКС
    # ============================

    if result.startswith("YANDEX:"):

        query = result.replace("YANDEX:", "", 1).strip()

        return JSONResponse({
            "answer": f"Ищу в Яндексе: {query}",
            "action": "yandex",
            "query": query
        })

    # ============================
    # ОБЫЧНЫЙ ОТВЕТ
    # ============================

    return JSONResponse({
        "answer": result,
        "action": "none",
        "query": ""
    })


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9012
    )