# Usage Guide — yt-dlp Concurrent Download Manager

This guide walks through every command, configuration, and background behavior of `yt_dlp_manager.py` in detail.

---

## 1. Starting the tool

Ensure you have Python 3.10+ and `yt-dlp` installed (along with `ffmpeg` for post-processing, thumbnail embedding, and metadata).

```bash
python yt_dlp_manager.py
```

On startup, the tool will:
1. Verify that `yt-dlp` is installed and print the current version.
2. Register a graceful `Ctrl+C` / signal handler so interrupts wait for active downloads instead of creating corrupted partial files.
3. Display the configuration and command menus.
4. Drop you into an interactive command prompt.

If `yt-dlp` is not found on your system `PATH`, the tool will display helpful install instructions and exit with status code `1`.

---

## 2. The interactive prompt

Once running, you'll see:

```
Enter a URL (or command):
```

From here, you can:
- **Paste a URL** to start a download thread in the background.
- **Type a single-letter command** (see below).

---

## 3. Commands

| Key | Action |
|---|---|
| `<URL>` | Starts a new download in the background (threads are managed concurrently) |
| `s` | Status check — displays a snapshot of active jobs with live progress percentage, speed, ETA, and video titles |
| `b` | Toggle **bypass mode** (enables Chrome impersonation, cache deletion, and IPv4 force) |
| `p` | Toggle **playlist mode** (single video download vs full playlist) |
| `d` | Change the download directory |
| `c` | Set or clear the Netscape cookies file |
| `q` / `quit` / `exit` | Quit — waits for all active downloads to finish cleanly before exiting |

### Starting a download

Simply paste any `http://` or `https://` URL and press Enter:

```
Enter a URL (or command): https://www.youtube.com/watch?v=example
```

The download starts immediately in its own background daemon thread. You are returned to the prompt instantly so you can queue more URLs. Each job receives a job number (`#1`, `#2`, ...) shown in the output to help you track it.

**Important details:**
- URLs must start with `http://` or `https://` — invalid paths are rejected with a warning.
- Duplicate downloads of the same URL currently in progress are prevented.
- There is no hard-coded limit on concurrent downloads.

### Checking status with live progress (`s`)

Typing `s` displays a live, structured overview of all active downloads, including their current progress, download speed, remaining time, and titles.

**Example output:**
```
  [12:04:15] Active: 2  Mode: SINGLE VIDEO  Bypass: OFF  Cookies: NOT SET
    #1   42.3%  3.2MiB/s ETA 00:14  Some Awesome Video.mp4
    #2    8.7%  1.1MiB/s ETA 02:45  Another Great Clip.mp4
```

If there are no running downloads, it prints:
```
  [12:04:30] Active: 0  Mode: SINGLE VIDEO  Bypass: OFF  Cookies: NOT SET
```

### Toggling bypass mode (`b`)

If a video is geo-blocked, restricted, or failing due to bot-detection/rate-limiting, press `b` to toggle **Bypass Mode**.

- **When ON:** Adds `--impersonate chrome`, `--rm-cache-dir`, and `-4` (forces IPv4) to the `yt-dlp` subprocess.
- **When OFF:** Uses standard `yt-dlp` arguments.
- Mode changes only apply to *new* downloads queued after the toggle.

### Toggling playlist mode (`p`)

By default, the tool is in **single-video mode**: even if you paste a playlist URL, only that specific video is downloaded.

Typing `p` switches to **playlist mode**: pasting a playlist URL downloads every video in the playlist, organizing them into a subdirectory named after the playlist:

```
<download_dir>/<playlist name>/<video title>.<ext>
```

In single-video mode, files are saved flat:

```
<download_dir>/<video title>.<ext>
```

Press `p` again to switch back. The current mode is displayed on the `s` status line.

### Changing the download directory (`d`)

```
Enter a URL (or command): d
Current directory: /home/user/Downloads/yt-dlp
New directory path: ~/Videos
  ✔ Directory updated to: /home/user/Videos
```

- `~` is automatically expanded to your home directory (e.g., `/home/user`).
- If the directory doesn't exist, it is created automatically.
- Path changes only affect downloads started *after* the change. Existing active jobs continue downloading to their original destination.

### Setting or clearing cookies (`c`)

Required for downloading private, age-restricted, login-gated, or subscriber-only content.

#### How to obtain cookies
1. **Method A (Recommended):** Log in to the website you want to download from, then install a browser extension like **"Get cookies.txt LOCALLY"**. Use it to export your cookies as a `.txt` file.
2. **Method B (Manual):** If Method A is not possible, you can manually copy your browser cookies. In your terminal, run:
   ```bash
   echo "PASTE_YOUR_COPIES_HERE" > cookies.txt
   ```
   This will create a `cookies.txt` file in your current folder.

#### Using cookies in the tool
```
Enter a URL (or command): c
No cookies file set.
Enter path to cookies .txt file: ~/cookies.txt
  ✔ Cookies set: /home/user/cookies.txt
```

- The cookies file must be in Netscape cookies format.
- To clear an existing cookies file, run `c` again and press Enter without typing a path:

```
Enter a URL (or command): c
Current cookies file: /home/user/cookies.txt
Enter new path, or press Enter to CLEAR cookies: 
  ✔ Cookies cleared.
```

### Quitting (`q`)

Typing `q` (or hitting `Ctrl+C`) initiates a graceful exit:

```
Enter a URL (or command): q
  Quitting — waiting for active downloads to finish…
```

The application will block until all background downloads are fully completed and moved out of staging. It then deletes any empty staging folders and exits cleanly.

---

## 4. The Safe Staging System

To support safe concurrent downloads, the tool employs an isolated staging workflow:

1. **Staging Folder:** Each download job is assigned a unique, hidden folder inside your download directory: `.activedownloads/job_<id>`.
2. **Isolation:** Files are downloaded, merged, and post-processed (adding metadata and embedding thumbnails) inside this hidden folder. Concurrent downloads never collide or overwrite each other.
3. **Move-on-Success:** Once `yt-dlp` completes successfully and terminates with code `0`, the finished files are moved atomically to the final download folder (preserving playlist directories if in playlist mode), and the staging directory for that job is wiped.
4. **No Half-Finished Files:** If a download fails or is terminated, the partial files are **left untouched** inside the hidden staging folder. This prevents corrupted, half-downloaded, or unmerged `.part` and `.temp` files from cluttering your actual download folder.
5. **Cleanup:** When the script exits, empty staging directories are completely cleaned up.
6. **Auxiliary File Purge & Soft-Fail Recovery:** Before moving files out of staging, any non-media leftover files (such as orphaned thumbnails, `.part`/`.ytdl` fragments, `.info.json` etc.) are automatically purged, ensuring only the actual video/audio media files end up in your download folder. Furthermore, if `yt-dlp` returns a non-zero exit code but the actual media finished downloading fine — failing only on subsequent thumbnail or metadata post-processing — the tool treats this as a "soft-fail" rather than a hard failure. It purges the staging junk, saves the downloaded media file to the destination folder, and reports a status of `✔ DONE (thumbnail/metadata embed failed, video kept)` instead of failing.

---

## 5. Reading the Output & Color Legend

The CLI utilizes clean ANSI escape colors to make terminal status readable at a glance:

| Color | Meaning |
|---|---|
| 🟢 **Green** | Success, job completion, or a feature/setting turned ON |
| 🔴 **Red** | Failures, missing dependencies, or errors |
| 🟡 **Yellow** | Warning, invalid input, duplicate URLs, or settings turned OFF |
| 🔵 **Blue** | Visual dividers, frame borders, and structural styling |
| 🩵 **Cyan** | Job IDs, single-video mode status, and prompt highlights |
| 🟣 **Magenta** | Bypass mode highlights and parameters |
| ⚪ **White** | Filenames and video titles |
| ░ **Dim** | Contextual metadata, timestamps, and helpful tips |

Each background event prints a labeled message with its job ID and a timestamp:

- `[12:04:11] #1 STARTED [SINGLE] https://...`
- `[12:04:38] #1 ✔ DONE (1 file(s) moved to ~/Downloads/yt-dlp)`
- `[12:05:01] #2 ✘ FAILED https://...` (followed by the last 6 lines of `yt-dlp` output to diagnose the issue)
- `[12:05:05] #3 ✔ DONE (thumbnail/metadata embed failed, video kept) (1 file(s) moved to ~/Downloads/yt-dlp)` (printed when a soft-fail post-processing error occurs but the video/audio is preserved)

---

## 6. Download settings (Subprocess Parameters)

Every job is executed via Python's standard library `subprocess` with these foundational parameters:

- `--embed-thumbnail` — Embeds the video's thumbnail cover art directly into the file.
- `--add-metadata` — Embeds description, uploader, title, and upload date.
- `-f bestvideo+bestaudio/best` — Picks the highest quality video and audio streams and merges them (requires `ffmpeg`).
- `--newline` — Standardizes output logging to simplify live progress parsing.

Additional dynamic flags:
- `--no-playlist` (passed when in single-video mode).
- `--cookies <path>` (passed if cookies are set).
- `--impersonate chrome --rm-cache-dir -4` (passed if bypass mode is ON).
- `-o <output_template>` (maps the files directly into `.activedownloads/job_<id>`).

---

## 7. Troubleshooting

| Problem | Cause / Solution |
|---|---|
| **`'yt-dlp' is not installed`** | Ensure `yt-dlp` is installed and added to your system `PATH`. Check with `which yt-dlp` or `yt-dlp --version`. |
| **`ffmpeg` warnings or format merge errors** | Ensure `ffmpeg` is installed. It's required by `yt-dlp` to merge high-quality video and audio tracks, embed thumbnails, and write metadata. |
| **Video blocked, bot detected, or HTTP 403 / 400 errors** | Press `b` to toggle **Bypass Mode**. If that fails, export a Netscape format `cookies.txt` file and set it with `c`. |
| **Download fails immediately** | Press `s` to inspect the status, or read the trailing logs printed directly after the `✘ FAILED` error message. |
| **Duplicate download skips** | The tool blocks simultaneous downloads of identical URLs to save bandwidth. Wait for the active job to finish or check progress with `s`. |
| **Playlist downloads only one video** | The tool is running in single-video mode. Press `p` to toggle **Playlist Mode** ON. |
| **Post-processing/thumbnail embedding fails** | If the media is fully downloaded but post-processing fails, the tool handles it as a soft-fail, purges staging leftovers, and keeps the media file. |

---

## 8. Exiting Safely

Always quit using `q` or `Ctrl+C`. This ensures:
1. In-progress threads are allowed to finish writing and packaging their streams cleanly.
2. `ffmpeg` completes any active formatting and metadata embedding, preventing corrupt files.
3. Any unused empty staging subdirectories under `.activedownloads` are cleaned up.
