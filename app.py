import os
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, g, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "bookmarks.db")

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
    db.executescript("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            url        TEXT    NOT NULL UNIQUE,
            title      TEXT,
            icon       TEXT,
            tags       TEXT    DEFAULT \'\',
            created_at TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_title      ON bookmarks(title);
        CREATE INDEX IF NOT EXISTS idx_tags       ON bookmarks(tags);
        CREATE INDEX IF NOT EXISTS idx_created_at ON bookmarks(created_at);
    """)
    db.commit()
    db.close()


def fetch_meta(url: str):
    proxies = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BookmarkBot/1.0)"}
    try:
        resp = requests.get(url, headers=headers, proxies=proxies,
                            timeout=10, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title = ""
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            title = og["content"].strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        icon_url = ""
        for rel in ("shortcut icon", "icon", "apple-touch-icon"):
            tag = soup.find("link", rel=lambda r: r and rel in r)
            if tag and tag.get("href"):
                icon_url = tag["href"]
                break

        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if icon_url.startswith("//"):
            icon_url = parsed.scheme + ":" + icon_url
        elif icon_url and not icon_url.startswith("http"):
            icon_url = base + "/" + icon_url.lstrip("/")
        if not icon_url:
            icon_url = base + "/favicon.ico"

        return {"title": title or url, "icon": icon_url}
    except Exception as e:
        return {"title": url, "icon": "", "error": str(e)}


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
    tag  = request.args.get("tag", "").strip()
    q    = request.args.get("q", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = max(1, min(100, int(request.args.get("per_page", 20))))
    db   = get_db()

    conditions = []
    params = []

    if tag:
        conditions.append("\',\'||tags||\',\' LIKE ?")
        params.append(f"%,{tag},%")
    if q:
        conditions.append("(title LIKE ? OR url LIKE ? OR tags LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # 查总数
    total = db.execute(
        f"SELECT COUNT(*) FROM bookmarks {where}", params
    ).fetchone()[0]

    # 分页查询
    offset = (page - 1) * per_page
    rows = db.execute(
        f"SELECT * FROM bookmarks {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()

    return jsonify({
        "items":      [dict(r) for r in rows],
        "total":      total,
        "page":       page,
        "per_page":   per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


@app.route("/api/bookmarks", methods=["POST"])
def add_bookmark():
    data = request.json or {}
    url  = data.get("url", "").strip()
    title = data.get("title", "").strip() or url
    icon  = data.get("icon", "").strip()
    tags  = ",".join(t.strip() for t in data.get("tags", []) if t.strip())
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not url:
        return jsonify({"error": "url required"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO bookmarks (url, title, icon, tags, created_at) VALUES (?,?,?,?,?)",
            (url, title, icon, tags, created_at),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "duplicate", "message": "This URL already exists"}), 409
    row = db.execute("SELECT * FROM bookmarks WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/bookmarks/<int:bid>", methods=["PUT"])
def update_bookmark(bid):
    data  = request.json or {}
    title = data.get("title", "").strip()
    icon  = data.get("icon", "").strip()
    tags  = ",".join(t.strip() for t in data.get("tags", []) if t.strip())
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
    rows = db.execute("SELECT tags FROM bookmarks WHERE tags != \'\'").fetchall()
    tag_set = set()
    for r in rows:
        for t in r["tags"].split(","):
            t = t.strip()
            if t:
                tag_set.add(t)
    return jsonify(sorted(tag_set))


@app.route("/api/proxy-icon")
def proxy_icon():
    icon_url = request.args.get("url", "").strip()
    if not icon_url:
        return "", 400
    proxies = {"http": PROXY, "https": PROXY} if PROXY else None
    try:
        resp = requests.get(icon_url, proxies=proxies, timeout=5)
        content_type = resp.headers.get("content-type", "image/x-icon")
        return Response(resp.content, content_type=content_type)
    except Exception:
        return "", 404

init_db()
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
