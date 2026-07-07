# Flickr 相簿下載器

[English README](README.md)

Flickr 相簿下載器是一個簡單的桌面與命令列工具，可以把 Flickr 相簿下載到本機資料夾。支援公開相簿、Flickr 分享短網址、guest pass 連結，以及你在瀏覽器登入後可以看到的私人相簿。

目前應用程式版本：`1.0.0`。

程式會直接建立相簿資料夾並下載照片/影片，不會再額外壓縮成 zip。檔名會盡量使用 Flickr 網頁上可見的照片標題。

## 功能

- 支援 Windows、macOS、Linux 的 Python 執行環境。
- 圖形介面可切換英文與繁體中文。
- 支援標準相簿網址、分享短網址、guest pass 網址。
- 可匯入 `cookies.txt` 下載已登入帳號可存取的私人相簿。
- 預設下載原檔 / 最大可用尺寸。
- 指定尺寸不存在時，可自動改用最接近尺寸。
- 相簿內若混合照片與影片，會在 Flickr 提供可下載影片網址時一併下載。
- 支援暫停、繼續、停止，以及中斷後恢復進度。
- 可調整同時下載數量。
- 資料夾重複時可選擇恢復、略過、覆蓋或另存新資料夾。
- 內建 Flickr HTTP 429 限流等待與重試。

## 注意事項

- 請只下載你有權存取與保存的相簿和檔案。
- 私人相簿需要從已登入 Flickr、且有權限觀看該相簿的瀏覽器匯出 cookies。
- 太高的同時下載數可能觸發 Flickr HTTP 429。大型原檔相簿建議先用 `1` 線程與恢復模式，再逐步提高。
- 如果 429 持續超過約 10 分鐘，建議稍後再試。請不要反覆更換 IP 來規避服務限制。

## 安裝

建議使用 Python 3.10 或更新版本。

```bash
python -m pip install -r requirements.txt
```

Linux 若 Python 沒有內建 Tkinter，請另外安裝：

```bash
sudo apt install python3-tk
```

## 啟動圖形介面

```bash
python flickr_album_downloader.py
```

貼上 Flickr 相簿網址後，先按「確認」，確認相簿名稱與封面縮圖沒問題，再按「開始下載」。

## 命令列使用

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

私人相簿請從已登入 Flickr 的瀏覽器匯出 Netscape 格式 `cookies.txt`。請妥善保存這個檔案，它可能包含可存取你 Flickr 工作階段的資訊。

## 資料夾處理模式

- `resume`：保留資料夾並略過已存在的檔案。
- `skip`：資料夾已存在時略過整個相簿。
- `overwrite`：刪除並重新建立相簿資料夾。
- `rename`：另存新資料夾，例如 `相簿名稱 (2)`。

## 打包 Windows 執行檔

安裝打包工具：

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
```

打包：

```powershell
.\build_windows.ps1
```

執行檔會輸出到：

```text
dist\Flickr Album Downloader.exe
```

這個打包腳本會產生應用程式圖示，並包含 Python 3.14 Windows 環境需要的 Tcl/Tk 自訂 hook。

## 自動跨平台打包

`.github/workflows/build.yml` 內的 GitHub Actions workflow 會產生下列可發布檔：

- `FlickrAlbumDownloader-1.0.0-windows-x64.exe`、`windows-x86.exe`、`windows-arm64.exe`。
- `FlickrAlbumDownloader-1.0.0-macos-x64.dmg`、`macos-arm64.dmg`。
- `FlickrAlbumDownloader-1.0.0-linux-x64.AppImage`、`linux-arm64.AppImage`。

可以從 GitHub Actions 手動執行 `Build desktop apps` 來產生 artifacts。推送 `v1.0.0` 這類版本 tag 時，也會自動打包並把可執行的發布檔直接附加到 GitHub Release。

Windows 與 Linux arm64 runner 目前屬於 GitHub public preview，因此設定為即使失敗也不阻塞穩定的 x64 / x86 打包。

macOS 版本會打包成可拖曳到 Applications 的 DMG，並進行 ad-hoc signing。若沒有 Apple Developer ID 憑證進行 notarization，部分 macOS 環境第一次開啟時仍可能需要按右鍵選擇「打開」。

Linux 版本會打包成 AppImage。部分 Linux 桌面環境第一次執行下載來的 AppImage 前，仍需要先允許該檔案可執行。

## macOS / Linux 打包

PyInstaller 需要在目標作業系統與目標架構上打包。例如 Windows x64 要在 Windows x64 打包，macOS ARM 要在 Apple Silicon Mac 打包。

```bash
python -m pip install -r requirements.txt -r requirements-build.txt
python tools/generate_icons.py
python -m PyInstaller --windowed --name "Flickr Album Downloader" --icon assets/icon.png --add-data "assets/icon.png:assets" --add-data "assets/icon.ico:assets" flickr_album_downloader.py
```

macOS 發布版需要使用 `.icns` 圖示。GitHub Actions workflow 會先將 `assets/icon.png` 轉成 `assets/icon.icns`，再打包 `.app`。

## 開發測試

```bash
python -m unittest discover -s tests
```

## 授權

本專案自行撰寫的原始碼採用 [MIT License](LICENSE)。

打包後的應用程式可能包含 Python、Tcl/Tk、Pillow、certifi 等第三方 runtime 元件。詳細資訊請見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## Flickr API 參考

- Flickr `flickr.photosets.getPhotos`: <https://www.flickr.com/services/api/flickr.photosets.getPhotos.html>
- Flickr URL 格式: <https://www.flickr.com/services/api/misc.urls.html>
