# JARVIS LAN Device Hub

A starter FastAPI hub for consent-based pairing, scoped permissions, command queues, and device revocation. It does not provide unrestricted access or execute arbitrary shell commands.

## Install on Windows

```powershell
cd jarvis_lan_devices
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
py -c "import secrets; print(secrets.token_urlsafe(40))"
```

Run the command twice and use the two generated values for `JARVIS_ADMIN_TOKEN` and `JARVIS_PAIRING_CODE` in `.env`.

```powershell
python main.py
```

Open `http://127.0.0.1:9014/docs`. Find the PC's LAN IP using `ipconfig`; clients on the same trusted Wi-Fi can use `http://LAN_IP:9014`. Only allow the port through Windows Firewall on a Private network. Do not port-forward this demo to the internet.

## Pairing workflow

1. Device owner calls `POST /api/pair/request` with `{"name":"My device","device_type":"windows","pairing_code":"YOUR_PAIRING_CODE"}`.
2. Admin calls `GET /api/admin/pair-requests` with `Authorization: Bearer YOUR_ADMIN_TOKEN`.
3. Admin approves via `POST /api/admin/devices/DEVICE_ID/approve`, JSON body e.g. `{"scopes":["status:read","display:notify"]}`.
4. Save the returned `device_token` securely on that device. It is returned only once.
5. View devices with `GET /api/admin/devices`; revoke access with `POST /api/admin/devices/DEVICE_ID/revoke`.

Available scopes: `status:read`, `media:control`, `smart_home:control`, `display:notify`. Actions are allowlisted. A revoked token stops working immediately.

## Windows agent

Copy `.env.example` to a separate `.env` next to `windows_agent.py`, set `JARVIS_SERVER=http://LAN_IP:9014` and `JARVIS_DEVICE_TOKEN=...`, then run `pip install httpx python-dotenv` and `python windows_agent.py`. The sample prints notifications; media controls are placeholders. It intentionally does not execute shell commands.

## Android and smart home

This package provides the API foundation, not an Android APK or direct Home Assistant integration. An Android companion should use these endpoints over the trusted LAN, ask the owner to confirm pairing, and store its token in Android Keystore. Home Assistant should use its official API with a dedicated least-privilege token stored server-side, mapping only approved actions to specific entity IDs. Do not expose Home Assistant tokens to browsers or client apps.

## Before production

The demo uses HTTP and is intended only for a trusted local network. For less-trusted networks, add TLS, user login, rate limiting, audit logs, token rotation, and explicit confirmation for sensitive actions. Never put the admin token in frontend JavaScript.
