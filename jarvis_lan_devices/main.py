import os
import re
import subprocess
import webbrowser
from pathlib import Path
from contextlib import asynccontextmanager
from urllib.parse import quote_plus, urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_URL = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
HOST = "127.0.0.1"
PORT = int(os.getenv("JARVIS_PORT", "9014"))

# Разрешённый список приложений Windows. Произвольные команды не выполняются.
ALLOWED_APPS = {
    "calculator": {"label": "Калькулятор", "command": ["calc.exe"]},
    "notepad": {"label": "Блокнот", "command": ["notepad.exe"]},
    "paint": {"label": "Paint", "command": ["mspaint.exe"]},
    "explorer": {"label": "Проводник", "command": ["explorer.exe"]},
    "task_manager": {"label": "Диспетчер задач", "command": ["taskmgr.exe"]},
    "settings": {"label": "Параметры Windows", "command": ["explorer.exe", "ms-settings:"]},
    "cmd": {"label": "Командная строка", "command": ["cmd.exe"]},
}

APP_ALIASES = {
    "калькулятор": "calculator", "calculator": "calculator",
    "блокнот": "notepad", "notepad": "notepad",
    "paint": "paint", "паинт": "paint", "пейнт": "paint",
    "проводник": "explorer", "файлы": "explorer", "explorer": "explorer",
    "диспетчер задач": "task_manager", "task manager": "task_manager",
    "параметры": "settings", "настройки": "settings", "настройки windows": "settings",
    "командная строка": "cmd", "командную строку": "cmd", "cmd": "cmd",
}

SITES = {
    "ютуб": "https://www.youtube.com", "youtube": "https://www.youtube.com",
    "гугл": "https://www.google.com", "google": "https://www.google.com",
    "яндекс": "https://yandex.ru", "википедия": "https://ru.wikipedia.org",
    "вк": "https://vk.com", "вконтакте": "https://vk.com",
    "почта": "https://mail.google.com", "gmail": "https://mail.google.com",
    "steam": "https://store.steampowered.com", "стим": "https://store.steampowered.com",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("JARVIS запускается...")
    yield
    print("JARVIS остановлен.")

app = FastAPI(title="JARVIS Local AI", version="3.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=6000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)

class LaunchRequest(BaseModel):
    app_name: str = Field(min_length=1, max_length=40)

class ActionRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)

def find_installed_apps():
    """Ищет ярлыки приложений в меню Пуск и на рабочем столе Windows."""
    import hashlib

    env = os.environ
    folders = [
        Path(env.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(env.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path.home() / "Desktop",
        Path.home() / "OneDrive/Desktop",
    ]
    found = {}
    for folder in folders:
        if not folder.is_dir():
            continue
        try:
            for shortcut in folder.rglob("*"):
                if shortcut.suffix.lower() not in (".lnk", ".url") or not shortcut.is_file():
                    continue
                label = shortcut.stem.strip()
                if not label or any(word in label.casefold() for word in
                                     ("uninstall", "удалить программу", "деинсталляция")):
                    continue
                try:
                    resolved = str(shortcut.resolve())
                except OSError:
                    resolved = str(shortcut)
                app_id = "shortcut_" + hashlib.sha256(resolved.casefold().encode("utf-8")).hexdigest()[:20]
                found[app_id] = {"label": label, "shortcut": str(shortcut), "kind": "shortcut"}
        except OSError:
            continue
    return found


def get_all_apps():
    result = {key: dict(value, kind="command") for key, value in ALLOWED_APPS.items()}
    result.update(find_installed_apps())
    return result


def launch_allowed_app(app_name: str):
    item = get_all_apps().get(app_name)
    if item is None:
        raise HTTPException(status_code=404, detail="Приложение не найдено. Обнови список приложений.")
    try:
        if item.get("kind") == "shortcut":
            if os.name != "nt":
                raise OSError("Запуск ярлыков поддерживается только в Windows")
            os.startfile(item["shortcut"])
        else:
            subprocess.Popen(item["command"], shell=False)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось запустить {item['label']}: {exc}")
    return {"ok": True, "message": f"Запускаю: {item['label']}."}

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(r'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS — Local AI</title><link rel="icon" type="image/png" href="/favicon.ico">
<style>
:root{color-scheme:dark;--panel:rgba(3,12,25,.86)}*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:#030814;color:#e9f8ff;font:16px "Segoe UI",Arial,sans-serif;background-image:linear-gradient(90deg,rgba(2,8,20,.91),rgba(2,8,20,.55)),url('/static/jarvis-bg.png');background-size:cover;background-position:center;background-attachment:fixed}
.wrap{max-width:1100px;margin:auto;padding:28px 18px}.top{display:flex;align-items:center;justify-content:space-between;gap:16px;border:1px solid #20bfff66;background:#061020cc;padding:14px 18px;border-radius:14px;backdrop-filter:blur(12px)}
.brand{font-size:clamp(24px,4vw,38px);font-weight:800;letter-spacing:5px;color:#7be3ff;text-shadow:0 0 20px #078dff}.sub{color:#a9dfff;font-size:12px;letter-spacing:3px}.status{color:#5fffd0;font-size:13px}
.layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,440px);gap:20px;margin-top:22px}.intro,.chat{border:1px solid #28bfff66;border-radius:18px;background:var(--panel);backdrop-filter:blur(12px);box-shadow:0 0 30px #0078ff12}
.intro{padding:28px;display:flex;flex-direction:column;justify-content:space-between;min-height:490px}.intro h1{font-size:clamp(28px,4vw,46px);margin:0 0 12px}.intro p{color:#b6dfff;line-height:1.7}
.pill{display:inline-block;border:1px solid #36cfff77;border-radius:30px;padding:8px 12px;color:#7ce8ff;font-size:13px;margin:5px 5px 0 0}
.chat{display:flex;flex-direction:column;min-height:490px;overflow:hidden}.chathead{padding:17px;border-bottom:1px solid #31bfff55;font-weight:700;color:#80e6ff}
.messages{padding:15px;display:flex;flex-direction:column;gap:12px;flex:1;max-height:360px;overflow:auto}.bubble{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5;padding:12px 14px;border-radius:12px;max-width:95%}.bot{background:#0a2440;border:1px solid #28aaff44;align-self:flex-start}.user{background:#075a83aa;border:1px solid #42d9ff66;align-self:flex-end}
.composer{display:flex;gap:8px;padding:12px;border-top:1px solid #31bfff55}.composer textarea{resize:vertical;min-height:48px;max-height:140px;flex:1;background:#020a17;color:white;border:1px solid #2b9fcf88;border-radius:10px;padding:12px;font:inherit;outline:none}
button{border:1px solid #39cfff66;border-radius:10px;padding:10px 13px;background:linear-gradient(135deg,#00a9d8,#1264ff);color:white;font-weight:700;cursor:pointer}.composer button{padding:0 18px}button:disabled{opacity:.55;cursor:wait}
.tools{padding:12px;border-top:1px solid #31bfff55;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.tools button{background:#0a2440}
#voiceSelect{max-width:100%;min-width:160px;background:#061020;color:white;border:1px solid #39cfff66;border-radius:10px;padding:8px}
#appStatus{color:#a9dfff;font-size:13px;line-height:1.5}.foot{text-align:center;color:#91b9d5;font-size:12px;margin-top:18px}
@media(max-width:800px){.layout{grid-template-columns:1fr}.intro{min-height:250px}.chat{min-height:470px}body{background-position:60% center}}
</style></head><body><div class="wrap">
<header class="top"><div><div class="brand">JARVIS</div><div class="sub">LOCAL AI ASSISTANT</div></div><div class="status">● ЛОКАЛЬНЫЙ РЕЖИМ<br><small>127.0.0.1:9014</small></div></header>
<main class="layout"><section class="intro"><div><h1>Система готова.</h1><p>Голосовой ввод, более низкий тон речи, ответы Groq AI и запуск выбранных приложений. Разреши браузеру доступ к микрофону.</p><span class="pill">Groq AI</span><span class="pill">Микрофон</span><span class="pill">Голосовые ответы</span><span class="pill">Windows</span></div><p><b>Приложения:</b> список собирается из ярлыков меню «Пуск» и рабочего стола. Для безопасности JARVIS запускает найденные ярлыки и заданные приложения, а не выполняет произвольные команды Windows.</p><div id="appStatus">Приложения: загружаю список…</div></section>
<section class="chat"><div class="chathead">◉ JARVIS / ГОЛОСОВОЙ ЧАТ</div><div id="messages" class="messages"><div class="bubble bot">Система онлайн. Напиши сообщение или нажми «Микрофон».</div></div>
<form id="form" class="composer"><textarea id="message" placeholder="Напиши сообщение JARVIS…" required maxlength="6000"></textarea><button id="send" type="submit">Отправить</button></form>
<div class="tools"><button type="button" id="mic">🎙 Микрофон</button><button type="button" id="speakToggle">🔊 Озвучивание: ВКЛ</button><button type="button" id="stopSpeak">■ Стоп</button><select id="voiceSelect" aria-label="Выбрать голос"><option>Загрузка голосов…</option></select></div>
<div class="tools" id="apps"></div></section></main><div class="foot">JARVIS Local AI · доступ через 127.0.0.1 · API-ключ хранится в .env</div></div>
<script>
const form=document.getElementById('form'),input=document.getElementById('message'),messages=document.getElementById('messages'),send=document.getElementById('send');
const mic=document.getElementById('mic'),speakToggle=document.getElementById('speakToggle'),stopSpeak=document.getElementById('stopSpeak'),voiceSelect=document.getElementById('voiceSelect');
let history=[],speakEnabled=true,recognition=null,voices=[];
function bubble(text,kind){const el=document.createElement('div');el.className='bubble '+kind;el.textContent=text;messages.appendChild(el);messages.scrollTop=messages.scrollHeight;return el;}
function loadVoices(){
 if(!('speechSynthesis' in window))return;
 const previous=voiceSelect.value;voices=speechSynthesis.getVoices();
 const ru=voices.filter(v=>v.lang.toLowerCase().startsWith('ru'));
 const hints=['pavel','dmitry','dmitriy','yuri','yuriy','mikhail','alex','david','mark','male','муж'];
 const preferred=ru.filter(v=>hints.some(h=>v.name.toLowerCase().includes(h)));
 const ordered=[...preferred,...ru.filter(v=>!preferred.includes(v)),...voices.filter(v=>!v.lang.toLowerCase().startsWith('ru'))];
 voiceSelect.replaceChildren();
 if(!ordered.length){const o=document.createElement('option');o.value='';o.textContent='Нет доступных голосов';voiceSelect.appendChild(o);return;}
 for(const v of ordered){const o=document.createElement('option');o.value=v.name;o.textContent=`${v.name} (${v.lang})`;voiceSelect.appendChild(o);}
 if(previous&&ordered.some(v=>v.name===previous))voiceSelect.value=previous;else if(preferred.length)voiceSelect.value=preferred[0].name;else if(ru.length)voiceSelect.value=ru[0].name;
}
if('speechSynthesis'in window){loadVoices();speechSynthesis.addEventListener('voiceschanged',loadVoices);}
function say(text){
 if(!speakEnabled||!('speechSynthesis'in window))return;
 speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang='ru-RU';u.rate=0.88;u.pitch=0.62;u.volume=1;
 const chosen=voices.find(v=>v.name===voiceSelect.value);if(chosen){u.voice=chosen;u.lang=chosen.lang;}speechSynthesis.speak(u);
}
async function sendMessage(text){
 const message=(text??input.value).trim();if(!message)return;
 bubble(message,'user');input.value='';send.disabled=true;mic.disabled=true;
 try{
  const ar=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:message})});
  const ad=await ar.json();if(!ar.ok)throw new Error(ad.detail||'Ошибка команды');
  if(ad.handled){bubble(ad.message,'bot');say(ad.message);return;}
  history.push({role:'user',content:message});const wait=bubble('Думаю…','bot');
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,history:history.slice(0,-1).slice(-12)})});
  const data=await r.json();if(!r.ok)throw new Error(data.detail||'Ошибка запроса');
  wait.textContent=data.reply;history.push({role:'assistant',content:data.reply});say(data.reply);
 }catch(err){bubble('Ошибка: '+err.message,'bot');}
 finally{send.disabled=false;mic.disabled=false;input.focus();}
}
form.addEventListener('submit',async e=>{e.preventDefault();await sendMessage(input.value);});
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();form.requestSubmit();}});
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){recognition=new SR();recognition.lang='ru-RU';recognition.interimResults=false;recognition.maxAlternatives=1;
 recognition.onstart=()=>{mic.textContent='🎙 Слушаю…';mic.disabled=true;};recognition.onend=()=>{mic.textContent='🎙 Микрофон';mic.disabled=false;};
 recognition.onerror=e=>bubble('Микрофон: '+e.error+'. Проверь разрешение браузера.','bot');
 recognition.onresult=e=>{const heard=e.results[0][0].transcript;input.value=heard;sendMessage(heard);};
 mic.addEventListener('click',()=>{try{recognition.start();}catch(e){bubble('Микрофон уже активен.','bot');}});
}else{mic.disabled=true;mic.textContent='Микрофон недоступен';mic.title='Открой сайт в актуальном Chrome или Edge';}
speakToggle.addEventListener('click',()=>{speakEnabled=!speakEnabled;speakToggle.textContent='🔊 Озвучивание: '+(speakEnabled?'ВКЛ':'ВЫКЛ');if(!speakEnabled&&'speechSynthesis'in window)speechSynthesis.cancel();});
stopSpeak.addEventListener('click',()=>{if('speechSynthesis'in window)speechSynthesis.cancel();});
async function loadApps(){try{const r=await fetch('/api/apps'),d=await r.json(),box=document.getElementById('apps');box.replaceChildren();
 for(const a of d.apps){const b=document.createElement('button');b.textContent='Открыть '+a.label;b.addEventListener('click',()=>launchApp(a.name));box.appendChild(b);}
 document.getElementById('appStatus').textContent='Разрешённые приложения: '+d.apps.map(a=>a.label).join(', ');
 }catch(e){document.getElementById('appStatus').textContent='Не удалось загрузить список приложений.';}}
async function launchApp(name){if(!confirm('Разрешить JARVIS открыть приложение?'))return;try{
 const r=await fetch('/api/apps/launch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({app_name:name})});
 const d=await r.json();if(!r.ok)throw new Error(d.detail||'Ошибка');bubble(d.message,'bot');say(d.message);
 }catch(e){bubble('Запуск не выполнен: '+e.message,'bot');}}
loadApps();
</script></body></html>''')


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    image = STATIC_DIR / "jarvis-bg.png"
    if image.is_file():
        return FileResponse(image, media_type="image/png")
    raise HTTPException(status_code=404, detail="Добавь static/jarvis-bg.png")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "JARVIS Local AI", "host": HOST, "port": PORT}


@app.get("/api/apps")
def list_apps():
    apps = get_all_apps()
    return {"apps": [{"name": name, "label": item["label"]} for name, item in apps.items()]}


@app.post("/api/apps/launch")
def launch_app(data: LaunchRequest):
    return launch_allowed_app(data.app_name.strip().lower())


@app.post("/api/action")
def action(data: ActionRequest):
    raw = data.command.strip()
    low = raw.lower().strip(" .!?")
    cleaned = re.sub(r"^(?:джарвис|jarvis)[, ]*", "", low).strip()
    cleaned = re.sub(r"^(?:пожалуйста)[, ]*", "", cleaned).strip()

    # Проверяем приложения ПЕРЕД командами открытия сайтов.
    app_command = re.sub(r"^(?:открой|запусти|включи)\s+", "", cleaned).strip()
    app_command = re.sub(r"^(?:приложение)\s+", "", app_command).strip()
    if app_command in APP_ALIASES:
        result = launch_allowed_app(APP_ALIASES[app_command])
        result["handled"] = True
        return result

    # Ищем установленное приложение по названию ярлыка из меню Пуск/рабочего стола.
    # Запускается только найденный ярлык; текст пользователя не исполняется как команда ОС.
    if re.match(r"^(?:открой|запусти|включи)\s+", cleaned):
        requested = app_command.removeprefix("приложение ").strip().casefold()
        installed = find_installed_apps()
        exact = [(app_id, item) for app_id, item in installed.items()
                 if item["label"].casefold() == requested]
        if len(exact) == 1:
            result = launch_allowed_app(exact[0][0])
            result["handled"] = True
            return result
        if len(exact) > 1:
            return {"handled": True, "message": f"Найдено несколько приложений «{requested}». Выбери нужное в списке."}
        partial = [(app_id, item) for app_id, item in installed.items()
                   if requested and requested in item["label"].casefold()]
        if len(partial) == 1:
            result = launch_allowed_app(partial[0][0])
            result["handled"] = True
            return result
        if len(partial) > 1:
            names = ", ".join(item["label"] for _, item in partial[:6])
            return {"handled": True, "message": f"Нашёл несколько похожих приложений: {names}. Уточни название."}

    if app_command in ("браузер", "интернет"):
        webbrowser.open("https://www.google.com")
        return {"handled": True, "message": "Открываю браузер."}

    # Прямое открытие ссылки на ролик/фильм, если пользователь вставил URL.
    # Для названия без ссылки открываем поиск именно видео на YouTube.
    match = re.match(r"^(?:включи|найди|покажи|открой)\s+(?:видео|ролик|видеоролик)\s+(.+)$", cleaned, re.I)
    if match:
        title = match.group(1).strip(" .!?\"'")
        candidate = title if re.match(r"^https?://", title, re.I) else "https://" + title
        parsed = urlparse(candidate)
        if parsed.hostname and ("youtube.com" in parsed.hostname.lower() or parsed.hostname.lower() == "youtu.be") and re.match(r"^https?://", title, re.I):
            url = title
            message = f"Открываю видеоролик по прямой ссылке: {title}"
        else:
            url = "https://www.youtube.com/results?search_query=" + quote_plus(title) + "&sp=EgIQAQ%253D%253D"
            message = f"Открываю видеоролики по запросу «{title}» на YouTube. Выбери ролик для воспроизведения."
        webbrowser.open(url)
        return {"handled": True, "message": message}

    match = re.match(r"^(?:включи|найди|покажи|открой)\s+(?:фильм|кино|мультфильм|сериал)\s+(.+)$", cleaned, re.I)
    if match:
        title = match.group(1).strip(" .!?\"'")
        candidate = title if re.match(r"^https?://", title, re.I) else "https://" + title
        parsed = urlparse(candidate)
        if re.match(r"^https?://", title, re.I) and parsed.hostname:
            url = title
            message = f"Открываю фильм по ссылке: {title}"
        else:
            url = "https://www.youtube.com/results?search_query=" + quote_plus(title + " фильм смотреть")
            message = f"Ищу фильм «{title}» на YouTube. Доступность полного фильма зависит от источника."
        webbrowser.open(url)
        return {"handled": True, "message": message}

    match = re.match(r"^(?:найди информацию о|найди|поищи|загугли|ищи в интернете|поиск)\s+(.+)$", cleaned, re.I)
    if match:
        query = match.group(1).strip()
        webbrowser.open("https://www.google.com/search?q=" + quote_plus(query))
        return {"handled": True, "message": f"Открываю поиск Google: {query}"}

    match = re.match(r"^(?:открой сайт|открой страницу|открой|зайди на|перейди на)\s+(.+)$", cleaned, re.I)
    if match:
        target = match.group(1).strip().strip(" .!?")
        target_low = target.lower()
        if target_low in SITES:
            url = SITES[target_low]
        else:
            # Поддерживаем полные URL, www-домены и домены с путём,
            # параметрами запроса и портом: example.com/page?x=1.
            candidate = target if re.match(r"^https?://", target, re.I) else "https://" + target
            parsed = urlparse(candidate)
            host = parsed.hostname or ""
            looks_like_url = (
                parsed.scheme in ("http", "https")
                and bool(host)
                and ("." in host or host.lower() == "localhost" or re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host))
                and not any(ch.isspace() for ch in target)
            )
            if looks_like_url:
                url = candidate
            else:
                # Если пользователь назвал сайт без точного адреса — ищем его в интернете.
                url = "https://www.google.com/search?q=" + quote_plus(target)
        webbrowser.open(url)
        return {"handled": True, "message": f"Открываю: {url}"}

    return {"handled": False, "message": ""}


@app.post("/api/chat")
async def chat(data: ChatRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY не задан в .env")
    messages = [{
        "role": "system",
        "content": (
            "Ты JARVIS — русскоязычный ИИ-помощник с лаконичным и спокойным стилем. "
            "Отвечай ясно, полезно и безопасно. Не утверждай, что выполнил действие на "
            "компьютере, если сервер не сообщил об успехе. Управление приложениями "
            "доступно только через разрешённый список."
        )
    }]
    for item in data.history[-12:]:
        role, content = item.get("role"), item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content[:6000]})
    messages.append({"role": "user", "content": data.message})
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 1200},
            )
        if response.status_code >= 400:
            detail = "Groq API вернул ошибку. Проверь ключ, модель и доступность API."
            try:
                detail = response.json().get("error", {}).get("message", detail)
            except (ValueError, AttributeError):
                pass
            raise HTTPException(status_code=502, detail=detail[:1000])
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        return {"reply": reply or "Модель вернула пустой ответ."}
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Groq не ответил вовремя. Попробуй ещё раз.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Не удалось подключиться к Groq API. Проверь интернет.")
    except (KeyError, IndexError, TypeError, ValueError):
        raise HTTPException(status_code=502, detail="Не удалось разобрать ответ Groq API.")


if __name__ == "__main__":
    import uvicorn
    print(f"JARVIS Local AI: http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
