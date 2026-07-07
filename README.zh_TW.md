# Flickr 相簿下載器

[English README](README.md)

Flickr 相簿下載器是一個簡單的桌面與命令列工具，用來把 Flickr 相簿儲存到本機資料夾。它支援公開相簿、Flickr 分享短連結、guest pass 連結，以及你已經能在登入瀏覽器中查看的私人相簿。

目前版本：`1.0.0`

程式會直接把檔案下載到相簿資料夾，不會另外建立 zip 壓縮檔。檔名會盡量依照 Flickr 網頁上可見的相片標題保留。

## 功能

- 支援 Windows、macOS、Linux。
- 圖形介面支援英文與繁體中文切換。
- 支援標準相簿網址、短分享網址與 guest pass 網址。
- 可匯入 `cookies.txt`，下載你登入後可查看的私人相簿。
- 預設下載原檔 / 最大可用尺寸。
- 選定尺寸不存在時，可選擇改用最接近的可用尺寸。
- 相簿內若包含 Flickr 可下載的影片，也會一起下載。
- 支援暫停、繼續、停止，以及從既有檔案恢復進度。
- 支援使用者自行設定同時下載數量。
- 支援資料夾衝突處理：恢復、跳過、覆蓋、另存新資料夾。
- 內建 Flickr HTTP 429 限流重試與退避等待。

## 注意事項

- 請只下載你有權存取與保存的相簿和檔案。
- 私人相簿需要從已登入且有權限查看 Flickr 的瀏覽器匯出 cookies。
- 過高的同時下載數可能觸發 Flickr HTTP 429。大型原檔相簿建議先用 `1` 個下載執行緒與恢復模式，再逐步提高。
- 如果 429 持續超過約 10 分鐘，請先等待再試。不要頻繁切換 IP 來規避服務限制。

## 安裝

建議使用 Python 3.10 或更新版本。

```bash
python -m pip install -r requirements.txt
```

Linux 若 Python 沒有內建 Tkinter，請先安裝：

```bash
sudo apt install python3-tk
```

## 啟動圖形介面

```bash
python flickr_album_downloader.py
```

貼上 Flickr 相簿網址，按下確認，檢查相簿名稱與封面預覽後，再按開始下載。

## 命令列用法

```bash
python flickr_album_downloader.py --cli \
  --url "https://www.flickr.com/photos/user/albums/72177720300000000/" \
  --resolution original \
  --workers 1 \
  --conflict resume \
  --output "./downloads"
```

使用 cookies 下載私人或 guest pass 相簿：

```bash
python flickr_album_downloader.py --cli \
  --cookies "./cookies.txt" \
  --url "https://www.flickr.com/gp/user/code" \
  --output "./downloads"
```

英文 / 繁體中文：

```bash
python flickr_album_downloader.py --language en
python flickr_album_downloader.py --language zh
python flickr_album_downloader.py --version
```

## Cookie 檔案

私人相簿請從已登入 Flickr 且有權限查看相簿的瀏覽器匯出 Netscape `cookies.txt` 格式。請妥善保管這個檔案，因為它可能允許存取你的 Flickr 登入狀態。

## 資料夾衝突模式

- `resume`：保留資料夾，跳過已存在的檔案。
- `skip`：如果資料夾已存在，跳過整個相簿。
- `overwrite`：刪除並重新建立相簿資料夾。
- `rename`：另存成新資料夾，例如 `相簿名稱 (2)`。

## 建立 Windows 執行檔

安裝建置依賴：

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
```

建置：

```powershell
.\build_windows.ps1
```

執行檔會輸出到：

```text
dist\Flickr Album Downloader.exe
```

建置腳本會產生應用程式圖示，並包含 Python 3.14 Windows 安裝所需的 Tcl/Tk PyInstaller hook。

## 自動跨平台建置

`.github/workflows/build.yml` 會建立以下 release 檔案：

- `FlickrAlbumDownloader-1.0.0-windows-x64.exe`、`windows-x86.exe`、`windows-arm64.exe`。
- 未簽章 macOS fallback 版本：`FlickrAlbumDownloader-1.0.0-macos-x64.app.zip`、`macos-arm64.app.zip`。
- 設定 Apple Developer ID secrets 後的 Apple 公證 macOS 版本：`FlickrAlbumDownloader-1.0.0-macos-x64.dmg`、`macos-arm64.dmg`。
- `FlickrAlbumDownloader-1.0.0-linux-x64.AppImage`、`linux-arm64.AppImage`。

可以在 GitHub Actions 手動執行 `Build desktop apps` 產生 artifacts。推送 `v1.0.0` 這類版本 tag 時，也會自動建立 GitHub Release 並附上執行檔。

Windows 與 Linux arm64 runner 目前屬於 GitHub public preview runner，因此允許失敗，不會阻擋穩定的 x64 / x86 建置。

沒有 Apple Developer ID secrets 時，macOS 會產出 `.app.zip`，避免未簽章 DMG 在掛載前就被 Gatekeeper 阻擋。使用者解壓後仍需要手動允許未簽章 `.app`。請參考 [未簽章 macOS 安裝說明](docs/macos-unsigned-install.zh_TW.md)。

若日後設定 Apple Developer ID 與 App Store Connect API secrets，GitHub Actions 會簽署 `.app`、簽署 `.dmg`、提交 Apple notarization、公證完成後 staple 票據並驗證結果。請參考 [macOS 公證設定](docs/macos-notarization.zh_TW.md)。

Linux 版本會打包成 AppImage。部分 Linux 桌面環境第一次啟動前需要先把 AppImage 標記為可執行。

## macOS / Linux 建置

PyInstaller 的建置結果與作業系統和 CPU 架構相關；請在要發行的相同平台上建置。

```bash
python -m pip install -r requirements.txt -r requirements-build.txt
python tools/generate_icons.py
python -m PyInstaller --windowed --name "Flickr Album Downloader" --icon assets/icon.png --add-data "assets/icon.png:assets" --add-data "assets/icon.ico:assets" flickr_album_downloader.py
```

macOS release 建置會使用 `.icns` 圖示。GitHub Actions 會先把 `assets/icon.png` 轉成 `assets/icon.icns`，再建立 `.app` bundle。

## 開發

執行測試：

```bash
python -m unittest discover -s tests
```

## 授權

本專案自行撰寫的原始碼採用 [MIT License](LICENSE)。

建置出的應用程式可能包含 Python、Tcl/Tk、Pillow、certifi 等第三方 runtime 元件。請參考 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## Flickr API 參考

- Flickr `flickr.photosets.getPhotos`：<https://www.flickr.com/services/api/flickr.photosets.getPhotos.html>
- Flickr URL 格式：<https://www.flickr.com/services/api/misc.urls.html>
