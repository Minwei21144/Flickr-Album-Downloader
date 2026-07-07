# Flickr 相簿下載器

[English README](README.md)

Flickr 相簿下載器是一個簡單的桌面與命令列工具，可以把 Flickr 相簿下載到本機資料夾。支援公開相簿、Flickr 分享短網址、guest pass 連結，以及你在瀏覽器登入後可以看到的私人相簿。

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
python -m pip install -r requirements-build.txt
```

打包：

```powershell
.\build_windows.ps1
```

執行檔會輸出到：

```text
dist\FlickrAlbumDownloader.exe
```

這個打包腳本包含 Python 3.14 Windows 環境需要的 Tcl/Tk 自訂 hook。

## macOS / Linux 打包

PyInstaller 需要在目標作業系統與目標架構上打包。例如 Windows x64 要在 Windows x64 打包，macOS ARM 要在 Apple Silicon Mac 打包。

```bash
python -m pip install -r requirements-build.txt
python -m PyInstaller --onefile --windowed --name FlickrAlbumDownloader flickr_album_downloader.py
```

## 開發測試

```bash
python -m unittest discover -s tests
```

## Flickr API 參考

- Flickr `flickr.photosets.getPhotos`: <https://www.flickr.com/services/api/flickr.photosets.getPhotos.html>
- Flickr URL 格式: <https://www.flickr.com/services/api/misc.urls.html>
