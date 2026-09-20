import os
import socket
import uuid
import time
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis

from .db import Base, engine, get_db
from .models import Visit
from .config import REDIS_URL, INSTANCE_ID

import time

def init_db_with_retry():
    for i in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            print("DB init OK")
            return
        except Exception as e:
            print(f"DB init attempt {i}: {e}")
            time.sleep(2)
    print("DB init failed after retries, продолжаем")

init_db_with_retry()

app = FastAPI(title="PR2 backend")
r = redis.from_url(REDIS_URL, decode_responses=True)

HOSTNAME = socket.gethostname()
BOOT_UUID = str(uuid.uuid4())

def node_info():
    return {
        "instance_id": INSTANCE_ID,
        "hostname": HOSTNAME,
        "boot_uuid": BOOT_UUID,
        "pid": os.getpid(),
    }

@app.get("/", response_class=HTMLResponse)
def root():
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>PR2 backend</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
                color: #e2e8f0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .card {{
                background: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 16px;
                padding: 40px;
                max-width: 640px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.5);
                backdrop-filter: blur(10px);
            }}
            h1 {{
                font-size: 28px;
                margin-bottom: 8px;
                color: #f8fafc;
            }}
            .subtitle {{
                color: #94a3b8;
                font-size: 14px;
                margin-bottom: 32px;
            }}
            .badge {{
                display: inline-block;
                padding: 8px 16px;
                border-radius: 999px;
                font-weight: 600;
                font-size: 14px;
                margin-bottom: 24px;
            }}
            .badge.app1 {{ background: #10b981; color: #052e16; }}
            .badge.app2 {{ background: #3b82f6; color: #082f49; }}
            .badge.other {{ background: #f59e0b; color: #451a03; }}
            .row {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid rgba(148, 163, 184, 0.1);
                font-size: 15px;
            }}
            .row:last-child {{ border-bottom: none; }}
            .label {{ color: #94a3b8; }}
            .value {{
                color: #f1f5f9;
                font-family: 'SF Mono', Menlo, monospace;
                font-size: 14px;
            }}
            .counter {{
                margin-top: 24px;
                padding: 20px;
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 12px;
                text-align: center;
            }}
            .counter .num {{
                font-size: 42px;
                font-weight: 700;
                color: #60a5fa;
                display: block;
                margin-bottom: 4px;
            }}
            .counter .cap {{
                color: #94a3b8;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .links {{
                margin-top: 24px;
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .links a {{
                padding: 10px 18px;
                background: rgba(148, 163, 184, 0.1);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
                color: #cbd5e1;
                text-decoration: none;
                font-size: 14px;
                transition: all 0.2s;
            }}
            .links a:hover {{
                background: rgba(148, 163, 184, 0.2);
                color: #f8fafc;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>PR2 backend</h1>
            <p class="subtitle">FastAPI · Postgres · Redis · Docker</p>

            <span class="badge {INSTANCE_ID if INSTANCE_ID in ('app1', 'app2') else 'other'}">
                {INSTANCE_ID}
            </span>

            <div class="row"><span class="label">Hostname</span><span class="value">{HOSTNAME}</span></div>
            <div class="row"><span class="label">Boot UUID</span><span class="value">{BOOT_UUID[:8]}…</span></div>
            <div class="row"><span class="label">PID</span><span class="value">{os.getpid()}</span></div>

            <div class="links">
                <a href="/whoami">/whoami</a>
                <a href="/health">/health</a>
                <a href="/docs">/docs</a>
                <a href="/visits">/visits</a>
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.get("/whoami")
def whoami():
    return node_info()

@app.get("/visits")
def visits(request: Request, db: Session = Depends(get_db)):
    total = r.incr("visits:total")
    v = Visit(instance_id=INSTANCE_ID, path=str(request.url.path))
    db.add(v)
    db.commit()
    return {"total_visits_redis": total, **node_info()}

@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        r.ping()
        return {"status": "ok", **node_info()}
    except Exception as e:
        return {"status": "error", "detail": str(e), **node_info()}