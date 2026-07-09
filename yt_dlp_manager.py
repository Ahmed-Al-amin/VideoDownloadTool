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
import re
import signal
import shutil
from datetime import datetime

# ── ANSI colours ────────────────────────────────────────────────────────────
R   = "\033[1;31m"   # red
G   = "\033[1;32m"   # green
Y   = "\033[1;33m"   # yellow
B   = "\033[1;34m"   # blue
C   = "\033[1;36m"   # cyan
M   = "\033[1;35m"   # magenta
W   = "\033[1;37m"   # white
DIM = "\033[2m"
RST = "\033[0m"

# ── Config ───────────────────────────────────────────────────────────────────
DOWNLOAD_DIR    = os.path.expanduser("~/Downloads/yt-dlp")
YT_DLP_BINARY   = "yt-dlp"          # make sure yt-dlp is in your PATH
PLAYLIST_MODE   = False              # start in single-video mode
BYPASS_MODE     = False              # use --impersonate and -4 for blocked videos
COOKIES_FILE    = ""                 # path to cookies .txt file, empty = not set
STAGING_DIRNAME = ".activedownloads" # hidden folder used while a file is downloading

# Base yt-dlp flags (output path and playlist flag are added dynamically)
YT_DLP_BASE_ARGS = [
    "--embed-thumbnail",
    "--add-metadata",
    "-f", "bestvideo+bestaudio/best",
    "--newline",   # forces one progress line per update instead of \r overwrites
]

# ── Progress-line parsing ────────────────────────────────────────────────────
DEST_RE       = re.compile(r'\[download\]\s+Destination:\s+(.+)')
ALREADY_RE    = re.compile(r'\[download\]\s+(.+?)\s+has already been downloaded')
PROGRESS_RE   = re.compile(
    r'\[download\]\s+(?P<percent>[\d.]+)%'
    r'(?:\s+of\s+~?\s*(?P<size>[\d.]+\S*))?'
    r'(?:\s+at\s+(?P<speed>[\d.]+\S*|Unknown speed))?'
    r'(?:\s+ETA\s+(?P<eta>\S+))?'
)
MERGER_RE     = re.compile(r'\[Merger\]\s+Merging formats into "(.+)"')


def build_args(job_id: int, playlist_mode: bool, bypass_mode: bool, download_dir: str):
    """Return (yt-dlp args, staging_root) for this job.

    Every job gets its own staging subfolder (hidden, per-job) so concurrent
    downloads never collide, and so a job's files can be cleanly identified
    and moved to their final destination once yt-dlp is completely done with
    them (post-processing, thumbnail embedding, metadata, etc.).
    """
    staging_root = os.path.join(download_dir, STAGING_DIRNAME, f"job_{job_id}")

    if playlist_mode:
        # Each playlist gets its own subdirectory named after the playlist,
        # staged under the hidden folder first.
        template = os.path.join(staging_root, "%(playlist_title)s", "%(title)s.%(ext)s")
        playlist_flag = []
    else:
        # Flat — single video, no subdirectory
        template = os.path.join(staging_root, "%(title)s.%(ext)s")
        playlist_flag = ["--no-playlist"]

    cookies_flag = ["--cookies", COOKIES_FILE] if COOKIES_FILE else []

    # Bypass Flags
    bypass_flags = ["--impersonate", "chrome", "--rm-cache-dir", "-4"] if bypass_mode else []

    args = YT_DLP_BASE_ARGS + playlist_flag + cookies_flag + bypass_flags + ["-o", template]
    return args, staging_root


def move_finished_files(staging_root: str, download_dir: str, label: str) -> int:
    """Move every fully-downloaded file out of the hidden staging folder into
    the real download folder, preserving playlist subfolder structure.
    Returns the number of files moved."""
    if not os.path.isdir(staging_root):
        return 0

    moved = 0
    for root, _dirs, files in os.walk(staging_root):
        for fname in files:
            src = os.path.join(root, fname)
            rel = os.path.relpath(src, staging_root)
            dst = os.path.join(download_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)
                moved += 1
            except Exception as exc:
                print(f"  {R}⚠ {label} could not move '{fname}': {exc}{RST}")

    # Clean up this job's now-empty staging tree
    shutil.rmtree(staging_root, ignore_errors=True)
    return moved


# ── State (thread-safe) ──────────────────────────────────────────────────────
lock        = threading.Lock()
active_jobs: dict[str, threading.Thread] = {}   # url → thread
job_counter = 0
job_progress: dict[int, dict] = {}              # job_id → {title, percent, speed, eta, url}


def ts() -> str:
    """Current timestamp string."""
    return datetime.now().strftime("%H:%M:%S")


def print_status(show_progress: bool = False):
    """Print how many downloads are currently running and active modes.

    Per-job progress (name + %) is only included when show_progress=True,
    i.e. when the user explicitly presses 's'. Automatic status prints
    (on job start/finish) stay to the plain summary line."""
    with lock:
        n = len(active_jobs)
        progress_snapshot = dict(job_progress) if show_progress else {}

    mode     = f"{G}PLAYLIST{RST}"    if PLAYLIST_MODE else f"{C}SINGLE VIDEO{RST}"
    bypass   = f"{M}ON{RST}"          if BYPASS_MODE   else f"{DIM}OFF{RST}"
    cookies  = f"{G}SET{RST} {DIM}({COOKIES_FILE}){RST}" if COOKIES_FILE else f"{Y}NOT SET{RST}"

    status_line = (
        f"  {DIM}[{ts()}] {RST}"
        f"Active: {C}{n}{RST}  "
        f"Mode: {mode}  "
        f"Bypass: {bypass}  "
        f"Cookies: {cookies}"
    )
    print(status_line)

    if not show_progress:
        return

    if not progress_snapshot:
        if n:
            print(f"    {DIM}(no progress data yet — downloads still starting up){RST}")
        return

    for job_id in sorted(progress_snapshot):
        info = progress_snapshot[job_id]
        title = info.get("title") or info.get("url", "?")
        percent = info.get("percent")
        speed = info.get("speed") or "?"
        eta = info.get("eta") or "?"
        if percent is None:
            print(f"    {C}#{job_id}{RST} {DIM}starting…{RST}  {W}{title}{RST}")
        else:
            print(
                f"    {C}#{job_id}{RST} "
                f"{Y}{percent:5.1f}%{RST} "
                f"{DIM}{speed} ETA {eta}{RST}  "
                f"{W}{title}{RST}"
            )


def run_download(url: str, job_id: int, playlist_mode: bool, bypass_mode: bool, download_dir: str):
    """Run yt-dlp for *url* in a background thread, staging output in a hidden
    folder and moving finished files into the real folder afterwards."""
    label = f"#{job_id}"
    mode_tag = f"{G}[PLAYLIST]{RST}" if playlist_mode else f"{C}[SINGLE]{RST}"
    bypass_tag = f" {M}[BYPASS]{RST}" if bypass_mode else ""

    print(f"\n{G}[{ts()}] {label} STARTED {mode_tag}{bypass_tag}  {DIM}{url}{RST}")
    print_status()

    args, staging_root = build_args(job_id, playlist_mode, bypass_mode, download_dir)
    cmd = [YT_DLP_BINARY] + args + [url]

    output_lines: list[str] = []
    current_title = url
    last_percent  = -1.0

    with lock:
        job_progress[job_id] = {"title": url, "percent": None, "speed": None, "eta": None, "url": url}

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            output_lines.append(line)

            dest_match = DEST_RE.search(line)
            already_match = ALREADY_RE.search(line)
            merger_match = MERGER_RE.search(line)

            if dest_match:
                current_title = os.path.basename(dest_match.group(1))
                last_percent = -1.0
                with lock:
                    job_progress[job_id]["title"] = current_title
                    job_progress[job_id]["percent"] = 0.0
                continue

            if already_match:
                current_title = os.path.basename(already_match.group(1))
                with lock:
                    job_progress[job_id]["title"] = f"{current_title} (already downloaded)"
                continue

            if merger_match:
                with lock:
                    job_progress[job_id]["title"] = f"merging → {os.path.basename(merger_match.group(1))}"
                continue

            prog_match = PROGRESS_RE.search(line)
            if prog_match:
                percent = float(prog_match.group("percent"))
                speed = prog_match.group("speed") or "?"
                eta   = prog_match.group("eta") or "?"
                with lock:
                    job_progress[job_id]["percent"] = percent
                    job_progress[job_id]["speed"] = speed
                    job_progress[job_id]["eta"] = eta
                last_percent = percent

        proc.wait()

        if proc.returncode == 0:
            moved = move_finished_files(staging_root, download_dir, label)
            print(
                f"\n{G}[{ts()}] {label} ✔ DONE{RST}  "
                f"{DIM}({moved} file(s) moved to {download_dir}){RST}  {DIM}{url}{RST}"
            )
        else:
            last_lines = "\n    ".join(output_lines[-6:]) if output_lines else "(no output)"
            print(
                f"\n{R}[{ts()}] {label} ✘ FAILED{RST}  {Y}{url}{RST}\n"
                f"    {DIM}{last_lines}{RST}"
            )
            # Leave partial files in staging (untouched) so nothing broken
            # lands in the real folder — only clean up if it's already empty.
            if os.path.isdir(staging_root) and not os.listdir(staging_root):
                shutil.rmtree(staging_root, ignore_errors=True)

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
            job_progress.pop(job_id, None)
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
        # Snapshot the current mode/dir so this job stays locked to what it
        # was when the user hit Enter, even if settings change afterwards.
        t = threading.Thread(
            target=run_download,
            args=(url, jid, PLAYLIST_MODE, BYPASS_MODE, DOWNLOAD_DIR),
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
        print(f"  {G}✔ Playlist mode ON{RST}")
    else:
        print(f"  {C}✔ Single-video mode ON{RST}")


def toggle_bypass():
    """Toggle the bypass flags (impersonate chrome, rm-cache, ipv4)."""
    global BYPASS_MODE
    BYPASS_MODE = not BYPASS_MODE
    if BYPASS_MODE:
        print(f"  {M}✔ Bypass Mode ON{RST} — Using Chrome impersonation and IPv4.")
    else:
        print(f"  {DIM}✔ Bypass Mode OFF{RST} — Using standard yt-dlp settings.")


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

    COOKIES_FILE = path
    print(f"  {G}✔ Cookies set: {COOKIES_FILE}{RST}")


def check_yt_dlp():
    """Check that yt-dlp is installed."""
    if shutil.which(YT_DLP_BINARY) is None:
        print(f"\n{R}✘ '{YT_DLP_BINARY}' is not installed.{RST}")
        sys.exit(1)
    try:
        result = subprocess.run([YT_DLP_BINARY, "--version"], stdout=subprocess.PIPE, text=True)
        print(f"  {DIM}yt-dlp version: {RST}{G}{result.stdout.strip()}{RST}")
    except:
        pass


def wait_for_all():
    """Block until every running download thread finishes."""
    with lock:
        threads = list(active_jobs.values())
    for t in threads:
        t.join()


def cleanup_staging_root(download_dir: str):
    """Remove the top-level hidden staging container if it's empty.

    Each job already cleans up its own job_<id> subfolder on success, so by
    the time all downloads have finished, .activedownloads should just be an
    empty (or non-existent) directory. This wipes it so no trace is left
    behind when the script quits.
    """
    staging_container = os.path.join(download_dir, STAGING_DIRNAME)
    if not os.path.isdir(staging_container):
        return
    try:
        # Only remove leftover empty job dirs / the container itself.
        # Never touch a job dir that still has files in it (shouldn't happen
        # here since wait_for_all() already joined every thread, but be safe).
        for entry in os.listdir(staging_container):
            entry_path = os.path.join(staging_container, entry)
            if os.path.isdir(entry_path) and not os.listdir(entry_path):
                os.rmdir(entry_path)
        if not os.listdir(staging_container):
            os.rmdir(staging_container)
    except Exception:
        pass  # non-critical cleanup — don't block quitting over it


def signal_handler(sig, frame):
    print(f"\n{Y}  Interrupted. Waiting for {len(active_jobs)} active download(s) to finish…{RST}")
    wait_for_all()
    cleanup_staging_root(DOWNLOAD_DIR)
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
  {DIM}Directory : {RST}{W}{DOWNLOAD_DIR}{RST}
  {DIM}Staging   : {RST}{DIM}{STAGING_DIRNAME}/ (hidden — files move out once finished){RST}
  {DIM}Mode      : {RST}{C}SINGLE{RST} / {G}PLAYLIST{RST}
  {DIM}Bypass    : {RST}{M}--impersonate chrome -4{RST}
""")

    check_yt_dlp()
    print()

    print(
        f"  {W}URL{RST}   {DIM}→ start download{RST}\n"
        f"  {W}s{RST}     {DIM}→ status check{RST}\n"
        f"  {W}b{RST}     {DIM}→ toggle BYPASS mode (for blocked videos){RST}\n"
        f"  {W}p{RST}     {DIM}→ toggle playlist mode{RST}\n"
        f"  {W}d{RST}     {DIM}→ change directory{RST}\n"
        f"  {W}c{RST}     {DIM}→ set cookies{RST}\n"
        f"  {W}q{RST}     {DIM}→ quit{RST}\n"
    )

    while True:
        try:
            raw = input(f"{DIM}  Enter a URL (or command): {RST}").strip()
        except EOFError:
            break

        cmd = raw.lower()

        if cmd in {"q", "quit", "exit"}:
            print(f"{Y}  Quitting — waiting for active downloads to finish…{RST}")
            wait_for_all()
            cleanup_staging_root(DOWNLOAD_DIR)
            print(f"{G}  All done. Goodbye.{RST}")
            break
        elif cmd == "s":
            print_status(show_progress=True)
        elif cmd == "b":
            toggle_bypass()
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
