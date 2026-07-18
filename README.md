<div align="center">

# 🎬 yt-dlp Concurrent Download Manager

**A lightweight, terminal-based manager for running multiple `yt-dlp` downloads at once — with live progress, playlist support, and a bypass mode for blocked videos.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Arch%20Linux-1793D1?style=for-the-badge&logo=arch-linux&logoColor=white)](https://archlinux.org/)
[![yt-dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![License](https://img.shields.io/badge/License-MIT-brightgreen?style=for-the-badge)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-blueviolet?style=for-the-badge)](CONTRIBUTING.md)

</div>

---

## 📖 About

**yt-dlp Concurrent Download Manager** is a single-file Python script that wraps [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) in an interactive terminal interface. Instead of running one download at a time, it lets you queue up multiple URLs that download **simultaneously in background threads**, each with its own progress tracking, isolated staging folder, and clean move-to-destination on completion.

It was built for Arch Linux but works anywhere `yt-dlp` and Python 3.10+ are available.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔀 **Concurrent downloads** | Fire off multiple URLs back-to-back — each runs in its own background thread. |
| 📊 **Live progress tracking** | Press `s` at any time to see per-job percentage, speed, and ETA. |
| 📁 **Safe staging system** | Every job downloads into a hidden, isolated staging folder (`.activedownloads/job_<id>`) so concurrent downloads never collide or leave partial files in your real folder. |
| 🎵 **Playlist mode** | Toggle between single-video and full-playlist downloads, each playlist organized into its own subfolder. |
| 🛡️ **Bypass mode** | Toggle `--impersonate chrome`, `--rm-cache-dir`, and `-4` (force IPv4) on the fly for videos that are geo-blocked or bot-detected. |
| 🍪 **Cookie support** | Point to a `cookies.txt` file for age-restricted or login-gated content. |
| 🖼️ **Metadata & thumbnails** | Automatically embeds thumbnails and metadata into downloaded files. |
| 📂 **Custom download directory** | Change your output folder at any time without restarting. |
| 🧹 **Auto cleanup** | Empty staging folders are wiped on exit; failed downloads leave no partial files behind in your real folder. |
| ⌨️ **Graceful Ctrl+C** | Interrupting the script waits for active downloads to finish before exiting cleanly. |
| 🛡️ **Soft-fail recovery** | If thumbnail/metadata embedding fails but the media is fully downloaded, the tool recovers gracefully, purges auxiliary leftovers, and preserves the media file instead of failing. |

---

## 🎨 Color Legend

The interface uses ANSI colors to make status scannable at a glance:

| Color | Meaning |
|---|---|
| 🟢 **Green** | Success — job started, finished, or a setting turned ON |
| 🔴 **Red** | Failure, error, or a missing dependency |
| 🟡 **Yellow** | Warning — invalid input, duplicate URL, or a setting unset |
| 🔵 **Blue** | Reserved / structural accents |
| 🩵 **Cyan** | Job IDs, single-video mode, informational values |
| 🟣 **Magenta** | Bypass mode indicator |
| ⚪ **White** | File / video titles |
| ░ **Dim** | Secondary/contextual text (timestamps, hints, paths) |

---

## 📦 Requirements

- **Python 3.10+**
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) installed and available on your `PATH`
- **ffmpeg** (required by `yt-dlp` for merging video+audio and embedding thumbnails)

### Install on Arch Linux

```bash
sudo pacman -S yt-dlp ffmpeg
```

### Install on other systems

```bash
pip install -U yt-dlp
# then install ffmpeg via your package manager
```

---

## 🚀 Installation

```bash
git clone https://github.com/Ahmed-Al-amin/VideoDownloadTool.git
cd VideoDownloadTool
python yt_dlp_manager.py
```

No extra Python dependencies are required — the script only uses the standard library.

---

## 🕹️ Usage

Run the script and you'll get an interactive prompt:

```bash
python yt_dlp_manager.py
```

```
╔══════════════════════════════════════════════╗
║       yt-dlp  Concurrent  Download Manager   ║
╚══════════════════════════════════════════════╝
  Directory : ~/Downloads/yt-dlp
  Staging   : .activedownloads/ (hidden — files move out once finished)
  Mode      : SINGLE / PLAYLIST
  Bypass    : --impersonate chrome -4
```

Paste a URL and hit Enter to start a download, or use one of the single-letter commands below.

### Commands

| Key | Action |
|---|---|
| `<URL>` | Start a new download |
| `s` | Show status (active jobs, progress, speed, ETA) |
| `b` | Toggle **bypass mode** (for blocked/restricted videos) |
| `p` | Toggle **playlist mode** |
| `d` | Change the download directory |
| `c` | Set or clear a cookies file |
| `q` | Quit (waits for active downloads to finish first) |

### Example session

```
Enter a URL (or command): https://youtube.com/watch?v=example
[12:04:11] #1 STARTED [SINGLE]  https://youtube.com/watch?v=example

Enter a URL (or command): s
  Active: 1  Mode: SINGLE VIDEO  Bypass: OFF  Cookies: NOT SET
    #1  42.3%  3.2MiB/s ETA 00:14  Some Video Title.mp4

Enter a URL (or command): q
  Quitting — waiting for active downloads to finish…
[12:04:38] #1 ✔ DONE  (1 file(s) moved to ~/Downloads/yt-dlp)
  All done. Goodbye.
```

---

## ⚙️ Configuration

You can edit these defaults at the top of `yt_dlp_manager.py`, or change them at runtime with the in-app commands:

```python
DOWNLOAD_DIR    = os.path.expanduser("~/Downloads/yt-dlp")
YT_DLP_BINARY   = "yt-dlp"
PLAYLIST_MODE   = False
BYPASS_MODE     = False
COOKIES_FILE    = ""
```

Base `yt-dlp` flags used for every download:

```python
YT_DLP_BASE_ARGS = [
    "--embed-thumbnail",
    "--add-metadata",
    "-f", "bestvideo+bestaudio/best",
    "--newline",
]
```

---

## 🧠 How It Works

1. Each download runs in its own **daemon thread**, spawning `yt-dlp` as a subprocess.
2. Output goes first to a **hidden staging folder** (`~/Downloads/yt-dlp/.activedownloads/job_<id>`) so concurrent jobs never overwrite each other's files.
3. `yt-dlp`'s progress output is parsed line-by-line with regex to extract **percentage, speed, and ETA**, stored in a thread-safe shared dictionary.
4. On success, finished files are **moved** from staging into the real download folder (preserving playlist subfolders), and the staging folder is removed.
5. On failure, partial files are **left untouched** in staging so nothing broken ever lands in your real folder.
6. `Ctrl+C` triggers a graceful shutdown: it waits for all active downloads to finish, cleans up staging, then exits.
7. **Post-processing Soft-Fail Recovery:** If a download completes successfully but post-processing (such as thumbnail embedding or metadata tagging) fails, the tool recovers gracefully. It purges any non-media leftover files (like orphaned thumbnails/jsons) from staging, saves the main media file anyway, and reports the partial success instead of treating the entire download as failed.

---

## 🐞 Troubleshooting

| Problem | Fix |
|---|---|
| `'yt-dlp' is not installed` | Install it with `sudo pacman -S yt-dlp` (Arch) or `pip install -U yt-dlp`. |
| Video blocked / detected as bot | Press `b` to toggle **Bypass Mode**. |
| Age-restricted / login-required video | Press `c` and provide a `cookies.txt` file exported from your browser. |
| Download fails immediately | Press `s` to check status, or review the last output lines printed after a `✘ FAILED` message. |
| Post-processing or thumbnail embedding fails | If the actual video/audio downloads successfully but embedding fails, the tool automatically purges leftovers and keeps the downloaded media. |

---

## 🏷️ Tags

`yt-dlp` `youtube-downloader` `video-downloader` `python` `cli-tool` `terminal` `arch-linux` `concurrent-downloads` `playlist-downloader` `ffmpeg` `command-line-interface` `multithreading`

---

## 👤 Contributor

- [Ahmed Al-amin](https://github.com/Ahmed-Al-amin)

---

## 🤝 Contributing

Issues and pull requests are welcome! If you run into a bug or have an idea for a feature, feel free to open an issue on the [repo](https://github.com/Ahmed-Al-amin/VideoDownloadTool).

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with 🐍 and a lot of `--impersonate chrome`

</div>
