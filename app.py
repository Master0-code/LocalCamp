from flask import Flask, send_file, render_template, abort, request, session, redirect, url_for
from flask_socketio import SocketIO
from datetime import timedelta
import os
import secrets
import time

try:
    from dotenv import load_dotenv
    # Look for .env next to this file, not in whatever folder you happened
    # to launch python from — otherwise it silently fails to load.
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env") #this was the fix, cause i had multiple folders lined up, env file was is another
    load_dotenv(_env_path)
except ImportError:
    pass  # dotenv is optional — env vars can still be set the normal OS way

app = Flask(__name__)

# =========================================================
# SECRETS & SESSION CONFIG
# =========================================================

# SECRET_KEY: pulled from environment / .env, never hardcoded.
# Falls back to a random one-time key so the app still runs if you forget —
# but that means sessions won't survive a restart until you set it properly.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

# APP_PASSWORD: the single shared password gating access to the whole app.
APP_PASSWORD = os.environ.get("APP_PASSWORD")

if not APP_PASSWORD:
    APP_PASSWORD = secrets.token_urlsafe(9)
    print("=" * 60)
    print("No APP_PASSWORD set in your environment / .env file.")
    print(f"Generated a temporary password for this session: {APP_PASSWORD}")
    print("Set APP_PASSWORD in a .env file to keep it stable across restarts.")
    print("=" * 60)

SocketIO = SocketIO(app)

# =========================================================
# LOCAL LIBRARY
# =========================================================

LIBRARY_FOLDER = r"C:\your\file\that_you_want_to_put_ETC_to_share"  # change this to the path of the folder you want shared.

CATEGORIES = {
    "Pictures": {
        "folder": os.path.join(LIBRARY_FOLDER, "Pictures"),
        "extensions": {
            ".jpg", ".jpeg", ".png", ".gif",
            ".webp", ".bmp", ".svg"
        },
        "icon": "🖼️"
    },

    "Music": {
        "folder": os.path.join(LIBRARY_FOLDER, "Music"),
        "extensions": {
            ".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"
        },
        "icon": "🎵"
    },

    "Videos": {
        "folder": os.path.join(LIBRARY_FOLDER, "Videos"),
        "extensions": {
            ".mp4", ".webm", ".mkv", ".mov", ".avi"
        },
        "icon": "🎬"
    },

    "Documents": {
        "folder": os.path.join(LIBRARY_FOLDER, "Documents"),
        "extensions": {
            ".pdf", ".txt", ".doc", ".docx",
            ".xls", ".xlsx", ".ppt", ".pptx"
        },
        "icon": "📄"
    }
}


# =========================================================
# LOGIN RATE LIMITING (in-memory, per IP)
# =========================================================

LOGIN_ATTEMPTS = {}   # ip -> {"count": int, "locked_until": timestamp}
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes


def is_locked_out(ip):
    entry = LOGIN_ATTEMPTS.get(ip)
    return bool(entry and entry["locked_until"] > time.time())


def register_failed_attempt(ip):
    entry = LOGIN_ATTEMPTS.setdefault(ip, {"count": 0, "locked_until": 0})
    entry["count"] += 1

    if entry["count"] >= MAX_ATTEMPTS:
        entry["locked_until"] = time.time() + LOCKOUT_SECONDS
        entry["count"] = 0


def register_successful_login(ip):
    LOGIN_ATTEMPTS.pop(ip, None)


# =========================================================
# SECURITY — path safety + access control
# =========================================================

def safe_path(category, relative_path=""):

    if category not in CATEGORIES:
        abort(404)

    # realpath (not just abspath) resolves symlinks too, so a symlink
    # planted inside the library folder can't be used to escape it.
    base = os.path.realpath(CATEGORIES[category]["folder"])

    requested = os.path.realpath(
        os.path.join(base, relative_path)
    )

    # Prevent access outside the selected library folder
    if os.path.commonpath([base, requested]) != base:
        abort(403)

    return requested


def is_allowed_file(category, file_path):
    extension = os.path.splitext(file_path)[1].lower()
    return extension in CATEGORIES[category]["extensions"]


@app.before_request
def require_login():
    # Let the login page, logout, and static assets through without auth.
    if request.endpoint in ("login", "logout", "static") or request.endpoint is None:
        return

    if not session.get("authenticated"):
        return redirect(url_for("login", next=request.path))


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# =========================================================
# FILE INFORMATION
# =========================================================

def get_items(category, relative_path=""):

    folder = safe_path(category, relative_path)

    if not os.path.isdir(folder):
        abort(404)

    items = []

    for name in os.listdir(folder):

        # Skip hidden/system files (.git, .DS_Store, thumbs.db-style dotfiles, etc.)
        if name.startswith("."):
            continue

        full_path = os.path.join(folder, name)

        if os.path.isdir(full_path):

            items.append({
                "name": name,
                "type": "folder"
            })

        elif os.path.isfile(full_path):

            extension = os.path.splitext(name)[1].lower()

            if extension in CATEGORIES[category]["extensions"]:

                items.append({
                    "name": name,
                    "type": "file"
                })

    items.sort(
        key=lambda x: (
            x["type"] != "folder",
            x["name"].lower()
        )
    )

    return items


# =========================================================
# CUSTOM ERROR PAGES
# =========================================================

@app.errorhandler(404)
def not_found(e):
    return render_template(
        "error.html",
        error_code=404,
        error_icon="📂",
        error_title="Not found",
        error_message="This file or folder doesn't exist on the server."
    ), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template(
        "error.html",
        error_code=403,
        error_icon="🚫",
        error_title="Forbidden",
        error_message="You don't have permission to reach that path."
    ), 403


@app.errorhandler(500)
def server_error(e):
    return render_template(
        "error.html",
        error_code=500,
        error_icon="⚠️",
        error_title="Something broke",
        error_message="The server hit an unexpected error. Try again in a moment."
    ), 500


# =========================================================
# LOGIN / LOGOUT
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    ip = request.remote_addr
    error = None

    if is_locked_out(ip):
        error = "Too many attempts. Try again in a few minutes."

    elif request.method == "POST":
        submitted = request.form.get("password", "")

        if secrets.compare_digest(submitted, APP_PASSWORD):
            session.clear()
            session["authenticated"] = True
            session.permanent = True
            register_successful_login(ip)

            next_url = request.args.get("next") or url_for("home")
            return redirect(next_url)

        else:
            register_failed_attempt(ip)
            error = "Incorrect password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    category_icons = {
        name: data["icon"]
        for name, data in CATEGORIES.items()
    }

    return render_template("index.html", categories=category_icons)


# =========================================================
# BROWSE FOLDERS / FILES
# =========================================================

@app.route("/browse/<category>")
@app.route("/browse/<category>/<path:relative_path>")
def browse(category, relative_path=""):

    if category not in CATEGORIES:
        abort(404)

    items = get_items(category, relative_path)

    current_folder = relative_path.replace("\\", "/")

    if current_folder:
        parent = os.path.dirname(current_folder)
        back_url = "/browse/" + category

        if parent:
            back_url += "/" + parent.replace("\\", "/")
    else:
        back_url = "/"

    return render_template(
        "browse.html",
        category=category,
        category_icon=CATEGORIES[category]["icon"],
        current_folder=current_folder,
        items=items,
        back_url=back_url
    )


# =========================================================
# OPEN / PLAY FILE
# =========================================================

@app.route("/open/<category>/<path:relative_path>")
def open_file(category, relative_path):

    if category not in CATEGORIES:
        abort(404)

    file_path = safe_path(category, relative_path)

    if not os.path.isfile(file_path):
        abort(404)

    if not is_allowed_file(category, file_path):
        abort(403)

    extension = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path)

    template_by_category = {
        "Pictures": "view_image.html",
        "Music": "view_audio.html",
        "Videos": "view_video.html"
    }

    if category in template_by_category:
        return render_template(
            template_by_category[category],
            category=category,
            relative_path=relative_path,
            filename=filename
        )

    if extension == ".pdf":
        return render_template(
            "view_pdf.html",
            category=category,
            relative_path=relative_path,
            filename=filename
        )

    # Other documents (doc, xls, ppt, txt, etc.) — just send the file
    return send_file(
        file_path,
        as_attachment=False
    )


# =========================================================
# SERVE MEDIA FILE
# =========================================================

@app.route("/media/<category>/<path:relative_path>")
def media(category, relative_path):

    if category not in CATEGORIES:
        abort(404)

    file_path = safe_path(category, relative_path)

    if not os.path.isfile(file_path):
        abort(404)

    if not is_allowed_file(category, file_path):
        abort(403)

    return send_file(file_path)


# =========================================================
# DOWNLOAD
# =========================================================

@app.route("/download/<category>/<path:relative_path>")
def download(category, relative_path):

    if category not in CATEGORIES:
        abort(404)

    file_path = safe_path(category, relative_path)

    if not os.path.isfile(file_path):
        abort(404)

    if not is_allowed_file(category, file_path):
        abort(403)

    return send_file(
        file_path,
        as_attachment=True
    )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    SocketIO.run(
        app,
        host="0.0.0.0",
        port=80,
        debug=False
    )

# using flask with socketio, threaded=True, more to come as the core gets finished.
# something like gevent/eventlet is needed to handle multiple devices requesting/playing at once —
# otherwise a handful of simultaneous requests can bog down a single-threaded dev server.
# NOTE: this is still Werkzeug's development server. It works fine for a handful of
# trusted devices on a home LAN, but it is not hardened for adversarial traffic.
# For anything beyond that, run behind waitress or gunicorn+eventlet instead.