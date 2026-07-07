# Unsigned macOS Install Notes

Without an Apple Developer Program membership, macOS builds are distributed as unsigned `.app.zip` files instead of unsigned DMG files.

This is intentional: an unsigned DMG can be blocked before it even mounts. A ZIP lets the user extract the `.app`, move it to Applications, and explicitly allow that app once.

Traditional Chinese: [未簽章 macOS 安裝說明](macos-unsigned-install.zh_TW.md)

## Install

1. Download the matching macOS ZIP:
   - Apple Silicon: `FlickrAlbumDownloader-1.0.0-macos-arm64.app.zip`
   - Intel: `FlickrAlbumDownloader-1.0.0-macos-x64.app.zip`
2. Double-click the ZIP to extract `Flickr Album Downloader.app`.
3. Move `Flickr Album Downloader.app` to `/Applications`.
4. Right-click the app and choose **Open**, then confirm **Open** if macOS allows it.

If macOS still blocks the app, remove the quarantine attribute manually:

```bash
xattr -dr com.apple.quarantine "/Applications/Flickr Album Downloader.app"
open "/Applications/Flickr Album Downloader.app"
```

Only do this for builds downloaded from a repository or release page you trust.
