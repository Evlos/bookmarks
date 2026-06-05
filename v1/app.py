import json
import os
import re
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, g, jsonify, render_template, request

app = Flask(__name__)
DATA_FOLDER = os.environ.get("DATA_FOLDER", "./data")
os.makedirs(DATA_FOLDER, exist_ok=True)
DB_PATH = os.path.join(DATA_FOLDER, "bookmarks.db")

# ── optional socks5 proxy ──────────────────────────────────────────────────────
# Set SOCKS5_PROXY env var like: socks5://user:pass@127.0.0.1:1080
PROXY = os.environ.get("SOCKS5_PROXY", "")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """CREATE TABLE IF NOT EXISTS bookmarks (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            url       TEXT    NOT NULL,
            title     TEXT,
            icon      TEXT,
            tags      TEXT    DEFAULT '',
            created_at TEXT   NOT NULL
        )"""
    )
    db.commit()
    db.close()


# ── helpers ────────────────────────────────────────────────────────────────────

def fetch_meta(url: str):
    """Fetch page title and favicon url via server-side request (supports socks5)."""
    proxies = {}
    if PROXY:
        proxies = {"http": PROXY, "https": PROXY}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; BookmarkBot/1.0)"
        )
    }
    try:
        resp = requests.get(url, headers=headers, proxies=proxies or None,
                            timeout=10, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # title
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # favicon – try link tags first, then /favicon.ico
        icon_url = ""
        for rel in ("shortcut icon", "icon", "apple-touch-icon"):
            tag = soup.find("link", rel=lambda r: r and rel in r)
            if tag and tag.get("href"):
                icon_url = tag["href"]
                break

        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if icon_url and icon_url.startswith("//"):
            icon_url = parsed.scheme + ":" + icon_url
        elif icon_url and not icon_url.startswith("http"):
            icon_url = base + "/" + icon_url.lstrip("/")
        if not icon_url:
            icon_url = base + "/favicon.ico"

        return {"title": title or url, "icon": icon_url}
    except Exception as e:
        return {"title": url, "icon": "", "error": str(e)}


# ── routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fetch-meta")
def api_fetch_meta():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "no url"}), 400
    return jsonify(fetch_meta(url))


@app.route("/api/bookmarks", methods=["GET"])
def list_bookmarks():
    tag = request.args.get("tag", "").strip()
    db = get_db()
    if tag:
        rows = db.execute(
            "SELECT * FROM bookmarks WHERE ','||tags||',' LIKE ? ORDER BY id DESC",
            (f"%,{tag},%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM bookmarks ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/bookmarks", methods=["POST"])
def add_bookmark():
    data = request.json or {}
    url = data.get("url", "").strip()
    title = data.get("title", "").strip() or url
    icon = data.get("icon", "").strip()
    tags = ",".join(t.strip() for t in data.get("tags", []) if t.strip())
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not url:
        return jsonify({"error": "url required"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO bookmarks (url, title, icon, tags, created_at) VALUES (?,?,?,?,?)",
        (url, title, icon, tags, created_at),
    )
    db.commit()
    row = db.execute("SELECT * FROM bookmarks WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/bookmarks/<int:bid>", methods=["PUT"])
def update_bookmark(bid):
    data = request.json or {}
    title = data.get("title", "").strip()
    icon = data.get("icon", "").strip()
    tags = ",".join(t.strip() for t in data.get("tags", []) if t.strip())
    db = get_db()
    db.execute(
        "UPDATE bookmarks SET title=?, icon=?, tags=? WHERE id=?",
        (title, icon, tags, bid),
    )
    db.commit()
    row = db.execute("SELECT * FROM bookmarks WHERE id=?", (bid,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/api/bookmarks/<int:bid>", methods=["DELETE"])
def delete_bookmark(bid):
    db = get_db()
    db.execute("DELETE FROM bookmarks WHERE id=?", (bid,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/tags")
def list_tags():
    db = get_db()
    rows = db.execute("SELECT tags FROM bookmarks WHERE tags != ''").fetchall()
    tag_set = set()
    for r in rows:
        for t in r["tags"].split(","):
            t = t.strip()
            if t:
                tag_set.add(t)
    return jsonify(sorted(tag_set))


@app.route("/api/proxy-icon")
def proxy_icon():
    """Proxy favicon images to avoid CORS issues."""
    icon_url = request.args.get("url", "").strip()
    if not icon_url:
        return "", 400
    proxies = {}
    if PROXY:
        proxies = {"http": PROXY, "https": PROXY}
    try:
        resp = requests.get(icon_url, proxies=proxies or None, timeout=5)
        content_type = resp.headers.get("content-type", "image/x-icon")
        from flask import Response
        return Response(resp.content, content_type=content_type)
    except Exception:
        return "", 404

init_db()
if __name__ == "__main__":
    app.run(debug=True, port=5000)