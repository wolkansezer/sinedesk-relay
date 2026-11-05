"""SineDesk Relay Sunucusu — ID ile internet üzerinden bağlantı.
Bir VPS'te çalıştırın:  python relay_server.py --port 8080
SineDesk Ayarlar > Relay adresi: http://SUNUCU_IP:8080  (HTTPS için önüne Caddy/Nginx koyun)
Telefon/tarayıcı ile: http://SUNUCU_IP:8080  → ID + şifre yazıp bağlanın.
"""
import argparse, asyncio, json, os, secrets, sys
from aiohttp import web, WSMsgType

RES = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(RES, "web")
OWNERS_FILE = os.environ.get("SINEDESK_IDS", os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "relay_ids.json"))

HOSTS = {}     # id -> ws
PENDING = {}   # sid -> Future(ws)
try:
    OWNERS = json.load(open(OWNERS_FILE, encoding="utf-8"))
except Exception:
    OWNERS = {}


def client_ip(req):
    return (req.headers.get("X-Forwarded-For", "").split(",")[0].strip() or req.remote or "?")


async def ws_host(req):
    hid, tok = req.query.get("id", ""), req.query.get("token", "")
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(req)
    if not (hid.isdigit() and len(hid) == 9 and len(tok) >= 16):
        await ws.send_str(json.dumps({"t": "error", "reason": "geçersiz kayıt"})); await ws.close(); return ws
    if OWNERS.get(hid) not in (None, tok):
        await ws.send_str(json.dumps({"t": "error", "reason": "ID başka cihazda kayıtlı"})); await ws.close(); return ws
    if hid not in OWNERS:
        OWNERS[hid] = tok
        json.dump(OWNERS, open(OWNERS_FILE, "w", encoding="utf-8"))
    old = HOSTS.get(hid)
    if old is not None:
        await old.close()
    HOSTS[hid] = ws
    try:
        async for _ in ws:
            pass
    finally:
        if HOSTS.get(hid) is ws:
            HOSTS.pop(hid, None)
    return ws


async def ws_hostdata(req):
    hid, tok, sid = req.query.get("id", ""), req.query.get("token", ""), req.query.get("sid", "")
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=0)
    await ws.prepare(req)
    fut = PENDING.get(sid)
    if OWNERS.get(hid) != tok or not fut or fut.done():
        await ws.close(); return ws
    done = asyncio.Event()
    fut.set_result((ws, done))
    await done.wait()
    return ws


async def pipe(a, b):
    async for msg in a:
        if msg.type == WSMsgType.TEXT:
            await b.send_str(msg.data)
        elif msg.type == WSMsgType.BINARY:
            await b.send_bytes(msg.data)
        else:
            break


async def ws_client(req):
    hid = req.query.get("id", "").replace(" ", "")
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=8 * 1024 * 1024)
    await ws.prepare(req)
    host = HOSTS.get(hid)
    if host is None:
        await ws.send_str(json.dumps({"t": "auth_fail", "reason": "Bu ID'ye sahip bilgisayar çevrimdışı."}))
        await ws.close(); return ws
    sid = secrets.token_hex(8)
    fut = asyncio.get_running_loop().create_future()
    PENDING[sid] = fut
    try:
        await host.send_str(json.dumps({"t": "incoming", "sid": sid, "ip": client_ip(req)}))
        hws, done = await asyncio.wait_for(fut, 15)
    except Exception:
        PENDING.pop(sid, None)
        await ws.send_str(json.dumps({"t": "auth_fail", "reason": "Bilgisayar yanıt vermedi."}))
        await ws.close(); return ws
    PENDING.pop(sid, None)
    t1 = asyncio.ensure_future(pipe(ws, hws))
    t2 = asyncio.ensure_future(pipe(hws, ws))
    await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
    for t in (t1, t2):
        t.cancel()
    await hws.close(); await ws.close()
    done.set()
    return ws


def page(name):
    async def h(req):
        return web.FileResponse(os.path.join(WEB, name), headers={"Cache-Control": "no-store"})
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    app = web.Application()
    app.router.add_get("/", page("client.html"))
    app.router.add_get("/client", page("client.html"))
    app.router.add_get("/viewer", page("viewer.html"))
    app.router.add_get("/info", lambda r: web.json_response({"kind": "relay"}))
    app.router.add_get("/ws/host", ws_host)
    app.router.add_get("/ws/hostdata", ws_hostdata)
    app.router.add_get("/ws/client", ws_client)
    app.router.add_static("/static", WEB)
    print(f"SineDesk Relay çalışıyor → http://{a.host}:{a.port}")
    web.run_app(app, host=a.host, port=a.port, access_log=None, print=None)


if __name__ == "__main__":
    main()
