#!/usr/bin/env python3
"""
yt-dlp Concurrent Download Manager
Arch Linux — runs multiple downloads simultaneously in the background.
Usage: python yt_dlp_manager.py
"""

import subprocess
import threading
import sys
import os
import signal
import shutil
from datetime import datetime

# ── ANSI colours ────────────────────────────────────────────────────────────
R   = "\033[1;31m"   # red
G   = "\033[1;32m"   # green
Y   = "\033[1;33m"   # yellow
B   = "\033[1;34m"   # blue
C   = "\033[1;36m"   # cyan
W   = "\033[1;37m"   # white
DIM = "\033[2m"
RST = "\033[0m"

# ── Config ───────────────────────────────────────────────────────────────────
DOWNLOAD_DIR  = os.path.expanduser("~/Downloads/yt-dlp")
YT_DLP_BINARY = "yt-dlp"          # make sure yt-dlp is in your PATH
PLAYLIST_MODE = False              # start in single-video mode
COOKIES_FILE  = ""                 # path to cookies .txt file, empty = not set

# Base yt-dlp flags (output path and playlist flag are added dynamically)
YT_DLP_BASE_ARGS = [
    "--embed-thumbnail",
    "--add-metadata",
    "-f", "bestvideo+bestaudio/best",
]


def build_args() -> list[str]:
    """Return yt-dlp args with current DOWNLOAD_DIR and playlist mode baked in."""
    if PLAYLIST_MODE:
        # Each playlist gets its own subdirectory named after the playlist
        template = os.path.join(DOWNLOAD_DIR, "%(playlist_title)s", "%(title)s.%(ext)s")
        playlist_flag = []
    else:
        # Flat — single video, no subdirectory
        template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
        playlist_flag = ["--no-playlist"]
    cookies_flag = ["--cookies", COOKIES_FILE] if COOKIES_FILE else []
    return YT_DLP_BASE_ARGS + playlist_flag + cookies_flag + ["-o", template]


# ── State (thread-safe) ──────────────────────────────────────────────────────
lock        = threading.Lock()
active_jobs: dict[str, threading.Thread] = {}   # url → thread
job_counter = 0


def ts() -> str:
    """Current timestamp string."""
    return datetime.now().strftime("%H:%M:%S")


def print_status():
    """Print how many downloads are currently running."""
    with lock:
        n = len(active_jobs)
    mode     = f"{G}PLAYLIST{RST}"    if PLAYLIST_MODE else f"{C}SINGLE VIDEO{RST}"
    cookies  = f"{G}SET{RST} {DIM}({COOKIES_FILE}){RST}" if COOKIES_FILE else f"{Y}NOT SET{RST}"
    if n == 0:
        print(f"  {DIM}[{ts()}] No active downloads.{RST}  Mode: {mode}  Cookies: {cookies}")
    else:
        print(f"  {C}[{ts()}] Active downloads: {n}{RST}  Mode: {mode}  Cookies: {cookies}")


def run_download(url: str, job_id: int, playlist_mode: bool):
    """Run yt-dlp for *url* in a background thread."""
    label = f"#{job_id}"
    mode_tag = f"{G}[PLAYLIST]{RST}" if playlist_mode else f"{C}[SINGLE]{RST}"

    print(f"\n{G}[{ts()}] {label} STARTED {mode_tag}  {DIM}{url}{RST}")
    print_status()

    # Snapshot the args at the moment the download starts
    cmd = [YT_DLP_BINARY] + build_args() + [url]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        if proc.returncode == 0:
            print(f"\n{G}[{ts()}] {label} ✔ DONE{RST}  {DIM}{url}{RST}")
        else:
            error_tail = proc.stdout.strip().splitlines()
            last_lines = "\n    ".join(error_tail[-6:]) if error_tail else "(no output)"
            print(
                f"\n{R}[{ts()}] {label} ✘ FAILED{RST}  {Y}{url}{RST}\n"
                f"    {DIM}{last_lines}{RST}"
            )

    except FileNotFoundError:
        print(
            f"\n{R}[{ts()}] {label} ✘ ERROR{RST}  "
            f"'{YT_DLP_BINARY}' not found — install it with: {Y}sudo pacman -S yt-dlp{RST}"
        )
    except Exception as exc:
        print(f"\n{R}[{ts()}] {label} ✘ EXCEPTION{RST}  {url}\n    {exc}")

    finally:
        with lock:
            active_jobs.pop(url, None)
        print_status()
        print(f"{DIM}  Enter a URL (or 'q' to quit): {RST}", end="", flush=True)


def spawn_download(url: str):
    """Validate the URL and launch a download thread."""
    global job_counter

    url = url.strip()
    if not url:
        return

    if not (url.startswith("http://") or url.startswith("https://")):
        print(f"{Y}  ⚠ Not a valid URL (must start with http/https). Skipped.{RST}")
        return

    with lock:
        if url in active_jobs:
            print(f"{Y}  ⚠ Already downloading that URL. Skipped.{RST}")
            return
        job_counter += 1
        jid = job_counter
        t = threading.Thread(
            target=run_download,
            args=(url, jid, PLAYLIST_MODE),
            daemon=True,
        )
        active_jobs[url] = t

    t.start()


def change_directory():
    """Ask the user for a new download directory, create it if needed."""
    global DOWNLOAD_DIR
    print(f"  {C}Current directory: {DOWNLOAD_DIR}{RST}")
    try:
        raw = input(f"  {DIM}New directory path: {RST}").strip()
    except EOFError:
        return

    if not raw:
        print(f"  {Y}⚠ No path entered. Directory unchanged.{RST}")
        return

    new_dir = os.path.expanduser(raw)

    if os.path.exists(new_dir):
        if not os.path.isdir(new_dir):
            print(f"  {R}✘ '{new_dir}' exists but is a file, not a directory. Unchanged.{RST}")
            return
        print(f"  {G}✔ Directory already exists. Switched to: {new_dir}{RST}")
    else:
        try:
            os.makedirs(new_dir, exist_ok=True)
            print(f"  {G}✔ Directory created: {new_dir}{RST}")
        except PermissionError:
            print(f"  {R}✘ Permission denied — cannot create '{new_dir}'. Unchanged.{RST}")
            return
        except Exception as exc:
            print(f"  {R}✘ Could not create directory: {exc}. Unchanged.{RST}")
            return

    DOWNLOAD_DIR = new_dir
    print(f"  {G}  Future downloads will go to: {DOWNLOAD_DIR}{RST}")


def toggle_playlist():
    """Toggle between single-video and playlist mode."""
    global PLAYLIST_MODE
    PLAYLIST_MODE = not PLAYLIST_MODE
    if PLAYLIST_MODE:
        print(
            f"  {G}✔ Playlist mode ON{RST} — full playlists will be downloaded.\n"
            f"  {DIM}  Each video saved as: playlist-name/video-title.ext{RST}"
        )
    else:
        print(
            f"  {C}✔ Single-video mode ON{RST} — only the individual video is downloaded,\n"
            f"  {DIM}  even if the URL belongs to a playlist.{RST}"
        )


def set_cookies():
    """Ask for a cookies .txt file path, or clear it if already set."""
    global COOKIES_FILE

    if COOKIES_FILE:
        print(f"  {C}Current cookies file: {COOKIES_FILE}{RST}")
        try:
            choice = input(f"  {DIM}Enter new path, or press Enter to CLEAR cookies: {RST}").strip()
        except EOFError:
            return
        if not choice:
            COOKIES_FILE = ""
            print(f"  {Y}✔ Cookies cleared. Downloads will proceed without authentication.{RST}")
            return
    else:
        print(f"  {DIM}No cookies file set.{RST}")
        try:
            choice = input(f"  {DIM}Enter path to cookies .txt file: {RST}").strip()
        except EOFError:
            return
        if not choice:
            print(f"  {Y}⚠ No path entered. Cookies unchanged.{RST}")
            return

    path = os.path.expanduser(choice)

    if not os.path.exists(path):
        print(f"  {R}✘ File not found: '{path}'. Cookies unchanged.{RST}")
        return
    if not os.path.isfile(path):
        print(f"  {R}✘ That path is not a file. Cookies unchanged.{RST}")
        return
    if not path.endswith(".txt"):
        # warn but still allow it — some people rename their cookies file
        print(f"  {Y}⚠ Warning: file does not end in .txt — make sure it is a Netscape-format cookies file.{RST}")

    COOKIES_FILE = path
    print(
        f"  {G}✔ Cookies set: {COOKIES_FILE}{RST}\n"
        f"  {DIM}  All future downloads will use this cookies file.{RST}\n"
        f"  {DIM}  Tip: export cookies with the 'Get cookies.txt LOCALLY' extension in Chrome/Firefox.{RST}"
    )


def check_yt_dlp():
    """Check that yt-dlp is installed. Exit with a helpful message if not."""
    if shutil.which(YT_DLP_BINARY) is None:
        print(
            f"\n{R}✘ '{YT_DLP_BINARY}' is not installed or not in your PATH.{RST}\n\n"
            f"  Install it on Arch Linux with:\n"
            f"    {Y}sudo pacman -S yt-dlp{RST}\n\n"
            f"  Or via pip:\n"
            f"    {Y}pip install yt-dlp{RST}\n"
        )
        sys.exit(1)

    # Also grab and show the installed version
    try:
        result = subprocess.run(
            [YT_DLP_BINARY, "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        version = result.stdout.strip()
        print(f"  {DIM}yt-dlp version: {RST}{G}{version}{RST}")
    except Exception:
        pass  # version check is cosmetic, don't crash if it fails



    """Block until every running download thread finishes."""
    with lock:
        threads = list(active_jobs.values())
    for t in threads:
        t.join()


def signal_handler(sig, frame):
    print(f"\n{Y}  Interrupted. Waiting for {len(active_jobs)} active download(s) to finish…{RST}")
    wait_for_all()
    print(f"{G}  All done. Goodbye.{RST}")
    sys.exit(0)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    signal.signal(signal.SIGINT, signal_handler)

    print(f"""
{C}╔══════════════════════════════════════════════╗
║       yt-dlp  Concurrent  Download Manager   ║
╚══════════════════════════════════════════════╝{RST}
  {DIM}Downloads go to : {RST}{W}{DOWNLOAD_DIR}{RST}
  {DIM}Mode             : {RST}{C}SINGLE VIDEO{RST} {DIM}(type {RST}{W}p{RST}{DIM} to switch){RST}
  {DIM}Cookies          : {RST}{Y}NOT SET{RST} {DIM}(type {RST}{W}c{RST}{DIM} to set){RST}
""")

    check_yt_dlp()
    print()

    print(
        f"  {W}URL{RST}   {DIM}→ start a download in the background{RST}\n"
        f"  {W}s{RST}     {DIM}→ show active downloads, mode & cookies status{RST}\n"
        f"  {W}d{RST}     {DIM}→ change output directory{RST}\n"
        f"  {W}p{RST}     {DIM}→ toggle single-video / playlist mode{RST}\n"
        f"  {W}c{RST}     {DIM}→ set / clear cookies .txt file (for login-gated sites){RST}\n"
        f"  {W}q{RST}     {DIM}→ quit (waits for active downloads to finish){RST}\n"
    )

    while True:
        try:
            raw = input(f"{DIM}  Enter a URL (or 'q' to quit): {RST}").strip()
        except EOFError:
            break

        cmd = raw.lower()

        if cmd in {"q", "quit", "exit"}:
            print(f"{Y}  Quitting — waiting for active downloads to finish…{RST}")
            wait_for_all()
            print(f"{G}  All done. Goodbye.{RST}")
            break

        elif cmd == "s":
            print_status()

        elif cmd == "d":
            change_directory()

        elif cmd == "p":
            toggle_playlist()

        elif cmd == "c":
            set_cookies()

        else:
            spawn_download(raw)


if __name__ == "__main__":
    main()
