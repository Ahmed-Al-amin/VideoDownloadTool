# Usage Guide — yt-dlp Concurrent Download Manager

This guide walks through every command and behavior of `yt_dlp_manager.py` in detail.

## 1. Starting the tool

```bash
python yt_dlp_manager.py
```

On startup the tool will:
1. Create the download directory (`~/Downloads/yt-dlp` by default) if it doesn't already exist
2. Register a `Ctrl+C` handler so an interrupt waits for active downloads instead of killing them
3. Check that `yt-dlp` is installed and print its version
4. Show the command menu and drop you into an interactive prompt

If `yt-dlp` is not found on your `PATH`, the tool will exit and print install instructions.

## 2. The interactive prompt

Once running, you'll see:

```
Enter a URL (or 'q' to quit):
```

From here you can either:
- **Paste a URL** to start a download, or
- **Type a single-letter command** (see below)

## 3. Commands

| Command | Action |
|---|---|
| *(paste a URL)* | Starts a new download in the background |
| `s` | Show status — number of active downloads, current mode, and cookies status |
| `d` | Change the output directory |
| `p` | Toggle between single-video mode and playlist mode |
| `c` | Set or clear the cookies file |
| `q` / `quit` / `exit` | Quit — waits for all active downloads to finish first |

### Starting a download

Simply paste any `http://` or `https://` URL and press Enter:

```
Enter a URL (or 'q' to quit): https://www.youtube.com/watch?v=example
```

The download starts immediately in its own thread, and you're returned to the prompt right away so you can queue more URLs. Each job gets a job number (`#1`, `#2`, ...) shown in the output so you can track it.

**Notes:**
- URLs must start with `http://` or `https://` — anything else is rejected
- You can't start the same URL twice while it's already downloading (it will be skipped)
- There's no hard limit on concurrent downloads — every valid URL you enter spawns a new thread

### Checking status (`s`)

Shows something like:

```
[14:32:10] Active downloads: 2  Mode: SINGLE VIDEO  Cookies: NOT SET
```

or, if idle:

```
[14:32:10] No active downloads.  Mode: PLAYLIST  Cookies: SET (/home/user/cookies.txt)
```

### Changing the output directory (`d`)

```
Enter a URL (or 'q' to quit): d
Current directory: /home/user/Downloads/yt-dlp
New directory path: /home/user/Videos
```

- `~` is expanded automatically (e.g. `~/Videos` works)
- If the directory doesn't exist, it's created for you
- If the path exists but is a file (not a folder), the change is rejected
- **Only affects downloads started after the change** — anything already running keeps using the old path

### Toggling playlist mode (`p`)

By default the tool is in **single-video mode**: even if you paste a playlist URL, only that one video downloads.

Typing `p` switches to **playlist mode**, where pasting a playlist URL downloads every video in it, saved into its own subfolder named after the playlist:

```
<download_dir>/<playlist name>/<video title>.<ext>
```

In single-video mode, files are saved flat:

```
<download_dir>/<video title>.<ext>
```

Typing `p` again switches back. The current mode is always shown in the `s` status output.

### Setting or clearing cookies (`c`)

Useful for downloading content that requires you to be logged in (age-restricted videos, private/unlisted content, members-only content, etc.).

```
Enter a URL (or 'q' to quit): c
No cookies file set.
Enter path to cookies .txt file: ~/cookies.txt
```

- The file must exist and be a regular file
- It should be in **Netscape cookie format** — you'll get a warning (not a hard failure) if the filename doesn't end in `.txt`
- **Tip:** export cookies using a browser extension such as "Get cookies.txt LOCALLY" for Chrome/Firefox

To **clear** an already-set cookies file, run `c` again and press Enter without typing a path:

```
Enter a URL (or 'q' to quit): c
Current cookies file: /home/user/cookies.txt
Enter new path, or press Enter to CLEAR cookies:
```

### Quitting (`q`)

```
Enter a URL (or 'q' to quit): q
Quitting — waiting for active downloads to finish…
```

The tool will **not** exit until every active download thread completes. Pressing `Ctrl+C` does the same thing — it will not abandon in-progress downloads.

## 4. Reading the output

Each download prints colored status lines as it progresses:

- 🟢 `STARTED` — job began, shows job number and URL
- 🟢 `✔ DONE` — finished successfully
- 🔴 `✘ FAILED` — yt-dlp returned a non-zero exit code; the last few lines of yt-dlp's output are printed to help diagnose the issue
- 🔴 `✘ ERROR` — the `yt-dlp` binary itself couldn't be found
- 🔴 `✘ EXCEPTION` — an unexpected Python error occurred while running the job

Because downloads run in background threads, output from multiple jobs can interleave — look for the job number (`#1`, `#2`, ...) and URL to tell them apart.

## 5. Download settings that apply to every job

Every download uses these fixed yt-dlp flags:

- `--embed-thumbnail` — embeds the video's thumbnail into the file
- `--add-metadata` — embeds title/description/etc. metadata
- `-f bestvideo+bestaudio/best` — picks the best available video and audio streams and merges them (falls back to best combined stream if separate streams aren't available)

Plus, dynamically:
- `--no-playlist` (only in single-video mode)
- `--cookies <path>` (only if a cookies file is set)
- `-o <output template>` — based on current directory and mode

**Important:** each download "snapshots" the current directory, mode, and cookies settings at the moment it *starts*. If you change settings while a download is already running, that running download keeps its original settings — only new downloads pick up the change.

## 6. Troubleshooting

| Problem | Likely cause / fix |
|---|---|
| Tool exits immediately with an install message | `yt-dlp` isn't installed or isn't on your `PATH` — see the [README](README.md) for install instructions |
| Download fails right away | Check the printed error tail; often means the URL is invalid, geo-blocked, or requires cookies |
| Age-restricted / login-required content fails | Set a cookies file with `c` |
| "Already downloading that URL. Skipped." | You pasted a URL that's already an active job — wait for it to finish or check with `s` |
| Playlist only downloads one video | You're in single-video mode — press `p` to switch to playlist mode |
| Files saved to the wrong place | Remember directory changes only apply to downloads started *after* the change |

## 7. Exiting safely

Always prefer `q` or `Ctrl+C` over force-killing the terminal — both wait for active downloads to finish cleanly, avoiding partially-downloaded or corrupted files.
