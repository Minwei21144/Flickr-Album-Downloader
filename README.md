# Flickr Album Downloader

[繁體中文說明](README.zh_TW.md)

Flickr Album Downloader is a small desktop and command-line tool for saving Flickr albums to a local folder. It is designed for public albums, Flickr share links, guest pass links, and private albums that you can access in your signed-in browser.

Current app version: `1.0.0`.

The app downloads files directly into an album folder. It does not create a zip archive, and it keeps filenames based on the visible Flickr photo title whenever possible.

## Features

- Simple Windows, macOS, and Linux Python app.
- GUI language switch: English and Traditional Chinese.
- Supports standard album URLs, short share URLs, and guest pass URLs.
- Optional `cookies.txt` import for private albums you can view while signed in.
- Original / largest available download by default.
- Optional fallback to the nearest available size when the selected size is missing.
- Downloads photos and videos when Flickr exposes downloadable video URLs.
- Pause, resume, stop, and resume-from-existing-file workflows.
- Parallel downloads with user-selectable worker count.
- Folder conflict handling: resume, skip, overwrite, or save as a new folder.
- Built-in retry and backoff for Flickr HTTP 429 rate limiting.

## Important Notes

- Use this tool only for albums and files you are allowed to access and save.
- Private albums require browser cookies from a Flickr session that already has access.
- High parallel download counts can trigger Flickr HTTP 429. For large original-size albums, start with `1` worker and resume mode, then increase gradually.
- If 429 continues for more than about 10 minutes, wait and try later. Do not repeatedly switch IP addresses to bypass service limits.

## Install

Python 3.10 or newer is recommended.

```bash
python -m pip install -r requirements.txt
```

On Linux, install Tkinter if your Python distribution does not include it:

```bash
sudo apt install python3-tk
```

## Run the GUI

```bash
python flickr_album_downloader.py
```

Paste a Flickr album URL, click Confirm, verify the album title and cover preview, then click Start download.

## Command-Line Usage

```bash
python flickr_album_downloader.py --cli \
  --url "https://www.flickr.com/photos/user/albums/72177720300000000/" \
  --resolution original \
  --workers 1 \
  --conflict resume \
  --output "./downloads"
```

Private or guest pass album with cookies:

```bash
python flickr_album_downloader.py --cli \
  --cookies "./cookies.txt" \
  --url "https://www.flickr.com/gp/user/code" \
  --output "./downloads"
```

English / Traditional Chinese:

```bash
python flickr_album_downloader.py --language en
python flickr_album_downloader.py --language zh
python flickr_album_downloader.py --version
```

## Cookie File

For private albums, export cookies from a browser where you are already signed in to Flickr. The file must use Netscape `cookies.txt` format. Keep this file private; it may allow access to your Flickr session.

## Folder Conflict Modes

- `resume`: keep the folder and skip files that already exist.
- `skip`: skip the album if the folder already exists.
- `overwrite`: delete and recreate the album folder.
- `rename`: save to a new folder such as `Album Name (2)`.

## Build a Windows Executable

Install build dependencies:

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
```

Build:

```powershell
.\build_windows.ps1
```

The executable will be written to:

```text
dist\Flickr Album Downloader.exe
```

The build script generates the app icon and includes the custom Tcl/Tk packaging hooks needed for Python 3.14 Windows installs.

## Automated Cross-Platform Builds

The GitHub Actions workflow in `.github/workflows/build.yml` builds release-ready files for:

- `FlickrAlbumDownloader-1.0.0-windows-x64.exe`, `windows-x86.exe`, and `windows-arm64.exe`.
- `FlickrAlbumDownloader-1.0.0-macos-x64.dmg` and `macos-arm64.dmg`.
- `FlickrAlbumDownloader-1.0.0-linux-x64.AppImage` and `linux-arm64.AppImage`.

Run the `Build desktop apps` workflow manually from GitHub Actions to create build artifacts. Pushing a version tag such as `v1.0.0` also builds the apps and attaches the executable release files directly to the GitHub Release.

Windows and Linux arm64 runners are marked as GitHub public preview runners, so they are allowed to fail without blocking the stable x64/x86 builds.

macOS builds are packaged as drag-to-Applications DMG images. By default they are ad-hoc signed for testing. If Apple Developer ID and App Store Connect API secrets are configured, GitHub Actions signs the `.app`, signs the `.dmg`, submits the DMG for Apple notarization, staples the notarization ticket, and verifies the result. See [macOS notarization setup](docs/macos-notarization.md).

Linux builds are packaged as AppImage files. Some Linux desktop environments require marking a downloaded AppImage as executable before the first launch.

## Build on macOS / Linux

PyInstaller builds are platform-specific. Build on the same operating system and CPU architecture that you want to distribute for.

```bash
python -m pip install -r requirements.txt -r requirements-build.txt
python tools/generate_icons.py
python -m PyInstaller --windowed --name "Flickr Album Downloader" --icon assets/icon.png --add-data "assets/icon.png:assets" --add-data "assets/icon.ico:assets" flickr_album_downloader.py
```

For macOS release builds, use an `.icns` icon. The GitHub Actions workflow converts `assets/icon.png` to `assets/icon.icns` before building the `.app` bundle.

## Development

Run tests:

```bash
python -m unittest discover -s tests
```

## License

This project's own source code is licensed under the [MIT License](LICENSE).

Built applications may include third-party runtime components such as Python, Tcl/Tk, Pillow, and certifi. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for details.

## Flickr API References

- Flickr `flickr.photosets.getPhotos`: <https://www.flickr.com/services/api/flickr.photosets.getPhotos.html>
- Flickr URL formats: <https://www.flickr.com/services/api/misc.urls.html>
