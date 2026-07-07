# 未簽章 macOS 安裝說明

在沒有 Apple Developer Program 會員資格的情況下，macOS 版本會以未簽章 `.app.zip` 發布，而不是未簽章 DMG。

這是刻意的選擇：未簽章 DMG 可能在掛載前就被 macOS 擋下；ZIP 則可以讓使用者先解壓出 `.app`，拖進 Applications，再針對這個 App 手動允許一次。

English: [Unsigned macOS install notes](macos-unsigned-install.md)

## 安裝方式

1. 下載對應的 macOS ZIP：
   - Apple Silicon：`FlickrAlbumDownloader-1.0.0-macos-arm64.app.zip`
   - Intel：`FlickrAlbumDownloader-1.0.0-macos-x64.app.zip`
2. 雙擊 ZIP，解壓出 `Flickr Album Downloader.app`。
3. 把 `Flickr Album Downloader.app` 拖到 `/Applications`。
4. 對 App 按右鍵，選擇 **打開 / Open**，如果 macOS 跳出確認視窗，再按 **打開 / Open**。

如果 macOS 仍然阻擋，可以手動移除 quarantine 屬性：

```bash
xattr -dr com.apple.quarantine "/Applications/Flickr Album Downloader.app"
open "/Applications/Flickr Album Downloader.app"
```

只建議對你信任的 repository 或 release 頁面下載的版本執行這個動作。
