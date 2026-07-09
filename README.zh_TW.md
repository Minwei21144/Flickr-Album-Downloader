# Flickr 相簿下載器

[English README](README.md)

![Flickr 相簿下載器畫面截圖](docs/images/app-screenshot.png)

Flickr 相簿下載器是一個簡單的桌面工具，用來把 Flickr 相簿儲存到本機資料夾。它支援公開相簿、Flickr 分享短連結、guest pass 連結，以及你已經能在登入瀏覽器中查看的私人相簿。

目前版本：`1.1.0`

## 下載

請從 [Releases 頁面](https://github.com/Minwei21144/Flickr-Album-Downloader/releases) 下載已打包好的程式。

Release 檔案：

- Windows：`FlickrAlbumDownloader-1.1.0-windows-x64.exe`、`windows-x86.exe`、`windows-arm64.exe`
- macOS 未簽章 app ZIP：`FlickrAlbumDownloader-1.1.0-macos-arm64.app.zip`、`macos-x64.app.zip`
- Linux AppImage：`FlickrAlbumDownloader-1.1.0-linux-x64.AppImage`、`linux-arm64.AppImage`

macOS 版本在未設定 Apple Developer ID 公證資訊時會是未簽章版本。請參考 [未簽章 macOS 安裝說明](docs/macos-unsigned-install.zh_TW.md)。

## 功能

- 支援 Windows、macOS、Linux 桌面環境。
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

## 使用注意事項

- 請只下載你有權存取與保存的相簿和檔案。
- 私人相簿需要從已登入且有權限查看 Flickr 的瀏覽器匯出 cookies。
- 過高的同時下載數可能觸發 Flickr HTTP 429。大型原檔相簿建議先用 `1` 個下載執行緒與恢復模式，再逐步提高。
- 如果 429 持續超過約 10 分鐘，請先等待再試。不要頻繁切換 IP 來規避服務限制。

## Cookie 檔案

私人相簿請從已登入 Flickr 且有權限查看相簿的瀏覽器匯出 Netscape `cookies.txt` 格式。請妥善保管這個檔案，因為它可能允許存取你的 Flickr 登入狀態。

## 資料夾衝突模式

- `resume`：保留資料夾，跳過已存在的檔案。
- `skip`：如果資料夾已存在，跳過整個相簿。
- `overwrite`：刪除並重新建立相簿資料夾。
- `rename`：另存成新資料夾，例如 `相簿名稱 (2)`。

## 命令列

一般使用者建議直接使用打包好的桌面程式。Python 原始碼也支援命令列操作：

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

## 開發

原始碼執行與本機開發建議使用 Python 3.10 或更新版本。

```bash
python -m pip install -r requirements.txt
python flickr_album_downloader.py
python -m unittest discover -s tests
```

Release 建置由 `.github/workflows/build.yml` 處理。Windows 本機建置可使用 `build_windows.ps1`。

## macOS 打包

沒有 Apple Developer ID secrets 時，GitHub Actions 會發布未簽章 `.app.zip`。這可以避免未簽章 DMG 在掛載前就被 Gatekeeper 阻擋，但使用者解壓後仍需要手動允許該 App。請參考 [未簽章 macOS 安裝說明](docs/macos-unsigned-install.zh_TW.md)。

若日後設定 Apple Developer ID 與 App Store Connect API secrets，GitHub Actions 會簽署 `.app`、簽署 `.dmg`、提交 Apple notarization、公證完成後 staple 票據並驗證結果。請參考 [macOS 公證設定](docs/macos-notarization.zh_TW.md)。

## 授權

本專案自行撰寫的原始碼採用 [MIT License](LICENSE)。

建置出的應用程式可能包含 Python、Tcl/Tk、Pillow、certifi 等第三方 runtime 元件。請參考 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## Flickr API 參考

- Flickr `flickr.photosets.getPhotos`：<https://www.flickr.com/services/api/flickr.photosets.getPhotos.html>
- Flickr URL 格式：<https://www.flickr.com/services/api/misc.urls.html>
