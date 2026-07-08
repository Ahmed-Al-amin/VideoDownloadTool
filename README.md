# yt-dlp Concurrent Download Manager

A lightweight Python CLI wrapper around [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) that lets you queue up and run **multiple downloads at the same time** in the background, right from an interactive prompt — built and tested on Arch Linux.

```
╔══════════════════════════════════════════════╗
║       yt-dlp  Concurrent  Download Manager   ║
╚══════════════════════════════════════════════╝
```

## Features

- 🚀 **Concurrent downloads** — fire off as many URLs as you want; each runs in its own background thread
- 📺 **Single video / playlist mode toggle** — switch on the fly between downloading just one video or an entire playlist
- 📁 **Configurable output directory** — change where files are saved at any time, directory is created automatically if it doesn't exist
- 🍪 **Cookies support** — supply a Netscape-format `cookies.txt` file for login-gated content
- 🎨 **Colorized live status output** — see what's downloading, what finished, and what failed at a glance
- 🛑 **Graceful shutdown** — `Ctrl+C` or `q` waits for in-progress downloads to finish before exiting
- 🖼️ Automatically embeds thumbnails and metadata into downloaded files

## Requirements

- Python 3.10+ (uses `list[str]` type hints)
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) installed and available on your `PATH`

### Installing yt-dlp

**Arch Linux:**
```bash
sudo pacman -S yt-dlp
```

**Via pip (any OS):**
```bash
pip install yt-dlp
```

## Installation

Clone the repo and run the script directly — no extra dependencies required, it only uses the Python standard library.

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python yt_dlp_manager.py
```

## Quick Start

```bash
python yt_dlp_manager.py
```

Then just paste a URL and hit Enter — the download starts immediately in the background and you can keep queuing more URLs while it runs.

For the full command reference and detailed walkthrough, see the [Usage Guide](USAGE_GUIDE.md).

## Default Configuration

| Setting | Default |
|---|---|
| Download directory | `~/Downloads/yt-dlp` |
| Mode | Single video |
| Cookies | Not set |
| Format | `bestvideo+bestaudio/best` |
| Extras | Embeds thumbnail + metadata |

All of these (except format) can be changed interactively while the tool is running.

## License

Add your preferred license here (e.g. MIT).

## Disclaimer

This tool is a convenience wrapper around yt-dlp. Only download content you have the right to download, and respect the terms of service of the sites you use it with.
