import os
import re
import subprocess
import webbrowser
import time
from pathlib import Path
from contextlib import asynccontextmanager
from urllib.parse import quote_plus, urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_URL = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
GROQ_RESPONSES_URL = os.getenv("GROQ_RESPONSES_URL", "https://api.groq.com/openai/v1/responses").strip()
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
    global _camera
    try:
        if _camera is not None:
            _camera.release()
            _camera = None
    except Exception:
        pass
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
    """Ищет ярлыки Windows и доступные для безопасного запуска приложения из реестра."""
    import hashlib
    import shlex

    env = os.environ
    folders = [
        Path(env.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(env.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path.home() / "Desktop",
        Path.home() / "OneDrive/Desktop",
    ]
    found = {}
    skip_words = ("uninstall", "удалить программу", "деинсталляция", "readme", "help")

    def add_item(label, item):
        label = str(label or "").strip()
        if not label or any(word in label.casefold() for word in skip_words):
            return
        stable = str(item.get("shortcut") or item.get("executable") or label).casefold()
        app_id = "app_" + hashlib.sha256(stable.encode("utf-8", errors="ignore")).hexdigest()[:20]
        found[app_id] = {"label": label, **item}

    for folder in folders:
        if not folder.is_dir():
            continue
        try:
            for shortcut in folder.rglob("*"):
                if shortcut.suffix.lower() not in (".lnk", ".url") or not shortcut.is_file():
                    continue
                add_item(shortcut.stem, {"shortcut": str(shortcut), "kind": "shortcut"})
        except OSError:
            continue

    # Реестр позволяет найти приложения, у которых нет ярлыка в меню «Пуск».
    if os.name == "nt":
        try:
            import winreg
            registry_roots = (
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            )
            for root, key_path in registry_roots:
                try:
                    parent = winreg.OpenKey(root, key_path)
                except OSError:
                    continue
                with parent:
                    try:
                        count = winreg.QueryInfoKey(parent)[0]
                    except OSError:
                        count = 0
                    for index in range(count):
                        try:
                            sub_name = winreg.EnumKey(parent, index)
                            with winreg.OpenKey(parent, sub_name) as sub:
                                label = winreg.QueryValueEx(sub, "DisplayName")[0]
                                try:
                                    icon = str(winreg.QueryValueEx(sub, "DisplayIcon")[0]).strip()
                                except OSError:
                                    icon = ""
                                try:
                                    install_location = str(winreg.QueryValueEx(sub, "InstallLocation")[0]).strip()
                                except OSError:
                                    install_location = ""
                            # DisplayIcon может иметь вид "C:\\App\\app.exe",0.
                            icon_match = re.match(r'^\s*"?(.+?\.exe)"?(?:\s*,\s*-?\d+)?\s*$', icon, re.I)
                            exe = Path(icon_match.group(1).strip(' "')) if icon_match else None
                            if exe and exe.is_file():
                                add_item(label, {"executable": str(exe), "kind": "executable"})
                            elif install_location:
                                # Не сканируем весь диск: проверяем только несколько типичных имён запуска.
                                root_dir = Path(install_location.strip(' "'))
                                if root_dir.is_dir():
                                    candidates = [root_dir / f"{str(label).split()[0]}.exe"]
                                    candidates.extend(root_dir / name for name in ("launcher.exe", "start.exe", "app.exe"))
                                    valid = next((candidate for candidate in candidates if candidate.is_file()), None)
                                    if valid:
                                        add_item(label, {"executable": str(valid), "kind": "executable"})
                        except (OSError, ValueError, TypeError):
                            continue
        except ImportError:
            pass
    return found

_apps_cache = {"at": 0.0, "items": {}}
_apps_cache_lock = __import__("threading").Lock()


def get_all_apps(force_refresh: bool = False):
    """Кэширует обнаруженные приложения, чтобы поиск при каждом символе был быстрым."""
    now = time.monotonic()
    with _apps_cache_lock:
        if not force_refresh and _apps_cache["items"] and now - _apps_cache["at"] < 15:
            return dict(_apps_cache["items"])
        result = {key: dict(value, kind="command") for key, value in ALLOWED_APPS.items()}
        result.update(find_installed_apps())
        _apps_cache["at"] = now
        _apps_cache["items"] = result
        return dict(result)


def launch_allowed_app(app_name: str):
    item = get_all_apps().get(app_name)
    if item is None:
        raise HTTPException(status_code=404, detail="Приложение не найдено. Обнови список приложений.")
    try:
        if item.get("kind") == "shortcut":
            if os.name != "nt":
                raise OSError("Запуск ярлыков поддерживается только в Windows")
            os.startfile(item["shortcut"])
        elif item.get("kind") == "executable":
            executable = Path(item["executable"]).resolve()
            if not executable.is_file() or executable.suffix.lower() != ".exe":
                raise OSError("Исполняемый файл не найден или имеет неподдерживаемый формат")
            subprocess.Popen([str(executable)], shell=False, cwd=str(executable.parent))
        else:
            subprocess.Popen(item["command"], shell=False)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось запустить {item['label']}: {exc}")
    return {"ok": True, "message": f"Запускаю: {item['label']}."}

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(r"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS AI</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#030814;color:#e9f8ff;font:16px Segoe UI,Arial;background-image:linear-gradient(rgba(0,5,20,.38),rgba(0,5,20,.62)),url("/static/jarvis_wallpaper.png");background-size:cover;background-position:center center;background-repeat:no-repeat;background-attachment:fixed;min-height:100vh}
.wrap{max-width:1050px;margin:auto;padding:22px}.top,.panel{border:1px solid #26bfff66;background:rgba(3,14,32,.86);border-radius:16px;padding:18px;box-shadow:0 0 28px #0078ff16}.top{display:flex;justify-content:space-between;align-items:center;gap:12px}.brand{font-size:32px;font-weight:900;letter-spacing:6px;color:#7be3ff;text-shadow:0 0 20px #078dff}.muted{color:#9fc9e8;font-size:13px}.modes{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}.modes button{flex:1;min-width:200px}.layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,360px);gap:16px}.panel{min-height:420px}.messages{height:330px;overflow:auto;display:flex;flex-direction:column;gap:10px;margin:12px 0}.bubble{padding:11px 13px;border-radius:12px;white-space:pre-wrap;overflow-wrap:anywhere;max-width:95%}.bot{background:#0a2440;border:1px solid #28aaff44;align-self:flex-start}.user{background:#075a83aa;align-self:flex-end}.composer{display:flex;gap:8px}.composer textarea,input{min-width:0;flex:1;background:#020a17;color:white;border:1px solid #2b9fcf88;border-radius:10px;padding:12px;font:inherit}button{border:1px solid #39cfff66;border-radius:10px;padding:11px 14px;background:linear-gradient(135deg,#00a9d8,#1264ff);color:white;font-weight:700;cursor:pointer}button.secondary{background:#0a2440}.tools{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}select{background:#061020;color:white;border:1px solid #39cfff66;border-radius:10px;padding:9px;max-width:100%}.results{display:flex;flex-direction:column;gap:7px;margin-top:10px;max-height:220px;overflow:auto}.result{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px;border:1px solid #2b9fcf55;border-radius:10px}.result span{overflow-wrap:anywhere}.result button{padding:7px 10px}.mediaResults{display:flex;flex-direction:column;gap:9px;margin-top:12px;max-height:360px;overflow:auto}.mediaCard{border:1px solid #2b9fcf66;border-radius:11px;padding:11px;background:#041327}.mediaCard a{color:#7be3ff;font-weight:700;text-decoration:none;overflow-wrap:anywhere}.mediaCard a:hover{text-decoration:underline}.mediaCard p{color:#a9cbe3;font-size:13px;line-height:1.45;margin:7px 0 0}.mediaSource{font-size:11px;color:#6fa9d2;margin-top:6px}.camera{width:100%;border-radius:12px;background:#020711;margin-top:12px;min-height:180px;object-fit:contain}.hidden{display:none!important}#voiceState{color:#5fffd0;margin-top:10px}@media(max-width:780px){.layout{grid-template-columns:1fr}.top{align-items:flex-start}.panel{min-height:auto}.messages{height:300px}}
</style></head><body><div class="wrap">
<header class="top"><div><div class="brand">JARVIS</div><div class="muted">AI ASSISTANT · WINDOWS</div></div><div class="muted">Локальный интерфейс<br>127.0.0.1:9014</div></header>
<div class="modes"><button id="chatMode">💬 Режим чата</button><button id="voiceMode">🎙 Голосовой ассистент</button></div>
<main class="layout"><section class="panel" id="chatPanel"><b id="modeTitle">Чат JARVIS</b><div class="messages" id="messages"><div class="bubble bot">Система готова. Выбери режим и напиши сообщение.</div></div>
<form id="form" class="composer"><textarea id="message" placeholder="Напиши команду или вопрос…" required maxlength="6000"></textarea><button id="send">➤</button></form>
<div class="tools"><button class="secondary" id="mic">🎙 Слушать</button><button class="secondary" id="stopListen">■ Остановить речь</button><button class="secondary" id="speakToggle">🔊 Голос: ВКЛ</button></div>
<div class="tools"><label class="muted">Голос</label><select id="voiceSelect"></select><label class="muted">Скорость</label><input id="rate" type="range" min=".7" max="1.3" step=".05" value=".9" style="flex:0;min-width:100px"><label class="muted">Тон</label><input id="pitch" type="range" min=".5" max="1.5" step=".1" value=".8" style="flex:0;min-width:100px"></div><div id="voiceState" class="muted">Выбери голосовой режим, чтобы начать.</div></section>
<aside class="panel"><b>Поиск приложений</b><p class="muted">Вводи название — JARVIS ищет ярлыки Windows автоматически.</p><div class="tools"><input id="appSearch" placeholder="Например: Chrome, Discord, Steam…"><button id="refreshApps" class="secondary" type="button">Обновить</button></div><div id="appResults" class="results"></div><div id="appStatus" class="muted"></div>
<hr style="border-color:#2b9fcf44;margin:18px 0"><b>Поиск фильмов и видео</b><p class="muted">Ищи название и открывай найденные ссылки. Для фильмов покажем также каталоги легальных сервисов.</p><div class="tools"><input id="mediaSearch" placeholder="Название фильма или ролика…"><select id="mediaKind" aria-label="Тип поиска"><option value="video">Видео</option><option value="movie">Фильм / сериал</option></select></div><div class="tools"><button id="mediaSearchButton" type="button">🔎 Найти</button></div><div id="mediaStatus" class="muted"></div><div id="mediaResults" class="mediaResults"></div>
<hr style="border-color:#2b9fcf44;margin:18px 0"><b>Умная камера</b><p class="muted">Обнаружение людей доступно, если установлен OpenCV и YOLO.</p><div class="tools"><button id="cameraStart">📷 Включить</button><button id="cameraStop" class="secondary">Остановить</button></div><img id="camera" class="camera hidden" alt="Поток с камеры"><div id="cameraStatus" class="muted">Камера выключена.</div></aside></main>
<p class="muted" style="text-align:center;margin-top:16px">Голосовой режим использует микрофон браузера. Доступ к камере запрашивается только по нажатию кнопки.</p></div>
<script>
const $=id=>document.getElementById(id),messages=$('messages'),input=$('message');let history=[],voices=[],recognition=null,speakEnabled=true,mode='chat',listening=false,appTimer=null;
function bubble(t,k='bot'){const e=document.createElement('div');e.className='bubble '+k;e.textContent=t;messages.appendChild(e);messages.scrollTop=messages.scrollHeight;return e}
function loadVoices(){if(!('speechSynthesis'in window))return;let old=$('voiceSelect').value;voices=speechSynthesis.getVoices();let ru=voices.filter(v=>v.lang.toLowerCase().startsWith('ru'));let sorted=[...ru,...voices.filter(v=>!ru.includes(v))];$('voiceSelect').replaceChildren();sorted.forEach(v=>{let o=document.createElement('option');o.value=v.name;o.textContent=v.name+' ('+v.lang+')';$('voiceSelect').appendChild(o)});if(old)$('voiceSelect').value=old}
if('speechSynthesis'in window){loadVoices();speechSynthesis.addEventListener('voiceschanged',loadVoices)}
function say(t){if(!speakEnabled||!('speechSynthesis'in window))return;speechSynthesis.cancel();let u=new SpeechSynthesisUtterance(t),v=voices.find(x=>x.name===$('voiceSelect').value);u.lang='ru-RU';u.rate=+$('rate').value;u.pitch=+$('pitch').value;if(v){u.voice=v;u.lang=v.lang}speechSynthesis.speak(u)}
async function sendMessage(text){let m=(text??input.value).trim();if(!m)return;bubble(m,'user');input.value='';$('send').disabled=true;try{let ar=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:m})});let ad=await ar.json();if(!ar.ok)throw Error(ad.detail||'Ошибка команды');if(ad.handled){bubble(ad.message);say(ad.message);return}history.push({role:'user',content:m});let wait=bubble('Думаю…');let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m,history:history.slice(0,-1).slice(-12)})});let d=await r.json();if(!r.ok)throw Error(d.detail||'Ошибка запроса');wait.textContent=d.reply;history.push({role:'assistant',content:d.reply});say(d.reply)}catch(e){bubble('Ошибка: '+e.message)}finally{$('send').disabled=false;input.focus()}}
$('form').addEventListener('submit',e=>{e.preventDefault();sendMessage(input.value)});input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('form').requestSubmit()}});
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(SR){recognition=new SR();recognition.lang='ru-RU';recognition.interimResults=false;recognition.continuous=false;recognition.onstart=()=>{$('voiceState').textContent='Слушаю…';listening=true;$('mic').textContent='🎙 Слушаю…'};recognition.onend=()=>{listening=false;$('mic').textContent='🎙 Слушать';if(mode==='voice')$('voiceState').textContent='Готов. Нажми «Слушать» для следующей команды.'};recognition.onerror=e=>{$('voiceState').textContent='Микрофон: '+e.error};recognition.onresult=e=>sendMessage(e.results[0][0].transcript)}else{$('mic').disabled=true;$('voiceState').textContent='Распознавание речи недоступно. Открой в Chrome или Edge.'}
function setMode(m){mode=m;$('modeTitle').textContent=m==='chat'?'Чат JARVIS':'Голосовой ассистент';$('chatMode').style.opacity=m==='chat'?'1':'.65';$('voiceMode').style.opacity=m==='voice'?'1':'.65';if(m==='voice'){$('voiceState').textContent='Голосовой режим активен. Разреши микрофон кнопкой «Слушать».';say('Голосовой режим активирован. Я готов слушать команды.')}else $('voiceState').textContent='Режим чата активен.'}
$('chatMode').onclick=()=>setMode('chat');$('voiceMode').onclick=()=>setMode('voice');$('mic').onclick=()=>{if(!recognition)return;try{recognition.start()}catch(e){$('voiceState').textContent='Распознавание уже запущено.'}};$('stopListen').onclick=()=>{if(recognition)recognition.stop();if('speechSynthesis'in window)speechSynthesis.cancel()};$('speakToggle').onclick=()=>{speakEnabled=!speakEnabled;$('speakToggle').textContent='🔊 Голос: '+(speakEnabled?'ВКЛ':'ВЫКЛ');if(!speakEnabled)speechSynthesis.cancel()};
async function searchApps(){let q=$('appSearch').value.trim();if(!q){$('appResults').replaceChildren();$('appStatus').textContent='';return}try{let r=await fetch('/api/apps/search?q='+encodeURIComponent(q));let d=await r.json();$('appResults').replaceChildren();d.apps.forEach(a=>{let row=document.createElement('div');row.className='result';let label=document.createElement('span');label.textContent=a.label;let b=document.createElement('button');b.textContent='Открыть';b.onclick=()=>launchApp(a.name);row.append(label,b);$('appResults').appendChild(row)});$('appStatus').textContent=d.apps.length?'Найдено: '+d.apps.length:'Ничего не найдено'}catch(e){$('appStatus').textContent='Ошибка поиска'}}
$('appSearch').addEventListener('input',()=>{clearTimeout(appTimer);appTimer=setTimeout(searchApps,180)});
async function launchApp(name){if(!confirm('Разрешить JARVIS открыть выбранное приложение?'))return;try{let r=await fetch('/api/apps/launch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({app_name:name})}),d=await r.json();if(!r.ok)throw Error(d.detail||'Ошибка');bubble(d.message);say(d.message)}catch(e){bubble('Не удалось запустить: '+e.message)}}
$('refreshApps').onclick=async()=>{const b=$('refreshApps');b.disabled=true;b.textContent='Ищу…';try{const r=await fetch('/api/apps/refresh',{method:'POST'}),d=await r.json();if(!r.ok)throw Error(d.detail||'Ошибка обновления');$('appStatus').textContent=d.message;await searchApps()}catch(e){$('appStatus').textContent='Не удалось обновить список: '+e.message}finally{b.disabled=false;b.textContent='Обновить'}};
let mediaTimer=null;
function renderMediaResults(items){const box=$('mediaResults');box.replaceChildren();items.forEach(item=>{const card=document.createElement('div');card.className='mediaCard';const a=document.createElement('a');a.href=item.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=item.title||item.source||item.url;const source=document.createElement('div');source.className='mediaSource';source.textContent=item.source||'';card.append(a,source);if(item.snippet){const p=document.createElement('p');p.textContent=item.snippet;card.appendChild(p)}box.appendChild(card)})}
async function searchMedia(){const q=$('mediaSearch').value.trim();if(!q){$('mediaStatus').textContent='Введи название фильма или видео.';$('mediaResults').replaceChildren();return}const button=$('mediaSearchButton');button.disabled=true;button.textContent='Ищу…';$('mediaStatus').textContent='Ищу ссылки в интернете…';$('mediaResults').replaceChildren();try{const params=new URLSearchParams({q,kind:$('mediaKind').value});const r=await fetch('/api/media/search?'+params.toString());const d=await r.json();if(!r.ok)throw Error(d.detail||'Ошибка поиска');renderMediaResults(d.results||[]);$('mediaStatus').textContent=d.results&&d.results.length?('Найдено ссылок: '+d.results.length+(d.live_results?' · результаты поиска':' · прямые ссылки на поисковые каталоги')):'Ссылок не найдено. Попробуй другое название.'}catch(e){$('mediaStatus').textContent='Ошибка поиска: '+e.message}finally{button.disabled=false;button.textContent='🔎 Найти'}}
$('mediaSearchButton').addEventListener('click',searchMedia);$('mediaSearch').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();searchMedia()}});$('mediaKind').addEventListener('change',()=>{if($('mediaSearch').value.trim())searchMedia()});
let cameraPoll=null;
async function updateCameraStatus(){try{let r=await fetch('/api/camera/status'),d=await r.json();if(!d.active)return;let objects=Object.entries(d.objects||{}).map(([k,v])=>k+': '+v).join(', ');$('cameraStatus').textContent=d.vision_available?(objects?('Людей: '+d.people+' · Объекты: '+objects):'Vision AI активен: объекты пока не обнаружены'):'Видео работает, но Vision AI не установлен. Выполни pip install ultralytics';if(d.vision_error)$('cameraStatus').textContent+=' · Ошибка модели: '+d.vision_error}catch(e){}}
$('cameraStart').onclick=async()=>{try{let r=await fetch('/api/camera/start',{method:'POST'}),d=await r.json();if(!r.ok)throw Error(d.detail||'Камера недоступна');$('camera').src='/api/camera/stream?ts='+Date.now();$('camera').classList.remove('hidden');$('cameraStatus').textContent=d.message;clearInterval(cameraPoll);cameraPoll=setInterval(updateCameraStatus,1500)}catch(e){$('cameraStatus').textContent=e.message}};
$('cameraStop').onclick=async()=>{clearInterval(cameraPoll);try{await fetch('/api/camera/stop',{method:'POST'})}catch(e){}$('camera').src='';$('camera').classList.add('hidden');$('cameraStatus').textContent='Камера выключена.'};
</script></body></html>""")

@app.get("/api/apps/search")
def search_apps(q: str = ""):
    """Поиск по названию, словам и похожему написанию (например, 'chrom' -> Chrome)."""
    from difflib import SequenceMatcher
    query = re.sub(r"\s+", " ", q.strip().casefold())
    if not query:
        return {"apps": []}

    aliases = {
        "хром": "chrome", "гугл хром": "chrome", "браузер": "chrome",
        "стим": "steam", "дискорд": "discord", "телега": "telegram",
        "телеграм": "telegram", "ворд": "word", "эксель": "excel",
        "пейнт": "paint", "паинт": "paint", "блокнот": "notepad",
        "калькулятор": "calculator", "проводник": "explorer",
    }
    normalized = aliases.get(query, query)
    apps = get_all_apps()
    scored = []
    for name, item in apps.items():
        label = item["label"].casefold()
        label_flat = re.sub(r"[^a-zа-я0-9]+", " ", label)
        name_flat = re.sub(r"[^a-zа-я0-9]+", " ", name.casefold())
        score = 0.0
        if normalized == label or normalized == name_flat:
            score = 1.0
        elif label.startswith(normalized) or name_flat.startswith(normalized):
            score = 0.92
        elif normalized in label or normalized in name_flat:
            score = 0.82
        else:
            query_words = normalized.split()
            label_words = label_flat.split()
            if query_words and all(any(word in candidate for candidate in label_words) for word in query_words):
                score = 0.75
            else:
                score = max(SequenceMatcher(None, normalized, label_flat).ratio(),
                            SequenceMatcher(None, normalized, name_flat).ratio())
        if score >= 0.62:
            scored.append((score, name, item))
    scored.sort(key=lambda row: (-row[0], row[2]["label"].casefold()))
    return {"apps": [{"name": name, "label": item["label"], "match": round(score, 2)}
                      for score, name, item in scored[:12]]}


@app.get("/api/apps")
def list_apps():
    apps = get_all_apps()
    return {"apps": [{"name": name, "label": item["label"]} for name, item in apps.items()]}


@app.post("/api/apps/refresh")
def refresh_apps():
    """Принудительно пересканировать ярлыки и реестр Windows."""
    apps = get_all_apps(force_refresh=True)
    return {"ok": True, "count": len(apps), "message": f"Поиск обновлён. Найдено приложений: {len(apps)}"}


@app.post("/api/apps/launch")
def launch_app(data: LaunchRequest):
    return launch_allowed_app(data.app_name.strip().lower())


class MediaResultParser(__import__("html.parser", fromlist=["HTMLParser"]).HTMLParser):
    """Минимальный парсер результатов HTML-поиска без дополнительных библиотек."""
    def __init__(self):
        super().__init__()
        self.results = []
        self._current = None
        self._in_title = False
        self._in_snippet = False
        self._snippet_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "a" and "result__a" in classes:
            self._current = {"url": attrs.get("href", ""), "title": "", "snippet": "", "source": "Веб-поиск"}
            self._in_title = True
        elif self._current is not None and tag in ("a", "div", "span") and "result__snippet" in classes:
            self._in_snippet = True
            self._snippet_depth = 1
        elif self._in_snippet and tag in ("div", "span"):
            self._snippet_depth += 1

    def handle_data(self, data):
        if self._current is None:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._in_title:
            self._current["title"] += (" " if self._current["title"] else "") + text
        elif self._in_snippet:
            self._current["snippet"] += (" " if self._current["snippet"] else "") + text

    def handle_endtag(self, tag):
        if self._current is None:
            return
        if tag == "a" and self._in_title:
            self._in_title = False
            if self._current.get("url") and self._current.get("title"):
                self.results.append(self._current)
                self._current = None
        elif self._in_snippet and tag in ("div", "span"):
            self._snippet_depth -= 1
            if self._snippet_depth <= 0:
                self._in_snippet = False


def _media_fallback_links(query: str, kind: str):
    encoded = quote_plus(query)
    if kind == "movie":
        return [
            {"title": f"Искать «{query}» в Google", "url": f"https://www.google.com/search?q={encoded}+фильм+сериал", "source": "Google"},
            {"title": f"Искать «{query}» на Кинопоиске", "url": f"https://www.kinopoisk.ru/index.php?kp_query={encoded}", "source": "Кинопоиск"},
            {"title": f"Проверить доступность «{query}» на JustWatch", "url": f"https://www.justwatch.com/ru/search?q={encoded}", "source": "JustWatch · поиск доступности на стримингах"},
            {"title": f"Искать «{query}» на IMDb", "url": f"https://www.imdb.com/find/?q={encoded}", "source": "IMDb"},
            {"title": f"Видео по запросу «{query}» на YouTube", "url": f"https://www.youtube.com/results?search_query={encoded}+фильм", "source": "YouTube"},
        ]
    return [
        {"title": f"Видео «{query}» на YouTube", "url": f"https://www.youtube.com/results?search_query={encoded}", "source": "YouTube"},
        {"title": f"Видео «{query}» на Google Видео", "url": f"https://www.google.com/search?tbm=vid&q={encoded}", "source": "Google Видео"},
        {"title": f"Видео «{query}» на Rutube", "url": f"https://rutube.ru/search/?query={encoded}", "source": "Rutube"},
        {"title": f"Видео «{query}» на Vimeo", "url": f"https://vimeo.com/search?q={encoded}", "source": "Vimeo"},
    ]


@app.get("/api/media/search")
async def search_media(q: str = "", kind: str = "video"):
    """Возвращает найденные веб-ссылки; если поисковик недоступен — ссылки на каталоги."""
    query = re.sub(r"\s+", " ", q).strip()[:180]
    if not query:
        raise HTTPException(status_code=400, detail="Введи название для поиска.")
    if kind not in ("video", "movie"):
        kind = "video"
    search_terms = query if kind == "video" else f"{query} фильм сериал смотреть легально"
    search_url = "https://html.duckduckgo.com/html/?q=" + quote_plus(search_terms)
    results = []
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
        }) as client:
            response = await client.get(search_url)
            response.raise_for_status()
        parser = MediaResultParser()
        parser.feed(response.text)
        for item in parser.results:
            url = item.get("url", "").strip()
            if not url.startswith(("https://", "http://")):
                continue
            host = (urlparse(url).hostname or "").lower()
            if not host or "duckduckgo.com" in host:
                continue
            title = re.sub(r"\s+", " ", item.get("title", "")).strip()
            snippet = re.sub(r"\s+", " ", item.get("snippet", "")).strip()
            if not title:
                continue
            results.append({"title": title[:220], "url": url, "snippet": snippet[:400], "source": host})
            if len(results) >= 8:
                break
    except (httpx.HTTPError, ValueError, TypeError):
        results = []
    live_results = bool(results)
    if kind == "movie":
        results.extend(_media_fallback_links(query, kind))
    elif not results:
        results = _media_fallback_links(query, kind)
    # Удаляем дубликаты URL и ограничиваем число ссылок в интерфейсе.
    unique = []
    seen = set()
    for item in results:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return {"query": query, "kind": kind, "live_results": live_results, "results": unique[:12]}


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

    # Умный поиск приложения по команде использует тот же рейтинг совпадений, что и панель.
    if re.match(r"^(?:открой|запусти|включи)\s+", cleaned):
        requested = app_command.removeprefix("приложение ").strip().casefold()
        if requested:
            matches = search_apps(requested).get("apps", [])
            if matches:
                top = matches[0]
                second_score = matches[1]["match"] if len(matches) > 1 else 0.0
                # Не угадываем при неоднозначности: показываем варианты вместо запуска не той программы.
                if top["match"] >= 0.80 and (len(matches) == 1 or top["match"] - second_score >= 0.12):
                    result = launch_allowed_app(top["name"])
                    result["handled"] = True
                    return result
                if top["match"] >= 0.62:
                    names = ", ".join(item["label"] for item in matches[:5])
                    return {"handled": True, "message": f"Нашёл похожие приложения: {names}. Уточни название."}

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


    # Поиск через Яндекс: текстовые и голосовые команды
    yandex_match = re.match(
        r"^(?:(?:найди|поищи|ищи|открой|покажи)\s+"
        r"(?:в\s+)?яндексе\s+(.+)|"
        r"(?:открой\s+яндекс\s+и\s+)?"
        r"(?:найди|поищи|ищи|поиск)\s+(.+?)\s+в\s+яндексе)$",
        cleaned,
        re.I
    )

    if yandex_match:
        query = next(
            (group.strip() for group in yandex_match.groups() if group),
            ""
        ).strip(" .!?\"'")

        if query:
            url = "https://yandex.ru/search/?text=" + quote_plus(query)
            webbrowser.open(url)
            return {
                "handled": True,
                "message": f"Ищу в Яндексе: {query}"
            }

    # Поиск изображений через Яндекс
    match = re.match(
        r"^(?:найди|поищи|покажи)\s+"
        r"(?:в\s+)?(?:яндексе\s+)?"
        r"(?:картинки|изображения|фото)\s+(.+)$",
        cleaned,
        re.I
    )
    if match:
        query = match.group(1).strip(" .!?\"'")
        url = "https://yandex.ru/images/search?text=" + quote_plus(query)
        webbrowser.open(url)
        return {
            "handled": True,
            "message": f"Ищу изображения в Яндексе: {query}"
        }

    # Поиск видео через Яндекс
    match = re.match(
        r"^(?:найди|поищи|покажи)\s+"
        r"(?:в\s+)?(?:яндексе\s+)?"
        r"(?:видео|ролики)\s+(.+)$",
        cleaned,
        re.I
    )
    if match:
        query = match.group(1).strip(" .!?\"'")
        url = "https://yandex.ru/video/search?text=" + quote_plus(query)
        webbrowser.open(url)
        return {
            "handled": True,
            "message": f"Ищу видео в Яндексе: {query}"
        }

    # Обычный поиск по умолчанию тоже через Яндекс
    match = re.match(
        r"^(?:найди информацию о|найди|поищи|загугли|"
        r"ищи в интернете|поиск)\s+(.+)$",
        cleaned,
        re.I
    )
    if match:
        query = match.group(1).strip()
        url = "https://yandex.ru/search/?text=" + quote_plus(query)
        webbrowser.open(url)
        return {
            "handled": True,
            "message": f"Открываю поиск Яндекса: {query}"
        }

    return {"handled": False, "message": ""}



@app.post("/api/chat")
async def chat(data: ChatRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY не задан в .env")

    # Режим интернет-поиска включается префиксом «Умный поиск:».
    smart_search = bool(re.match(r"^\s*умный\s+поиск\b", data.message, re.I))
    user_message = re.sub(
        r"^\s*умный\s+поиск\s*[:：,\-—]?\s*", "", data.message,
        count=1, flags=re.I
    ).strip() if smart_search else data.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Напиши, что нужно найти в интернете.")

    system_prompt = (
        "Ты JARVIS — умный ИИ-помощник. Отвечай на языке пользователя, "
        "обычно на русском. Объясняй ясно, структурированно и без лишней воды. "
        "Не утверждай, что выполнил действие на компьютере, если сервер не сообщил "
        "об успехе. Управление приложениями доступно только через разрешённый список. "
        "Если включён интернет-поиск, опирайся на найденные источники, различай факты "
        "и предположения и не выдумывай ссылки."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for item in data.history[-12:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content[:6000]})
    messages.append({"role": "user", "content": user_message})

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            if smart_search:
                # Отдельный endpoint Responses API с инструментом веб-поиска.
                response = await client.post(
                    GROQ_RESPONSES_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "input": messages,
                        "tools": [{"type": "browser_search"}],
                        "tool_choice": "auto",
                        "max_output_tokens": 1600,
                    },
                )
            else:
                # Обычный чат оставлен на прежнем Chat Completions API.
                response = await client.post(
                    GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1200,
                    },
                )

        if response.status_code >= 400:
            detail = "Ошибка Groq API. Проверь ключ, модель и настройки поиска."
            try:
                error_data = response.json()
                detail = error_data.get("error", {}).get("message", detail)
            except (ValueError, AttributeError):
                pass
            raise HTTPException(status_code=502, detail=detail[:1000])

        result = response.json()
        if smart_search:
            reply = result.get("output_text", "")
            if not reply:
                parts = []
                for item in result.get("output", []):
                    if item.get("type") != "message":
                        continue
                    for part in item.get("content", []):
                        if part.get("type") in ("output_text", "text"):
                            text_part = part.get("text", "")
                            if text_part:
                                parts.append(text_part)
                reply = "\n".join(parts)
        else:
            reply = result["choices"][0]["message"]["content"]

        return {"reply": reply or "Не удалось получить текст ответа. Попробуй ещё раз."}

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Groq не ответил вовремя. Попробуй ещё раз.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Не удалось подключиться к Groq API. Проверь интернет.")
    except (KeyError, IndexError, TypeError, ValueError):
        raise HTTPException(status_code=502, detail="Не удалось разобрать ответ Groq API.")


# Необязательная умная камера. Установка: pip install opencv-python ultralytics
try:
    import cv2
except ImportError:
    cv2 = None
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

_camera = None
_camera_model = None
_camera_lock = __import__("threading").Lock()
_camera_stats = {"people": 0, "objects": {}, "total": 0, "vision_error": ""}

def _camera_frame():
    global _camera_model, _camera_stats
    if cv2 is None:
        raise RuntimeError("OpenCV не установлен. Выполни: pip install opencv-python")
    if _camera is None or not _camera.isOpened():
        raise RuntimeError("Камера не запущена.")
    ok, frame = _camera.read()
    if not ok:
        raise RuntimeError("Не удалось получить кадр с камеры.")
    if YOLO is not None:
        try:
            if _camera_model is None:
                _camera_model = YOLO("yolov8n.pt")
            result = _camera_model.predict(frame, verbose=False, conf=0.45)[0]
            names = result.names
            counts = {}
            people = 0
            for box in result.boxes:
                class_id = int(box.cls[0])
                label = str(names.get(class_id, class_id)) if isinstance(names, dict) else str(names[class_id])
                counts[label] = counts.get(label, 0) + 1
                if class_id == 0:
                    people += 1
            _camera_stats.update({"people": people, "objects": counts, "total": sum(counts.values()), "vision_error": ""})
            frame = result.plot()
            summary = ", ".join(f"{label}: {count}" for label, count in sorted(counts.items())[:5]) or "Объекты не обнаружены"
            cv2.putText(frame, f"PEOPLE: {people} | OBJECTS: {sum(counts.values())}", (18, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, summary[:90], (18, 62), cv2.FONT_HERSHEY_SIMPLEX,
                        0.48, (0, 230, 255), 1, cv2.LINE_AA)
        except Exception as exc:
            _camera_stats["vision_error"] = str(exc)[:180]
    return cv2.imencode(".jpg", frame)[1].tobytes()

@app.post("/api/camera/start")
def camera_start():
    global _camera
    if cv2 is None:
        raise HTTPException(status_code=503, detail="OpenCV не установлен. Выполни: pip install opencv-python")
    with _camera_lock:
        if _camera is None or not _camera.isOpened():
            _camera = cv2.VideoCapture(0, cv2.CAP_DSHOW if os.name == "nt" else 0)
        if not _camera.isOpened():
            _camera.release()
            _camera = None
            raise HTTPException(status_code=503, detail="Камера не найдена или занята другим приложением.")
    if YOLO is None:
        return {"ok": True, "message": "Камера включена. Для распознавания людей установи ultralytics: pip install ultralytics"}
    return {"ok": True, "message": "Камера и распознавание объектов включены."}

@app.post("/api/camera/stop")
def camera_stop():
    global _camera
    with _camera_lock:
        if _camera is not None:
            _camera.release()
            _camera = None
        _camera_stats.update({"people": 0, "objects": {}, "total": 0, "vision_error": ""})
    return {"ok": True, "message": "Камера выключена."}

def _camera_stream():
    while True:
        with _camera_lock:
            if _camera is None or not _camera.isOpened():
                break
            try:
                frame = _camera_frame()
            except RuntimeError:
                break
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

@app.get("/api/camera/status")
def camera_status():
    active = bool(cv2 is not None and _camera is not None and _camera.isOpened())
    return {
        "active": active,
        "vision_available": YOLO is not None,
        "people": _camera_stats["people"],
        "total_objects": _camera_stats["total"],
        "objects": _camera_stats["objects"],
        "vision_error": _camera_stats["vision_error"],
    }


@app.get("/api/camera/stream")
def camera_stream():
    if cv2 is None:
        raise HTTPException(status_code=503, detail="OpenCV не установлен.")
    return StreamingResponse(_camera_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    import uvicorn
    print(f"JARVIS Local AI: http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
