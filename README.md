# 📌 Bookmark Manager

A lightweight, self-hosted bookmark organizer with automatic metadata fetching, proxy support, and a sleek UI.

---

## Preview

![Preview](https://raw.githubusercontent.com/Evlos/uploads/refs/heads/main/Bookmarks%20-%20Google%20Chrome_2026-06-06_12-43-22.jpg)

## ✨ Features

- **Smart Addition:** Simply paste a URL — the application automatically fetches the page title and favicon in the background.
- **Dark Mode Support:** A built-in dark mode toggle that saves your preference to `localStorage` and automatically applies it on your next visit.
- **Tag Sidebar:** Keep everything organized with an intuitive left sidebar that displays all tags for quick, one-click filtering.
- **Full Bookmark Control:** Easily view, edit, and delete bookmarks. The list gracefully displays titles, icons, URLs, tags, and creation times.
- **Built-in Icon Proxy:** All third-party favicons are safely routed through a server-side proxy (`/api/proxy-icon`) to completely eliminate CORS issues.

## 🚀 Getting Started

### Prerequisites

Ensure you have Python installed on your machine.

### Installation

Install the required Python dependencies by running:

```bash
pip install flask "requests[socks]" beautifulsoup4
```

### Running the App

Start the Flask development server:

```bash
python app.py
```

Once the server is running, open your browser and navigate to [http://localhost:5000](http://localhost:5000).

## ⚙️ Configuration (SOCKS5 Proxy)

If you need to fetch web metadata through a SOCKS5 proxy (useful for restricted network environments), you can optionally set the `SOCKS5_PROXY` environment variable before starting the application.

**Without Authentication:**
```bash
export SOCKS5_PROXY="socks5://127.0.0.1:1080"
python app.py
```

**With Authentication:**
```bash
export SOCKS5_PROXY="socks5://user:password@127.0.0.1:1080"
python app.py
```

## 📂 Project Structure

```text
bookmark_app/
├── app.py              # Core Flask backend server
├── requirements.txt    # Python dependency list
├── data/
│   └── bookmarks.db    # SQLite database (auto-generated on first run)
└── templates/
    └── index.html      # Single-page frontend view (Tailwind CDN)
```

## 📄 License

This project is open-sourced under the [GNU General Public License v3.0](LICENSE).
