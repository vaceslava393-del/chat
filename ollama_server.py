import httpx
import uvicorn

from fastapi import FastAPI
from pydantic import BaseModel


# ============================================================
# НАСТРОЙКИ
# ============================================================

# Ollama уже запущен отдельно
OLLAMA_URL = "http://127.0.0.1:11434"

# Посмотри название модели через: ollama list
OLLAMA_MODEL = "llama3.2"


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(title="JARVIS AI")


# ============================================================
# МОДЕЛЬ ЗАПРОСА
# ============================================================

class ChatRequest(BaseModel):
    message: str


# ============================================================
# ГЛАВНАЯ
# ============================================================

@app.get("/")
async def home():
    return {
        "status": "online",
        "name": "JARVIS AI",
        "ollama": OLLAMA_URL,
        "model": OLLAMA_MODEL
    }


# ============================================================
# ПРОВЕРКА OLLAMA
# ============================================================

@app.get("/ollama")
async def check_ollama():

    try:
        async with httpx.AsyncClient(timeout=10) as client:

            response = await client.get(
                f"{OLLAMA_URL}/api/tags"
            )

            response.raise_for_status()

            data = response.json()

            return {
                "status": "online",
                "models": data.get("models", [])
            }

    except Exception as e:

        return {
            "status": "offline",
            "error": str(e)
        }


# ============================================================
# ЧАТ С OLLAMA
# ============================================================

@app.post("/chat")
async def chat(request: ChatRequest):

    try:

        async with httpx.AsyncClient(timeout=120) as client:

            response = await client.post(
                f"{OLLAMA_URL}/api/chat",

                json={
                    "model": OLLAMA_MODEL,

                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Ты JARVIS — умный помощник. "
                                "Отвечай на русском языке."
                            )
                        },
                        {
                            "role": "user",
                            "content": request.message
                        }
                    ],

                    "stream": False
                }
            )

            response.raise_for_status()

            data = response.json()

            return {
                "success": True,
                "answer": data["message"]["content"]
            }

    except httpx.ConnectError:

        return {
            "success": False,
            "error": (
                "Ollama не запущен или недоступен "
                "по адресу " + OLLAMA_URL
            )
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# ЗАПУСК JARVIS
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("🤖 JARVIS AI")
    print("=" * 60)

    print()
    print("Ollama:", OLLAMA_URL)
    print("Модель:", OLLAMA_MODEL)
    print()
    print("JARVIS:")
    print("http://127.0.0.1:8000")
    print()
    print("Проверка Ollama:")
    print("http://127.0.0.1:8000/ollama")
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )