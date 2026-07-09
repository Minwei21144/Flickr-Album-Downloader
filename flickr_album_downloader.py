#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import concurrent.futures
import email.utils
import html
import http.cookiejar
import io
import json
import mimetypes
import os
import queue
import random
import re
import shutil
import ssl
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from app_metadata import (
    APP_CURRENT_RELEASE_URL,
    APP_IDENTIFIER,
    APP_NAME,
    APP_USER_AGENT,
    APP_VERSION,
)
from update_checker import UpdateCheckResult, check_for_update

_TCL_DLL_REF = None


def prepare_tcl_runtime() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        global _TCL_DLL_REF

        base_dir = Path(getattr(sys, "_MEIPASS", sys.base_prefix)).resolve()
        dll_candidates = (
            base_dir / "tcl86t.dll",
            Path(sys.base_prefix).resolve() / "DLLs" / "tcl86t.dll",
        )
        for dll_path in dll_candidates:
            if not dll_path.exists():
                continue
            tcl_dll = ctypes.CDLL(str(dll_path))
            tcl_dll.Tcl_FindExecutable.argtypes = [ctypes.c_wchar_p]
            tcl_dll.Tcl_FindExecutable(str(Path(sys.executable).resolve()))
            _TCL_DLL_REF = tcl_dll
            break
    except Exception:
        pass


prepare_tcl_runtime()

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from tkinter import ttk
except ImportError:
    tk = None
    ttk = None
    filedialog = None
    messagebox = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


APP_DIR_NAME = "flickr-album-downloader"
API_ENDPOINT = "https://www.flickr.com/services/rest/"
PUBLIC_API_KEY_URLS = [
    "https://www.flickr.com/explore",
    "https://www.flickr.com/photos",
    "https://www.flickr.com/search/",
    "https://www.flickr.com/services/api/",
]
USER_AGENT = APP_USER_AGENT
HTTP_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
HTTP_MAX_RETRIES = 12
HTTP_MAX_RETRY_DELAY = 600
HTML_REQUEST_INTERVAL = 0.7
API_REQUEST_INTERVAL = 0.8
IMAGE_REQUEST_INTERVAL = 6.0
MIN_IMAGE_REQUEST_INTERVAL = 0.25
MAX_DOWNLOAD_WORKERS = 16
RATE_LIMIT_NOTICE = (
    "Flickr 回傳 HTTP 429，表示這個網路出口的下載請求被暫時限流。"
    "程式會先進入緩衝等待並自動重試；請不要提高線程數。"
    "若等待 10 分鐘以上仍持續被擋，建議稍後再試，或改用你有權使用的其他網路出口/IP。"
    "請勿反覆切換 IP 來規避 Flickr 的服務限制。"
)
HIGH_WORKER_NOTICE = (
    "提醒：同時下載數超過 1 時，Flickr 較容易回傳 429。"
    "大型原檔相簿建議先用 1 線程與續傳模式；若要加速，請逐步提高並觀察是否出現限流。"
)
SIZE_EXTRAS = "media,o_dims,original_format,url_sq,url_t,url_s,url_q,url_m,url_n,url_z,url_c,url_l,url_o"
COMMON_RESOLUTION_OPTIONS = [
    ("original", "原檔 / 最大可用"),
    ("4096", "4096px"),
    ("2048", "2048px"),
    ("1600", "1600px"),
    ("1024", "1024px"),
]

COOKIE_LOCK = threading.Lock()
COOKIE_JAR: http.cookiejar.MozillaCookieJar | None = None
COOKIE_FILE_LOADED: str | None = None

DEFAULT_RESOLUTION_OPTIONS = COMMON_RESOLUTION_OPTIONS


def app_root_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def app_asset_path(filename: str) -> Path:
    return app_root_dir() / "assets" / filename


def set_window_icon(root: tk.Tk) -> None:
    icon_ico = app_asset_path("icon.ico")
    icon_png = app_asset_path("icon.png")
    try:
        if sys.platform == "win32" and icon_ico.exists():
            root.iconbitmap(default=str(icon_ico))
            return
    except Exception:
        pass
    try:
        if icon_png.exists():
            icon_photo = tk.PhotoImage(file=str(icon_png))
            root.iconphoto(True, icon_photo)
            root._app_icon_photo = icon_photo
    except Exception:
        pass


CONFLICT_OPTIONS = [
    ("resume", "恢復進度 / 跳過已存在照片"),
    ("skip", "資料夾存在就略過"),
    ("overwrite", "覆蓋原資料夾"),
    ("rename", "另存新資料夾"),
]
CONFLICT_LABEL_TO_VALUE = {label: value for value, label in CONFLICT_OPTIONS}
CONFLICT_VALUE_TO_LABEL = {value: label for value, label in CONFLICT_OPTIONS}
EN_RESOLUTION_OPTIONS = [
    ("original", "Original / largest available"),
    ("4096", "4096px"),
    ("2048", "2048px"),
    ("1600", "1600px"),
    ("1024", "1024px"),
]
EN_CONFLICT_OPTIONS = [
    ("resume", "Resume / skip existing photos"),
    ("skip", "Skip existing folder"),
    ("overwrite", "Overwrite existing folder"),
    ("rename", "Save as new folder"),
]
LANGUAGE_OPTIONS = [("zh", "中文"), ("en", "English")]
LANGUAGE_LABEL_TO_CODE = {label: code for code, label in LANGUAGE_OPTIONS}
LANGUAGE_CODE_TO_LABEL = {code: label for code, label in LANGUAGE_OPTIONS}
APP_LANGUAGE = "zh"

TEXT = {
    "zh": {
        "album_info": "{title}\n照片數：{count} 張\n讀取方式：{mode}\n網址：{url}",
        "album_not_confirmed": "尚未確認相簿。",
        "all_files": "所有檔案",
        "btn_browse": "選擇",
        "btn_confirm": "確認",
        "btn_pause": "暫停",
        "btn_resume": "繼續",
        "btn_start": "開始下載",
        "btn_stop": "停止",
        "cancelled": "下載已取消。",
        "album_code_missing": "找不到相簿代碼。請貼上像 https://www.flickr.com/photos/user/albums/album-id/ 這類 URL。",
        "api_connect_failed": "無法連線到 Flickr API：{reason}",
        "api_http_403": "Flickr API HTTP 錯誤：403。若這是私人相簿，請匯入已登入 Flickr 的 cookies.txt。",
        "api_http_error": "Flickr API HTTP 錯誤：{code}",
        "api_json_error": "Flickr API 回傳的資料無法解析。",
        "api_reported_error": "Flickr API 回報錯誤 {code}: {message}",
        "cli_description": "下載 Flickr 相簿到本機資料夾。",
        "cli_missing": "命令列模式缺少：{items}",
        "cli_tk_missing": "這個 Python 環境沒有 Tkinter，請改用 --cli 命令列模式。",
        "confirm_album_first": "請先確認相簿。",
        "confirm_done": "相簿確認完成，可以開始下載。",
        "confirm_error_info": "相簿確認失敗。",
        "dialog_done": "下載完成：\n{path}",
        "done": "完成。",
        "done_folder": "完成：{path}",
        "error": "錯誤：{message}",
        "fallback_check": "指定尺寸沒有時自動改用最接近尺寸",
        "fetch_album_page": "讀取相簿清單第 {page} 頁...",
        "folder_skip": "資料夾已存在，已略過：{path}",
        "folder_skip_log": "資料夾已存在，依設定略過：{path}",
        "html_mode": "網頁讀取模式",
        "html_no_downloadable": "無法從這個 Flickr 頁面讀到可下載的照片。",
        "help_api_key": "選填：自備 Flickr API Key。",
        "help_cli": "使用命令列模式，不啟動圖形介面。",
        "help_conflict": "資料夾已存在時的處理方式。",
        "help_cookies": "選填：Netscape 格式 cookies.txt，用於已登入 Flickr 的私人相簿。",
        "help_language": "介面語言：zh 或 en。",
        "help_no_fallback": "指定尺寸不存在時直接停止。",
        "help_output": "輸出父資料夾路徑。",
        "help_resolution": "下載解析度，例如 best、original、2048。圖形介面會依相簿自動列出。",
        "help_url": "Flickr 相簿 URL。",
        "help_workers": "同時下載數量，建議 1-16；遇到 429 時請降低。",
        "image_connect_failed": "圖片下載連線失敗：{reason}",
        "image_http_403": "圖片下載 HTTP 錯誤：403。若這是私人照片，請匯入已登入 Flickr 的 cookies.txt。",
        "image_http_error": "圖片下載 HTTP 錯誤：{code}",
        "label_album_url": "相簿 URL",
        "label_conflict": "資料夾處理",
        "label_cookie": "Cookie 檔",
        "label_language": "語言",
        "label_output": "儲存位置",
        "label_resolution": "解析度",
        "label_workers": "同時下載",
        "log_confirm_done": "相簿確認完成。",
        "log_confirm_start": "開始確認相簿。",
        "log_cookie_set": "已設定 Cookie 檔：{path}",
        "log_done": "完成，檔案已儲存：{path}",
        "log_intro": "貼上 Flickr 相簿 URL，先按確認，確認縮圖與相簿名後再開始下載。",
        "log_pause": "已暫停，可調整線程數後按繼續套用。",
        "log_resume": "繼續下載，已套用 {workers} 線程。",
        "log_start_download": "開始下載。",
        "log_stop": "收到停止要求，已開始中止任務。",
        "multi_thread_enabled": "多線程下載已啟用：{workers} 線程，下載請求啟動間隔約 {interval:.2f} 秒。",
        "no_preview": "尚無縮圖",
        "no_preview_available": "無法顯示縮圖",
        "no_downloadable_photo": "這個相簿沒有可下載的照片。",
        "no_success": "沒有任何照片成功下載。",
        "network_request_failed": "網路請求失敗。",
        "parse_url": "解析網址：{url}",
        "photo_no_downloadable_sizes": "照片 {photo_id} 沒有可下載的尺寸。",
        "photo_no_original": "這張照片沒有開放原始檔。",
        "photo_no_sizes": "這張照片沒有可下載的尺寸。",
        "photo_size_progress": "讀取照片尺寸 {done}/{total}",
        "photo_target_missing": "這張照片沒有 {target}px 這個尺寸。",
        "preview_failed": "縮圖讀取失敗：{error}",
        "preview_loading": "讀取中...",
        "public_access_info": "取得 Flickr 公開存取資訊...",
        "rate_limit_notice": "Flickr 回傳 HTTP 429，表示這個網路出口的下載請求被暫時限流。程式會先進入緩衝等待並自動重試；請不要提高線程數。若等待 10 分鐘以上仍持續被擋，建議稍後再試，或改用你有權使用的其他網路出口/IP。請勿反覆切換 IP 來規避 Flickr 的服務限制。",
        "rate_limit_failed": "Flickr 回傳 429 速率限制，已重試 {attempt} 次後仍失敗。請降低同時下載數量後再試。",
        "read_guest_page": "讀取 guest pass 頁面第 {page} 頁...",
        "resolution_wait": "請先確認相簿",
        "retry_wait": "HTTP {code}，等待 {delay:.0f} 秒後重試（第 {attempt}/{max_attempts} 次）",
        "saved_file": "已儲存：{filename}（{label}）",
        "skip_existing_file": "已存在，略過：{filename}",
        "skip_photo": "略過：{title}（{error}）",
        "skipped": "已略過。",
        "skipped_count": "有 {count} 張照片略過。",
        "start_file": "開始下載：{filename}（{label}）",
        "status_canceling": "正在取消...",
        "status_confirm_failed": "確認失敗。",
        "status_confirming": "確認相簿中...",
        "status_continue": "繼續下載...",
        "status_error": "發生錯誤。",
        "status_paused": "已暫停。",
        "status_processing": "處理中...",
        "status_ready": "準備好了。",
        "status_starting": "開始處理...",
        "site_key_failed": "無法取得 Flickr 公開 site key：{detail}",
        "site_key_missing_detail": "已讀取頁面但沒有找到 site key",
        "url_not_flickr_album": "這看起來不像 Flickr 相簿 URL。",
        "url_read_failed": "網址讀取失敗：{reason}",
        "url_read_http_403": "網址讀取 HTTP 錯誤：403。若這是私人或 guest pass 連結，請匯入已登入 Flickr 的 cookies.txt。",
        "url_read_http_error": "網址讀取 HTTP 錯誤：{code}",
        "url_required": "請先貼上 Flickr 相簿 URL。",
        "web_visible_size": "網頁可見尺寸",
        "worker_notice": "提醒：同時下載數超過 1 時，Flickr 較容易回傳 429。大型原檔相簿建議先用 1 線程與續傳模式；若要加速，請逐步提高並觀察是否出現限流。目前設定：{workers} 線程。",
    },
    "en": {
        "album_info": "{title}\nPhotos: {count}\nMode: {mode}\nURL: {url}",
        "album_not_confirmed": "No album confirmed.",
        "all_files": "All files",
        "btn_browse": "Browse",
        "btn_confirm": "Confirm",
        "btn_pause": "Pause",
        "btn_resume": "Resume",
        "btn_start": "Start download",
        "btn_stop": "Stop",
        "cancelled": "Download cancelled.",
        "album_code_missing": "Could not find an album ID. Paste a URL like https://www.flickr.com/photos/user/albums/album-id/.",
        "api_connect_failed": "Could not connect to the Flickr API: {reason}",
        "api_http_403": "Flickr API HTTP error: 403. For private albums, import cookies.txt from a browser that is signed in to Flickr.",
        "api_http_error": "Flickr API HTTP error: {code}",
        "api_json_error": "The Flickr API response could not be parsed.",
        "api_reported_error": "Flickr API returned error {code}: {message}",
        "cli_description": "Download a Flickr album to a local folder.",
        "cli_missing": "CLI mode is missing: {items}",
        "cli_tk_missing": "This Python environment does not have Tkinter. Use --cli instead.",
        "confirm_album_first": "Confirm an album first.",
        "confirm_done": "Album confirmed. You can start downloading.",
        "confirm_error_info": "Album confirmation failed.",
        "dialog_done": "Download complete:\n{path}",
        "done": "Complete.",
        "done_folder": "Complete: {path}",
        "error": "Error: {message}",
        "fallback_check": "Use the nearest available size if selected size is missing",
        "fetch_album_page": "Reading album page {page}...",
        "folder_skip": "Folder already exists, skipped: {path}",
        "folder_skip_log": "Folder already exists, skipped by setting: {path}",
        "html_mode": "HTML mode",
        "html_no_downloadable": "No downloadable photos were found on this Flickr page.",
        "help_api_key": "Optional: your own Flickr API key.",
        "help_cli": "Use command-line mode instead of opening the GUI.",
        "help_conflict": "How to handle an existing album folder.",
        "help_cookies": "Optional: Netscape-format cookies.txt for private Flickr albums from a signed-in browser.",
        "help_language": "Display language: zh or en.",
        "help_no_fallback": "Stop if the selected size is unavailable.",
        "help_output": "Parent output folder.",
        "help_resolution": "Download resolution, such as best, original, or 2048. The GUI lists available options automatically.",
        "help_url": "Flickr album URL.",
        "help_workers": "Parallel download count, recommended 1-16. Lower it if 429 appears.",
        "image_connect_failed": "Image download connection failed: {reason}",
        "image_http_403": "Image download HTTP error: 403. For private photos, import cookies.txt from a browser that is signed in to Flickr.",
        "image_http_error": "Image download HTTP error: {code}",
        "label_album_url": "Album URL",
        "label_conflict": "Folder handling",
        "label_cookie": "Cookie file",
        "label_language": "Language",
        "label_output": "Save to",
        "label_resolution": "Resolution",
        "label_workers": "Parallel",
        "log_confirm_done": "Album confirmed.",
        "log_confirm_start": "Confirming album.",
        "log_cookie_set": "Cookie file set: {path}",
        "log_done": "Complete, files saved to: {path}",
        "log_intro": "Paste a Flickr album URL, confirm the album and cover, then start downloading.",
        "log_pause": "Paused. Adjust the parallel download count, then press Resume to apply.",
        "log_resume": "Resuming with {workers} parallel downloads.",
        "log_start_download": "Download started.",
        "log_stop": "Stop requested. Cancelling tasks.",
        "multi_thread_enabled": "Parallel download enabled: {workers} workers, request start interval about {interval:.2f}s.",
        "no_preview": "No thumbnail",
        "no_preview_available": "Preview unavailable",
        "no_downloadable_photo": "This album has no downloadable photos.",
        "no_success": "No photos were downloaded successfully.",
        "network_request_failed": "Network request failed.",
        "parse_url": "Parsing URL: {url}",
        "photo_no_downloadable_sizes": "Photo {photo_id} has no downloadable sizes.",
        "photo_no_original": "This photo does not expose the original file.",
        "photo_no_sizes": "This photo has no downloadable sizes.",
        "photo_size_progress": "Reading photo sizes {done}/{total}",
        "photo_target_missing": "This photo does not have a {target}px size.",
        "preview_failed": "Preview failed: {error}",
        "preview_loading": "Loading...",
        "public_access_info": "Getting Flickr public access information...",
        "rate_limit_notice": "Flickr returned HTTP 429, which means this network exit is temporarily rate limited. The app will buffer, wait, and retry automatically; do not increase the parallel download count. If it is still blocked after more than 10 minutes, try again later or use another network exit/IP that you are authorized to use. Do not repeatedly switch IPs to bypass Flickr service limits.",
        "rate_limit_failed": "Flickr returned 429 rate limiting and still failed after {attempt} retries. Lower the parallel download count and try again.",
        "read_guest_page": "Reading guest pass page {page}...",
        "resolution_wait": "Confirm an album first",
        "retry_wait": "HTTP {code}; waiting {delay:.0f}s before retry ({attempt}/{max_attempts})",
        "saved_file": "Saved: {filename} ({label})",
        "skip_existing_file": "Already exists, skipped: {filename}",
        "skip_photo": "Skipped: {title} ({error})",
        "skipped": "Skipped.",
        "skipped_count": "{count} photos skipped.",
        "start_file": "Starting: {filename} ({label})",
        "status_canceling": "Cancelling...",
        "status_confirm_failed": "Confirmation failed.",
        "status_confirming": "Confirming album...",
        "status_continue": "Resuming download...",
        "status_error": "An error occurred.",
        "status_paused": "Paused.",
        "status_processing": "Processing...",
        "status_ready": "Ready.",
        "status_starting": "Starting...",
        "site_key_failed": "Could not get Flickr public site key: {detail}",
        "site_key_missing_detail": "Pages were read but no site key was found",
        "url_not_flickr_album": "This does not look like a Flickr album URL.",
        "url_read_failed": "URL read failed: {reason}",
        "url_read_http_403": "URL read HTTP error: 403. For private or guest pass links, import cookies.txt from a browser that is signed in to Flickr.",
        "url_read_http_error": "URL read HTTP error: {code}",
        "url_required": "Paste a Flickr album URL first.",
        "web_visible_size": "Web visible size",
        "worker_notice": "Note: Flickr is more likely to return 429 when parallel downloads exceed 1. For large original-size albums, start with 1 worker and resume mode. If you need more speed, increase gradually and watch for rate limiting. Current setting: {workers} workers.",
    },
}

TEXT["zh"].update(
    {
        "btn_check_updates": "檢查更新",
        "current_version": "目前版本 v{version}",
        "footer_separator": "  |  ",
        "log_open_current_release": "開啟目前版本 Release：{url}",
        "update_already_running": "正在檢查更新，請稍候。",
        "update_check_available": "有新版本可用：v{current} -> v{latest}",
        "update_check_failed": "更新檢查失敗：{error}",
        "update_check_latest": "已是最新版本：v{version}",
        "update_check_start_auto": "正在自動檢查更新。",
        "update_check_start_manual": "正在檢查更新。",
        "update_dialog_available": "GitHub Releases 有新版本可用。\n\n目前版本：v{current}\n最新版本：v{latest}\n\n是否開啟下載頁面？",
        "update_dialog_failed": "無法完成更新檢查。\n\n{error}",
        "update_dialog_latest": "目前已是最新版本。\n\n目前版本：v{current}\n最新版本：v{latest}",
        "update_dialog_title": "檢查更新",
    }
)

TEXT["en"].update(
    {
        "btn_check_updates": "Check for updates",
        "current_version": "Version v{version}",
        "footer_separator": "  |  ",
        "log_open_current_release": "Opening current release: {url}",
        "update_already_running": "An update check is already running.",
        "update_check_available": "Update available: v{current} -> v{latest}",
        "update_check_failed": "Update check failed: {error}",
        "update_check_latest": "You are using the latest version: v{version}",
        "update_check_start_auto": "Checking for updates automatically.",
        "update_check_start_manual": "Checking for updates.",
        "update_dialog_available": "A new version is available on GitHub Releases.\n\nCurrent version: v{current}\nLatest version: v{latest}\n\nOpen the download page?",
        "update_dialog_failed": "The update check could not be completed.\n\n{error}",
        "update_dialog_latest": "You are using the latest version.\n\nCurrent version: v{current}\nLatest version: v{latest}",
        "update_dialog_title": "Check for updates",
    }
)


def normalize_language(language: str | None) -> str:
    return language if language in TEXT else "zh"


def set_app_language(language: str | None) -> str:
    global APP_LANGUAGE
    APP_LANGUAGE = normalize_language(language)
    return APP_LANGUAGE


def tr(key: str, language: str | None = None, **kwargs) -> str:
    lang = normalize_language(language or APP_LANGUAGE)
    template = TEXT.get(lang, {}).get(key) or TEXT["zh"].get(key) or key
    return template.format(**kwargs) if kwargs else template


def language_label(language: str | None) -> str:
    return LANGUAGE_CODE_TO_LABEL.get(normalize_language(language), LANGUAGE_CODE_TO_LABEL["zh"])


def resolution_options_for_language(language: str | None = None) -> list[tuple[str, str]]:
    return EN_RESOLUTION_OPTIONS if normalize_language(language or APP_LANGUAGE) == "en" else COMMON_RESOLUTION_OPTIONS


def conflict_options_for_language(language: str | None = None) -> list[tuple[str, str]]:
    return EN_CONFLICT_OPTIONS if normalize_language(language or APP_LANGUAGE) == "en" else CONFLICT_OPTIONS


def conflict_label_to_value_map(language: str | None = None) -> dict[str, str]:
    return {label: value for value, label in conflict_options_for_language(language)}


def conflict_value_to_label_map(language: str | None = None) -> dict[str, str]:
    return {value: label for value, label in conflict_options_for_language(language)}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".jpe", ".png", ".gif", ".webp", ".tif", ".tiff", ".bmp"}
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


class FlickrAPIError(RuntimeError):
    pass


class DownloadCancelled(RuntimeError):
    pass


class DownloadSkipped(RuntimeError):
    pass


class HostThrottle:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_time: dict[str, float] = {}

    def wait(
        self,
        url: str,
        min_interval: float,
        cancel_event: threading.Event | None = None,
        pause_event: threading.Event | None = None,
    ) -> None:
        host = urllib.parse.urlparse(url).netloc.lower() or "default"
        while True:
            if cancel_event and cancel_event.is_set():
                raise DownloadCancelled(tr("cancelled"))
            wait_if_paused(pause_event, cancel_event)
            now = time.monotonic()
            with self._lock:
                next_time = self._next_time.get(host, 0.0)
                if now >= next_time:
                    self._next_time[host] = now + min_interval
                    return
                delay = next_time - now
            sleep_interruptible(min(delay, 1.0), cancel_event, pause_event)

    def penalize(self, url: str, seconds: float) -> None:
        host = urllib.parse.urlparse(url).netloc.lower() or "default"
        until = time.monotonic() + max(0.0, seconds)
        with self._lock:
            self._next_time[host] = max(self._next_time.get(host, 0.0), until)


HOST_THROTTLE = HostThrottle()


@dataclass(frozen=True)
class AlbumRef:
    user_token: str
    photoset_id: str


@dataclass(frozen=True)
class PhotoItem:
    photo_id: str
    title: str
    sizes: tuple["SizeItem", ...] = ()
    thumbnail_url: str | None = None
    media: str = "photo"


@dataclass(frozen=True)
class SizeItem:
    label: str
    width: int
    height: int
    source: str
    preferred_extension: str | None = None

    @property
    def longest_edge(self) -> int:
        return max(self.width, self.height)

    @property
    def pixel_count(self) -> int:
        return self.width * self.height

    @property
    def is_original(self) -> bool:
        return self.label.lower() == "original"


@dataclass(frozen=True)
class AlbumData:
    title: str
    canonical_url: str
    photos: tuple[PhotoItem, ...]
    resolution_options: tuple[tuple[str, str], ...]
    api_key: str | None = None
    expected_count: int | None = None
    html_only: bool = False
    cover_url: str | None = None

    @property
    def preview_url(self) -> str | None:
        if self.cover_url:
            return self.cover_url
        for photo in self.photos:
            if photo.thumbnail_url:
                return photo.thumbnail_url
            if photo.sizes:
                smallest = min(photo.sizes, key=lambda item: (item.pixel_count, item.longest_edge))
                return smallest.source
        return None


def config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_DIR_NAME / "config.json"


def load_config() -> dict:
    path = config_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def set_cookie_file(cookie_file: str | None) -> None:
    config = load_config()
    if cookie_file:
        config["cookies_file"] = cookie_file
    else:
        config.pop("cookies_file", None)
    save_config(config)
    global COOKIE_JAR, COOKIE_FILE_LOADED
    with COOKIE_LOCK:
        COOKIE_JAR = None
        COOKIE_FILE_LOADED = None


def configured_cookie_file() -> str | None:
    value = load_config().get("cookies_file")
    return str(value) if value else None


def load_cookie_jar() -> http.cookiejar.MozillaCookieJar | None:
    cookie_file = configured_cookie_file()
    if not cookie_file:
        return None
    path = Path(cookie_file).expanduser()
    if not path.exists():
        return None

    global COOKIE_JAR, COOKIE_FILE_LOADED
    with COOKIE_LOCK:
        if COOKIE_JAR is not None and COOKIE_FILE_LOADED == str(path):
            return COOKIE_JAR
        jar = http.cookiejar.MozillaCookieJar(str(path))
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except (OSError, http.cookiejar.LoadError):
            return None
        COOKIE_JAR = jar
        COOKIE_FILE_LOADED = str(path)
        return COOKIE_JAR


def apply_cookie_header(request: urllib.request.Request) -> None:
    jar = load_cookie_jar()
    if jar is not None:
        jar.add_cookie_header(request)


def normalize_url(url: str) -> str:
    text = url.strip()
    if not text:
        raise ValueError(tr("url_required"))
    parsed = urllib.parse.urlparse(text)
    if not parsed.scheme:
        text = "https://" + text
    return text


def parse_album_url(album_url: str) -> AlbumRef:
    text = album_url.strip()
    if not text:
        raise ValueError(tr("url_required"))

    parsed = urllib.parse.urlparse(normalize_url(text))

    host = parsed.netloc.lower()
    if "flickr.com" not in host:
        raise ValueError(tr("url_not_flickr_album"))

    path = urllib.parse.unquote(parsed.path)
    match = re.search(r"/photos/([^/]+)/(?:albums|sets)/(\d+)", path)
    if not match:
        raise ValueError(tr("album_code_missing"))

    return AlbumRef(user_token=match.group(1), photoset_id=match.group(2))


def find_album_ref_in_text(text: str) -> AlbumRef | None:
    decoded = urllib.parse.unquote(text.replace("\\/", "/"))
    patterns = [
        r"https?://(?:www\.)?flickr\.com/photos/([^/\"'<>]+)/(?:albums|sets)/(\d+)",
        r"/photos/([^/\"'<>]+)/(?:albums|sets)/(\d+)",
        r'"albumId"\s*:\s*"(\d+)".{0,200}?"nsid"\s*:\s*"([^"]+)"',
        r'"nsid"\s*:\s*"([^"]+)".{0,200}?"albumId"\s*:\s*"(\d+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, decoded, re.DOTALL)
        if not match:
            continue
        if "albumId" in pattern and pattern.startswith('"albumId"'):
            return AlbumRef(user_token=match.group(2), photoset_id=match.group(1))
        return AlbumRef(user_token=match.group(1), photoset_id=match.group(2))
    return None


def read_url(url: str, timeout: int = 30) -> tuple[str, str, str | None]:
    request = urllib.request.Request(
        normalize_url(url),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with open_with_retries(request, timeout=timeout, min_interval=HTML_REQUEST_INTERVAL) as response:
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type")
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise FlickrAPIError(tr("url_read_http_403")) from exc
        raise FlickrAPIError(tr("url_read_http_error", code=exc.code)) from exc
    except urllib.error.URLError as exc:
        raise FlickrAPIError(tr("url_read_failed", reason=exc.reason)) from exc
    return final_url, body, content_type


def resolve_album_ref(album_url: str) -> tuple[AlbumRef | None, str, str | None]:
    url = normalize_url(album_url)
    try:
        return parse_album_url(url), url, None
    except ValueError:
        pass

    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if "flickr.com" not in host and "flic.kr" not in host:
        raise ValueError(tr("url_not_flickr_album"))

    final_url, page, _ = read_url(url)
    for candidate in (final_url, page):
        try:
            return parse_album_url(candidate), final_url, page
        except ValueError:
            found = find_album_ref_in_text(candidate)
            if found:
                canonical = f"https://www.flickr.com/photos/{found.user_token}/albums/{found.photoset_id}/"
                return found, canonical, page
    return None, final_url, page


def normalize_album_owner_url(user_token: str) -> str:
    encoded = urllib.parse.quote(user_token.strip("/"))
    return f"https://www.flickr.com/photos/{encoded}/"


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def wait_if_paused(pause_event: threading.Event | None, cancel_event: threading.Event | None) -> None:
    while pause_event and pause_event.is_set():
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelled(tr("cancelled"))
        time.sleep(0.15)


def sleep_interruptible(
    seconds: float,
    cancel_event: threading.Event | None = None,
    pause_event: threading.Event | None = None,
) -> None:
    end = time.monotonic() + max(0.0, seconds)
    while True:
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelled(tr("cancelled"))
        wait_if_paused(pause_event, cancel_event)
        remaining = end - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 0.5))


def retry_delay_from_http_error(exc: urllib.error.HTTPError, attempt: int) -> float:
    retry_after = exc.headers.get("Retry-After") if exc.headers else None
    if retry_after:
        retry_after = retry_after.strip()
        if retry_after.isdigit():
            return min(float(retry_after), HTTP_MAX_RETRY_DELAY)
        try:
            parsed = email.utils.parsedate_to_datetime(retry_after)
            return min(max(0.0, parsed.timestamp() - time.time()), HTTP_MAX_RETRY_DELAY)
        except (TypeError, ValueError, OverflowError):
            pass
    if exc.code == 429:
        base = 30 * attempt
    else:
        base = 2 ** max(0, attempt - 1)
    jitter = random.uniform(0.0, 0.75)
    return min(base + jitter, HTTP_MAX_RETRY_DELAY)


def worker_limit_notice(workers: int) -> str:
    return tr("worker_notice", workers=workers)


def download_interval_for_workers(workers: int) -> float:
    worker_count = max(1, workers)
    if worker_count <= 1:
        return IMAGE_REQUEST_INTERVAL
    return max(MIN_IMAGE_REQUEST_INTERVAL, IMAGE_REQUEST_INTERVAL / worker_count)


def open_with_retries(
    request: urllib.request.Request,
    timeout: int,
    min_interval: float,
    cancel_event: threading.Event | None = None,
    pause_event: threading.Event | None = None,
    retry_log: Callable[[str], None] | None = None,
):
    url = request.full_url
    last_error: urllib.error.HTTPError | None = None
    for attempt in range(1, HTTP_MAX_RETRIES + 1):
        HOST_THROTTLE.wait(url, min_interval, cancel_event=cancel_event, pause_event=pause_event)
        try:
            apply_cookie_header(request)
            return urllib.request.urlopen(request, timeout=timeout, context=ssl_context())
        except urllib.error.HTTPError as exc:
            if exc.code not in HTTP_RETRY_STATUS_CODES or attempt >= HTTP_MAX_RETRIES:
                if exc.code == 429:
                    raise FlickrAPIError(tr("rate_limit_failed", attempt=attempt)) from exc
                raise
            last_error = exc
            delay = retry_delay_from_http_error(exc, attempt)
            if retry_log:
                if exc.code == 429 and attempt == 1:
                    retry_log(tr("rate_limit_notice"))
                retry_log(tr("retry_wait", code=exc.code, delay=delay, attempt=attempt, max_attempts=HTTP_MAX_RETRIES))
            HOST_THROTTLE.penalize(url, delay)
            sleep_interruptible(delay, cancel_event, pause_event)
        except urllib.error.URLError:
            raise
    if last_error:
        raise last_error
    raise FlickrAPIError(tr("network_request_failed"))


def fetch_public_api_key() -> str:
    patterns = [
        r'\.flickr\.api\.site_key\s*=\s*"([^"]+)"',
        r'"site_key"\s*:\s*"([^"]+)"',
        r'"api_key"\s*:\s*"([^"]+)"',
    ]
    errors: list[str] = []
    for url in PUBLIC_API_KEY_URLS:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with open_with_retries(request, timeout=30, min_interval=HTML_REQUEST_INTERVAL) as response:
                page = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            errors.append(f"{url}: HTTP {exc.code}")
            continue
        except urllib.error.URLError as exc:
            errors.append(f"{url}: {exc.reason}")
            continue

        for pattern in patterns:
            match = re.search(pattern, page)
            if match:
                return match.group(1)

    detail = "; ".join(errors) if errors else tr("site_key_missing_detail")
    raise FlickrAPIError(tr("site_key_failed", detail=detail))


def api_request(api_key: str, method: str, **params) -> dict:
    query = {
        "method": method,
        "api_key": api_key,
        "format": "json",
        "nojsoncallback": "1",
    }
    query.update({key: value for key, value in params.items() if value is not None})
    url = API_ENDPOINT + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with open_with_retries(request, timeout=30, min_interval=API_REQUEST_INTERVAL) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise FlickrAPIError(tr("api_http_403")) from exc
        raise FlickrAPIError(tr("api_http_error", code=exc.code)) from exc
    except urllib.error.URLError as exc:
        raise FlickrAPIError(tr("api_connect_failed", reason=exc.reason)) from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise FlickrAPIError(tr("api_json_error")) from exc

    if data.get("stat") != "ok":
        code = data.get("code", "unknown")
        message = data.get("message", "Unknown error")
        raise FlickrAPIError(tr("api_reported_error", code=code, message=message))
    return data


def resolve_user_id(api_key: str, user_token: str) -> str:
    if re.fullmatch(r"\d+@N\d+", user_token, re.IGNORECASE):
        return user_token
    data = api_request(
        api_key,
        "flickr.urls.lookupUser",
        url=normalize_album_owner_url(user_token),
    )
    return data["user"]["id"]


def photoset_cover_url(photoset: dict) -> str | None:
    photo_id = photoset.get("primary") or photoset.get("primary_photo_id")
    secret = photoset.get("secret") or photoset.get("primary_photo_secret")
    server = photoset.get("server") or photoset.get("primary_photo_server")
    if photo_id and secret and server:
        return f"https://live.staticflickr.com/{server}/{photo_id}_{secret}_q.jpg"
    return None


def fetch_album_info(api_key: str, photoset_id: str, user_id: str) -> tuple[str, int | None, str | None]:
    data = api_request(
        api_key,
        "flickr.photosets.getInfo",
        photoset_id=photoset_id,
        user_id=user_id,
    )
    photoset = data["photoset"]
    title = photoset.get("title", {})
    if isinstance(title, dict):
        album_title = title.get("_content") or photoset_id
    else:
        album_title = str(title or photoset_id)
    count = photoset.get("count_photos") or photoset.get("photos")
    try:
        count_value = int(count)
    except (TypeError, ValueError):
        count_value = None
    return album_title, count_value, photoset_cover_url(photoset)


def extension_from_format(format_value: str | None, media: str = "photo") -> str | None:
    if not format_value:
        return ".mp4" if media == "video" else None
    clean = str(format_value).strip().lower().lstrip(".")
    mapping = {
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "png": ".png",
        "gif": ".gif",
        "webp": ".webp",
        "tif": ".tif",
        "tiff": ".tiff",
        "bmp": ".bmp",
        "mp4": ".mp4",
        "mov": ".mov",
        "m4v": ".m4v",
    }
    return mapping.get(clean, f".{clean}" if clean else None)


def size_item_from_photo_extra(item: dict, key: str, label: str, edge: int | None, media: str, preferred_extension: str | None) -> SizeItem | None:
    source = item.get(f"url_{key}")
    if not source:
        return None
    try:
        if key == "o":
            width = int(item.get("width_o") or 0)
            height = int(item.get("height_o") or 0)
        else:
            width = int(edge or 0)
            height = int(edge or 0)
    except ValueError:
        width = 0
        height = 0
    return SizeItem(label=label, width=width, height=height, source=str(source), preferred_extension=preferred_extension)


def sizes_from_photo_extra(item: dict) -> tuple[SizeItem, ...]:
    media = str(item.get("media") or "photo")
    original_ext = None
    if media != "video":
        original_ext = extension_from_format(item.get("originalformat") or item.get("original_format"), media=media)
    specs = [
        ("o", "Original", None),
        ("l", "Large 1024", 1024),
        ("c", "Medium 800", 800),
        ("z", "Medium 640", 640),
        ("m", "Medium 500", 500),
        ("n", "Small 320", 320),
        ("s", "Small 240", 240),
        ("q", "Square 150", 150),
        ("t", "Thumbnail 100", 100),
        ("sq", "Square 75", 75),
    ]
    sizes: list[SizeItem] = []
    for key, label, edge in specs:
        ext = original_ext if key == "o" else None
        size = size_item_from_photo_extra(item, key, label, edge, media, ext)
        if size:
            sizes.append(size)
    return tuple(sizes)


def is_video_size(size: SizeItem) -> bool:
    label = size.label.strip().lower()
    source = size.source.lower()
    return bool(re.fullmatch(r"\d+p", label)) or "/play/" in source or ".mp4" in source


def video_sizes_from_get_sizes(items: list[SizeItem]) -> list[SizeItem]:
    video_items: list[SizeItem] = []
    for item in items:
        if is_video_size(item):
            video_items.append(
                SizeItem(
                    label=item.label,
                    width=item.width,
                    height=item.height,
                    source=item.source,
                    preferred_extension=".mp4",
                )
            )
    if video_items:
        return sorted(video_items, key=lambda item: (item.longest_edge, item.pixel_count), reverse=True)
    return items


def fetch_album_photos(
    api_key: str,
    photoset_id: str,
    user_id: str,
    progress: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> list[PhotoItem]:
    photos: list[PhotoItem] = []
    page = 1
    pages = 1

    while page <= pages:
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelled(tr("cancelled"))
        if progress:
            progress(tr("fetch_album_page", page=page))
        data = api_request(
            api_key,
            "flickr.photosets.getPhotos",
            photoset_id=photoset_id,
            user_id=user_id,
            per_page=500,
            page=page,
            media="all",
            extras=SIZE_EXTRAS,
        )
        photoset = data["photoset"]
        pages = int(photoset.get("pages", 1))
        for item in photoset.get("photo", []):
            photo_id = str(item["id"])
            title = str(item.get("title") or photo_id)
            media = str(item.get("media") or "photo")
            if media == "video":
                sizes = tuple(fetch_photo_sizes(api_key, photo_id, media=media))
            else:
                sizes = sizes_from_photo_extra(item)
            thumb = None
            for key in ("url_q", "url_s", "url_t", "url_sq", "url_m"):
                if item.get(key):
                    thumb = str(item[key])
                    break
            photos.append(
                PhotoItem(
                    photo_id=photo_id,
                    title=title,
                    sizes=sizes,
                    thumbnail_url=thumb,
                    media=media,
                )
            )
        page += 1

    return photos


def fetch_photo_sizes(api_key: str, photo_id: str, media: str = "photo") -> list[SizeItem]:
    data = api_request(api_key, "flickr.photos.getSizes", photo_id=photo_id)
    items: list[SizeItem] = []
    for item in data["sizes"].get("size", []):
        source = item.get("source")
        if not source:
            continue
        try:
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
        except ValueError:
            width = 0
            height = 0
        items.append(
            SizeItem(
                label=str(item.get("label") or ""),
                width=width,
                height=height,
                source=str(source),
            )
        )
    if not items:
        raise FlickrAPIError(tr("photo_no_downloadable_sizes", photo_id=photo_id))
    if media == "video":
        return video_sizes_from_get_sizes(items)
    return items


def hydrate_photo_sizes(
    api_key: str,
    photos: Iterable[PhotoItem],
    workers: int = 1,
    progress: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> list[PhotoItem]:
    photo_list = list(photos)
    total = len(photo_list)
    if not photo_list:
        return []

    def load(photo: PhotoItem) -> PhotoItem:
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelled(tr("cancelled"))
        sizes = tuple(fetch_photo_sizes(api_key, photo.photo_id, media=photo.media))
        thumb = None
        if sizes:
            thumb = min(sizes, key=lambda item: (item.longest_edge, item.pixel_count)).source
        return PhotoItem(photo.photo_id, photo.title, sizes=sizes, thumbnail_url=thumb, media=photo.media)

    results: dict[str, PhotoItem] = {}
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, total))) as executor:
        future_to_photo = {executor.submit(load, photo): photo for photo in photo_list}
        for future in concurrent.futures.as_completed(future_to_photo):
            if cancel_event and cancel_event.is_set():
                for pending in future_to_photo:
                    pending.cancel()
                raise DownloadCancelled(tr("cancelled"))
            photo = future_to_photo[future]
            try:
                results[photo.photo_id] = future.result()
            except DownloadCancelled:
                raise
            except Exception:
                results[photo.photo_id] = photo
            done += 1
            if progress:
                progress(done, total, tr("photo_size_progress", done=done, total=total))

    return [results.get(photo.photo_id, photo) for photo in photo_list]


def build_resolution_options(photos: Iterable[PhotoItem]) -> tuple[tuple[str, str], ...]:
    return tuple(COMMON_RESOLUTION_OPTIONS)


def choose_size(sizes: Iterable[SizeItem], resolution: str, fallback: bool = True) -> SizeItem:
    available = [item for item in sizes if item.source]
    if not available:
        raise FlickrAPIError(tr("photo_no_sizes"))

    if resolution == "best":
        originals = [item for item in available if item.is_original]
        if originals:
            return max(originals, key=lambda item: item.pixel_count)
        return max(available, key=lambda item: (item.pixel_count, item.longest_edge))

    if resolution == "original":
        originals = [item for item in available if item.is_original]
        if originals:
            return max(originals, key=lambda item: item.pixel_count)
        if not fallback:
            raise FlickrAPIError(tr("photo_no_original"))
        return max(available, key=lambda item: (item.pixel_count, item.longest_edge))

    target = int(resolution)
    regular_sizes = [item for item in available if not item.is_original] or available
    exact = [item for item in regular_sizes if item.longest_edge == target]
    if exact:
        return max(exact, key=lambda item: item.pixel_count)

    if not fallback:
        raise FlickrAPIError(tr("photo_target_missing", target=target))

    smaller = [item for item in regular_sizes if item.longest_edge <= target]
    if smaller:
        return max(smaller, key=lambda item: (item.longest_edge, item.pixel_count))

    return min(regular_sizes, key=lambda item: (item.longest_edge, item.pixel_count))


def extension_from_url(url: str, content_type: str | None = None) -> str:
    path = urllib.parse.urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return ".jpg" if suffix in {".jpeg", ".jpe"} else suffix
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return ".jpg" if guessed in {".jpeg", ".jpe"} else guessed
    return ".jpg"


def media_request_headers(source_url: str) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,video/*,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.flickr.com/",
        "Connection": "close",
    }
    if source_url.lower().endswith((".mp4", ".mov", ".m4v")):
        headers["Accept"] = "video/*,image/*,*/*;q=0.8"
    return headers


def sanitize_filename(
    name: str,
    extension: str,
    max_length: int = 180,
    preserve_image_suffix: bool = True,
) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()
    clean = re.sub(r"\s+", " ", clean)
    clean = clean.rstrip(" .")
    if not clean:
        clean = "untitled"

    stem = clean
    current_suffix = Path(stem).suffix.lower()
    if preserve_image_suffix and current_suffix in IMAGE_EXTENSIONS:
        extension = current_suffix
        stem = stem[: -len(current_suffix)].rstrip(" .") or "untitled"

    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"

    extension = extension if extension.startswith(".") else f".{extension}"
    limit = max_length - len(extension)
    if len(stem) > limit:
        stem = stem[:limit].rstrip(" .") or "untitled"
    return f"{stem}{extension}"


def sanitize_folder_name(name: str, max_length: int = 180) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()
    clean = re.sub(r"\s+", " ", clean)
    clean = clean.rstrip(" .")
    if not clean:
        clean = "flickr_album"
    if clean.upper() in WINDOWS_RESERVED_NAMES:
        clean = f"_{clean}"
    if len(clean) > max_length:
        clean = clean[:max_length].rstrip(" .") or "flickr_album"
    return clean


def unique_filename(filename: str, used: set[str]) -> str:
    if filename not in used:
        used.add(filename)
        return filename

    path = Path(filename)
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = f"{stem} ({counter}){suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


def default_output_dir() -> Path:
    downloads = Path.home() / "Downloads"
    return downloads if downloads.exists() else Path.home()


def absolute_flickr_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://www.flickr.com" + url
    return url


def parse_html_album_title(page: str, fallback: str) -> str:
    patterns = [
        r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        r'<meta\s+name=["\']twitter:title["\']\s+content=["\']([^"\']+)["\']',
        r"<title>(.*?)</title>",
    ]
    for pattern in patterns:
        match = re.search(pattern, page, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        title = html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()
        title = re.sub(r"\s*\|\s*Flickr\s*$", "", title, flags=re.IGNORECASE).strip()
        if title:
            return title
    return fallback


def parse_html_expected_count(page: str) -> int | None:
    patterns = [
        r'"totalCount"\s*:\s*(\d+)',
        r'"count_photos"\s*:\s*"?(\d+)"?',
        r"(\d+)\s+photos",
    ]
    for pattern in patterns:
        match = re.search(pattern, page, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
    return None


def parse_html_cover_url(page: str) -> str | None:
    patterns = [
        r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, page, re.IGNORECASE | re.DOTALL)
        if match:
            return html.unescape(absolute_flickr_url(match.group(1)))
    return None


def parse_html_photo_cards(page: str) -> list[PhotoItem]:
    photos: list[PhotoItem] = []
    seen: set[str] = set()
    card_pattern = re.compile(r'<div\s+class="view photo-card-view\b[^>]+data-view-signature="[^"]*__id_(\d+)__[^"]*"', re.DOTALL)
    matches = list(card_pattern.finditer(page))
    for index, match in enumerate(matches):
        photo_id = match.group(1)
        if photo_id in seen:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(page)
        body = page[match.start() : end]
        image_match = re.search(r'src=["\']([^"\']*live\.staticflickr\.com[^"\']+)["\']', body)
        title_match = re.search(r'<a\s+class=["\']title["\'][^>]*>(.*?)</a>', body, re.DOTALL)
        if not title_match:
            title_match = re.search(r'title=["\']([^"\']+)["\']', body)
        if not image_match:
            continue

        source = html.unescape(absolute_flickr_url(image_match.group(1)))
        title = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip() if title_match else photo_id
        try:
            width = int((re.search(r'width=["\'](\d+)["\']', body) or [None, "0"])[1])
            height = int((re.search(r'height=["\'](\d+)["\']', body) or [None, "0"])[1])
        except ValueError:
            width = 0
            height = 0
        size = SizeItem(tr("web_visible_size"), width, height, source)
        photos.append(PhotoItem(photo_id, title or photo_id, sizes=(size,), thumbnail_url=source))
        seen.add(photo_id)
    return photos


def album_page_url(canonical_url: str, page: int) -> str:
    base = canonical_url.split("?", 1)[0].rstrip("/")
    query = urllib.parse.urlparse(canonical_url).query
    if page <= 1:
        path = base + "/"
    else:
        path = f"{base}/page{page}/"
    return path + (f"?{query}" if query else "")


def fetch_html_album(
    canonical_url: str,
    initial_page: str | None,
    fallback_title: str,
    log: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> AlbumData:
    pages: list[str] = []
    if initial_page:
        pages.append(initial_page)
    else:
        _, page, _ = read_url(canonical_url)
        pages.append(page)

    title = parse_html_album_title(pages[0], fallback_title)
    expected_count = parse_html_expected_count(pages[0])
    cover_url = parse_html_cover_url(pages[0])
    all_photos: list[PhotoItem] = []
    seen: set[str] = set()

    page_number = 1
    while True:
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelled(tr("cancelled"))
        if page_number > len(pages):
            try:
                if log:
                    log(tr("read_guest_page", page=page_number))
                _, page, _ = read_url(album_page_url(canonical_url, page_number))
            except FlickrAPIError:
                break
        else:
            page = pages[page_number - 1]

        new_count = 0
        for photo in parse_html_photo_cards(page):
            if photo.photo_id in seen:
                continue
            seen.add(photo.photo_id)
            all_photos.append(photo)
            new_count += 1

        if expected_count is not None and len(all_photos) >= expected_count:
            break
        if new_count == 0:
            break
        if new_count < 50 and page_number > 1:
            break
        page_number += 1

    if not all_photos:
        raise FlickrAPIError(tr("html_no_downloadable"))

    return AlbumData(
        title=title,
        canonical_url=canonical_url,
        photos=tuple(all_photos),
        resolution_options=build_resolution_options(all_photos),
        expected_count=expected_count or len(all_photos),
        html_only=True,
        cover_url=cover_url,
    )


def load_public_api_key(log: Callable[[str], None] | None = None) -> str:
    cached = load_config().get("public_api_key")
    if cached:
        return cached
    if log:
        log(tr("public_access_info"))
    api_key = fetch_public_api_key()
    config = load_config()
    config["public_api_key"] = api_key
    save_config(config)
    return api_key


def prepare_album(
    album_url: str,
    api_key: str | None = None,
    log: Callable[[str], None] | None = None,
    progress: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> AlbumData:
    album_ref, canonical_url, initial_page = resolve_album_ref(album_url)
    if log:
        log(tr("parse_url", url=canonical_url))

    if album_ref is None:
        return fetch_html_album(canonical_url, initial_page, APP_NAME, log=log, cancel_event=cancel_event)

    provided_api_key = bool(api_key)
    api_key = api_key or load_public_api_key(log)
    try:
        user_id = resolve_user_id(api_key, album_ref.user_token)
    except FlickrAPIError as exc:
        if provided_api_key or "Invalid API Key" not in str(exc):
            raise
        config = load_config()
        config.pop("public_api_key", None)
        save_config(config)
        api_key = load_public_api_key(log)
        user_id = resolve_user_id(api_key, album_ref.user_token)

    try:
        album_title, expected_count, cover_url = fetch_album_info(api_key, album_ref.photoset_id, user_id)
        photos = fetch_album_photos(api_key, album_ref.photoset_id, user_id, progress=log, cancel_event=cancel_event)
        return AlbumData(
            title=album_title,
            canonical_url=f"https://www.flickr.com/photos/{album_ref.user_token}/albums/{album_ref.photoset_id}/",
            photos=tuple(photos),
            resolution_options=build_resolution_options(photos),
            api_key=api_key,
            expected_count=expected_count or len(photos),
            html_only=False,
            cover_url=cover_url,
        )
    except FlickrAPIError:
        if initial_page is None:
            _, initial_page, _ = read_url(canonical_url)
        return fetch_html_album(canonical_url, initial_page, album_ref.photoset_id, log=log, cancel_event=cancel_event)


def download_album_to_folder(
    api_key: str | None,
    album_url: str,
    output_dir: Path,
    resolution: str,
    fallback: bool = True,
    workers: int = 1,
    conflict_mode: str = "resume",
    progress: Callable[[int, int, str], None] | None = None,
    log: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    pause_event: threading.Event | None = None,
) -> Path:
    album = prepare_album(album_url, api_key=api_key, log=log, progress=progress, cancel_event=cancel_event)
    return download_prepared_album_to_folder(
        album,
        output_dir=output_dir,
        resolution=resolution,
        fallback=fallback,
        workers=workers,
        conflict_mode=conflict_mode,
        progress=progress,
        log=log,
        cancel_event=cancel_event,
        pause_event=pause_event,
    )


def download_to_file(
    source_url: str,
    target_path: Path,
    cancel_event: threading.Event | None = None,
    pause_event: threading.Event | None = None,
    log: Callable[[str], None] | None = None,
    min_interval: float = IMAGE_REQUEST_INTERVAL,
) -> str | None:
    request = urllib.request.Request(source_url, headers=media_request_headers(source_url))
    try:
        with open_with_retries(
            request,
            timeout=90,
            min_interval=min_interval,
            cancel_event=cancel_event,
            pause_event=pause_event,
            retry_log=log,
        ) as response:
            content_type = response.headers.get("Content-Type")
            with target_path.open("wb") as output:
                while True:
                    if cancel_event and cancel_event.is_set():
                        raise DownloadCancelled(tr("cancelled"))
                    wait_if_paused(pause_event, cancel_event)
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    output.write(chunk)
            return content_type
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise FlickrAPIError(tr("image_http_403")) from exc
        raise FlickrAPIError(tr("image_http_error", code=exc.code)) from exc
    except urllib.error.URLError as exc:
        raise FlickrAPIError(tr("image_connect_failed", reason=exc.reason)) from exc


def resolve_album_dir(base_dir: Path, album_title: str, conflict_mode: str) -> tuple[Path, bool]:
    target = base_dir / sanitize_folder_name(album_title)
    if not target.exists():
        return target, True
    if conflict_mode == "skip":
        return target, False
    if conflict_mode == "overwrite":
        shutil.rmtree(target)
        return target, True
    if conflict_mode == "rename":
        counter = 2
        while True:
            candidate = base_dir / f"{sanitize_folder_name(album_title)} ({counter})"
            if not candidate.exists():
                return candidate, True
            counter += 1
    return target, True


def planned_downloads(album: AlbumData, resolution: str, fallback: bool) -> list[tuple[PhotoItem, SizeItem, str]]:
    used_names: set[str] = set()
    plan: list[tuple[PhotoItem, SizeItem, str]] = []
    for photo in album.photos:
        selected = choose_size(photo.sizes, resolution, fallback=fallback)
        ext = selected.preferred_extension or extension_from_url(selected.source)
        filename = unique_filename(sanitize_filename(photo.title, ext), used_names)
        plan.append((photo, selected, filename))
    return plan


def download_prepared_album_to_folder(
    album: AlbumData,
    output_dir: Path,
    resolution: str,
    fallback: bool = True,
    workers: int = 1,
    worker_count_getter: Callable[[], int] | None = None,
    conflict_mode: str = "resume",
    progress: Callable[[int, int, str], None] | None = None,
    log: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    pause_event: threading.Event | None = None,
) -> Path:
    if not album.photos:
        raise FlickrAPIError(tr("no_downloadable_photo"))

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    album_dir, should_download = resolve_album_dir(output_dir, album.title, conflict_mode)
    if not should_download:
        if log:
            log(tr("folder_skip_log", path=album_dir))
        raise DownloadSkipped(tr("folder_skip", path=album_dir))
    album_dir.mkdir(parents=True, exist_ok=True)

    plan = planned_downloads(album, resolution, fallback)
    total = len(plan)
    last_logged_worker_count: int | None = None

    def current_worker_count() -> int:
        value = worker_count_getter() if worker_count_getter else workers
        try:
            requested = int(value)
        except (TypeError, ValueError):
            requested = workers
        return max(1, min(MAX_DOWNLOAD_WORKERS, total, requested))

    def current_download_interval() -> float:
        return download_interval_for_workers(current_worker_count())

    def log_worker_count_if_changed() -> None:
        nonlocal last_logged_worker_count
        worker_count = current_worker_count()
        if worker_count == last_logged_worker_count:
            return
        last_logged_worker_count = worker_count
        if log and worker_count > 1:
            log(tr("multi_thread_enabled", workers=worker_count, interval=current_download_interval()))
    log_worker_count_if_changed()
    done_count = 0
    downloaded_count = 0
    success_count = 0
    skipped: list[str] = []
    manifest_path = album_dir / ".flickr_download_manifest.json"

    def one(item: tuple[PhotoItem, SizeItem, str]) -> tuple[str, str]:
        photo, selected, filename = item
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelled(tr("cancelled"))
        wait_if_paused(pause_event, cancel_event)
        target_file = album_dir / filename
        if conflict_mode == "resume" and target_file.exists() and target_file.stat().st_size > 0:
            return "skipped", filename
        temp_file = album_dir / f".{filename}.{photo.photo_id}.part"
        try:
            item_log = (lambda message: log(f"{filename}: {message}")) if log else None
            if log:
                log(tr("start_file", filename=filename, label=selected.label or selected.longest_edge))
            content_type = download_to_file(
                selected.source,
                temp_file,
                cancel_event=cancel_event,
                pause_event=pause_event,
                log=item_log,
                min_interval=current_download_interval(),
            )
            final_ext = selected.preferred_extension or extension_from_url(selected.source, content_type)
            if Path(filename).suffix.lower() != final_ext.lower():
                filename = str(Path(filename).with_suffix(final_ext))
                target_file = album_dir / filename
            os.replace(temp_file, target_file)
        except Exception:
            temp_file.unlink(missing_ok=True)
            raise
        return "downloaded", filename

    next_index = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_DOWNLOAD_WORKERS, total)) as executor:
        future_to_item: dict[concurrent.futures.Future, tuple[PhotoItem, SizeItem, str]] = {}

        def submit_available() -> None:
            nonlocal next_index
            if pause_event and pause_event.is_set():
                return
            log_worker_count_if_changed()
            while next_index < total and len(future_to_item) < current_worker_count():
                item = plan[next_index]
                next_index += 1
                future_to_item[executor.submit(one, item)] = item

        submit_available()
        while future_to_item or next_index < total:
            if cancel_event and cancel_event.is_set():
                for pending in future_to_item:
                    pending.cancel()
                raise DownloadCancelled(tr("cancelled"))

            if not future_to_item:
                sleep_interruptible(0.2, cancel_event, pause_event)
                submit_available()
                continue

            done_futures, _ = concurrent.futures.wait(
                future_to_item,
                timeout=0.2,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            if not done_futures:
                submit_available()
                continue

            for future in done_futures:
                photo, selected, filename = future_to_item.pop(future)
                try:
                    status, final_name = future.result()
                    if status == "downloaded":
                        downloaded_count += 1
                        success_count += 1
                        message = tr("saved_file", filename=final_name, label=selected.label or selected.longest_edge)
                    else:
                        success_count += 1
                        message = tr("skip_existing_file", filename=final_name)
                except DownloadCancelled:
                    raise
                except Exception as exc:
                    skipped.append(f"{photo.title}: {exc}")
                    message = tr("skip_photo", title=photo.title, error=exc)
                    if log:
                        log(message)
                done_count += 1
                if progress:
                    progress(done_count, total, message)

            submit_available()

    manifest_path.unlink(missing_ok=True)

    if success_count == 0:
        raise FlickrAPIError(tr("no_success"))

    if log:
        if skipped:
            log(tr("skipped_count", count=len(skipped)))
        log(tr("done_folder", path=album_dir))
    return album_dir


class DownloaderApp:
    def __init__(self, root: tk.Tk, initial_language: str | None = None):
        self.root = root
        self.root.title(APP_NAME)
        set_window_icon(self.root)
        self.root.geometry("900x760")
        self.root.minsize(820, 680)

        self.config = load_config()
        self.language_code = set_app_language(initial_language or self.config.get("language", "zh"))
        self.events: queue.Queue[tuple] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.pause_event = threading.Event()
        self.worker_count_lock = threading.Lock()
        self.active_worker_count = 1
        self.album_data: AlbumData | None = None
        self.preview_photo = None
        self.update_check_in_progress = False

        self.language_var = tk.StringVar(value=language_label(self.language_code))
        self.album_url_var = tk.StringVar(value="")
        self.resolution_options = tuple(resolution_options_for_language(self.language_code))
        self.resolution_label_to_value = {label: value for value, label in self.resolution_options}
        self.resolution_var = tk.StringVar(value=self._t("resolution_wait"))
        self.output_var = tk.StringVar(value=self.config.get("last_output_dir", str(default_output_dir())))
        self.cookies_var = tk.StringVar(value=self.config.get("cookies_file", ""))
        self.fallback_var = tk.BooleanVar(value=self.config.get("fallback", True))
        self.thread_count_var = tk.IntVar(value=int(self.config.get("workers", 1)))
        self.active_worker_count = max(1, min(MAX_DOWNLOAD_WORKERS, int(self.thread_count_var.get() or 1)))
        self.conflict_label_to_value = conflict_label_to_value_map(self.language_code)
        self.conflict_value_to_label = conflict_value_to_label_map(self.language_code)
        self.conflict_var = tk.StringVar(
            value=self.conflict_value_to_label.get(self.config.get("conflict_mode", "resume"), conflict_options_for_language(self.language_code)[0][1])
        )
        self.status_var = tk.StringVar(value=self._t("status_ready"))
        self.album_info_var = tk.StringVar(value=self._t("album_not_confirmed"))

        self._build_ui()
        self.root.after(100, self._poll_events)
        self.root.after(800, lambda: self._start_update_check(manual=False))

    def _t(self, key: str, **kwargs) -> str:
        return tr(key, self.language_code, **kwargs)

    def _build_ui(self) -> None:
        padding = {"padx": 14, "pady": 8}
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        form = ttk.Frame(main)
        form.pack(fill="x", **padding)
        form.columnconfigure(1, weight=1)

        self.album_url_label = ttk.Label(form, text=self._t("label_album_url"))
        self.album_url_label.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(form, textvariable=self.album_url_var).grid(row=0, column=1, sticky="ew", pady=6)
        self.confirm_button = ttk.Button(form, text=self._t("btn_confirm"), command=self._confirm_album)
        self.confirm_button.grid(row=0, column=2, padx=(8, 0), pady=6)

        self.resolution_label = ttk.Label(form, text=self._t("label_resolution"))
        self.resolution_label.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        resolution_row = ttk.Frame(form)
        resolution_row.grid(row=1, column=1, columnspan=2, sticky="w", pady=6)
        self.resolution_combo = ttk.Combobox(
            resolution_row,
            textvariable=self.resolution_var,
            values=[self._t("resolution_wait")],
            state="disabled",
            width=22,
        )
        self.resolution_combo.pack(side="left")
        self.fallback_check = ttk.Checkbutton(
            resolution_row,
            text=self._t("fallback_check"),
            variable=self.fallback_var,
        )
        self.fallback_check.pack(side="left", padx=(14, 0))

        self.output_label = ttk.Label(form, text=self._t("label_output"))
        self.output_label.grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(form, textvariable=self.output_var).grid(row=2, column=1, sticky="ew", pady=6)
        self.output_button = ttk.Button(form, text=self._t("btn_browse"), command=self._choose_output)
        self.output_button.grid(row=2, column=2, padx=(8, 0), pady=6)

        self.cookie_label = ttk.Label(form, text=self._t("label_cookie"))
        self.cookie_label.grid(row=3, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(form, textvariable=self.cookies_var).grid(row=3, column=1, sticky="ew", pady=6)
        self.cookies_button = ttk.Button(form, text=self._t("btn_browse"), command=self._choose_cookies)
        self.cookies_button.grid(row=3, column=2, padx=(8, 0), pady=6)

        self.workers_label = ttk.Label(form, text=self._t("label_workers"))
        self.workers_label.grid(row=4, column=0, sticky="w", padx=(0, 10), pady=6)
        options_row = ttk.Frame(form)
        options_row.grid(row=4, column=1, columnspan=2, sticky="w", pady=6)
        self.thread_spinbox = ttk.Spinbox(options_row, from_=1, to=16, textvariable=self.thread_count_var, width=8)
        self.thread_spinbox.pack(side="left")
        self.conflict_label = ttk.Label(options_row, text=self._t("label_conflict"))
        self.conflict_label.pack(side="left", padx=(22, 8))
        self.conflict_combo = ttk.Combobox(
            options_row,
            textvariable=self.conflict_var,
            values=[label for _, label in conflict_options_for_language(self.language_code)],
            state="readonly",
            width=28,
        )
        self.conflict_combo.pack(side="left")

        self.language_label = ttk.Label(form, text=self._t("label_language"))
        self.language_label.grid(row=5, column=0, sticky="w", padx=(0, 10), pady=6)
        self.language_combo = ttk.Combobox(
            form,
            textvariable=self.language_var,
            values=[label for _, label in LANGUAGE_OPTIONS],
            state="readonly",
            width=22,
        )
        self.language_combo.grid(row=5, column=1, sticky="w", pady=6)
        self.language_combo.bind("<<ComboboxSelected>>", self._change_language)

        controls = ttk.Frame(main)
        controls.pack(fill="x", **padding)
        self.start_button = ttk.Button(controls, text=self._t("btn_start"), command=self._start_download, state="disabled")
        self.start_button.pack(side="left")
        self.pause_button = ttk.Button(controls, text=self._t("btn_pause"), command=self._toggle_pause, state="disabled")
        self.pause_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(controls, text=self._t("btn_stop"), command=self._stop_download, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(controls, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=(14, 0))

        ttk.Label(main, textvariable=self.status_var).pack(fill="x", padx=14)

        preview_frame = ttk.Frame(main)
        preview_frame.pack(fill="x", padx=14, pady=(4, 8))
        preview_frame.columnconfigure(1, weight=1)
        self.preview_label = ttk.Label(preview_frame, text=self._t("no_preview"), width=24, anchor="center")
        self.preview_label.grid(row=0, column=0, sticky="nw", padx=(0, 12))
        ttk.Label(preview_frame, textvariable=self.album_info_var, wraplength=640, justify="left").grid(
            row=0, column=1, sticky="nw"
        )

        log_frame = ttk.Frame(main)
        log_frame.pack(fill="both", expand=True, padx=14, pady=(8, 14))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=14, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

        ttk.Style(self.root).configure("Link.TLabel", foreground="#0563c1")
        footer = ttk.Frame(main)
        footer.pack(fill="x", padx=14, pady=(0, 10))
        footer.columnconfigure(0, weight=1)
        footer_info = ttk.Frame(footer)
        footer_info.grid(row=0, column=1, sticky="e")

        self.footer_app_name_label = ttk.Label(footer_info, text=APP_NAME)
        self.footer_app_name_label.pack(side="left")
        ttk.Label(footer_info, text=self._t("footer_separator")).pack(side="left")
        self.current_version_link = ttk.Label(
            footer_info,
            text=self._t("current_version", version=APP_VERSION),
            style="Link.TLabel",
            cursor="hand2",
        )
        self.current_version_link.pack(side="left")
        self.current_version_link.bind("<Button-1>", self._open_current_release)
        ttk.Label(footer_info, text=self._t("footer_separator")).pack(side="left")
        self.check_updates_link = ttk.Label(
            footer_info,
            text=self._t("btn_check_updates"),
            style="Link.TLabel",
            cursor="hand2",
        )
        self.check_updates_link.pack(side="left")
        self.check_updates_link.bind("<Button-1>", lambda _event: self._start_update_check(manual=True))

        self._log(self._t("log_intro"))

    def _current_resolution_value(self) -> str:
        return self.resolution_label_to_value.get(self.resolution_var.get(), self.config.get("resolution", "original"))

    def _current_conflict_value(self) -> str:
        return self.conflict_label_to_value.get(self.conflict_var.get(), self.config.get("conflict_mode", "resume"))

    def _set_album_info_text(self) -> None:
        if not self.album_data:
            self.album_info_var.set(self._t("album_not_confirmed"))
            return
        mode = self._t("html_mode") if self.album_data.html_only else "API"
        self.album_info_var.set(
            self._t(
                "album_info",
                title=self.album_data.title,
                count=len(self.album_data.photos),
                mode=mode,
                url=self.album_data.canonical_url,
            )
        )

    def _change_language(self, _event=None) -> None:
        code = LANGUAGE_LABEL_TO_CODE.get(self.language_var.get(), "zh")
        self.language_code = set_app_language(code)
        self.language_var.set(language_label(self.language_code))
        self.config["language"] = self.language_code
        save_config(self.config)
        self._apply_language()

    def _apply_language(self) -> None:
        resolution_value = self._current_resolution_value()
        conflict_value = self._current_conflict_value()

        self.album_url_label.configure(text=self._t("label_album_url"))
        self.confirm_button.configure(text=self._t("btn_confirm"))
        self.resolution_label.configure(text=self._t("label_resolution"))
        self.fallback_check.configure(text=self._t("fallback_check"))
        self.output_label.configure(text=self._t("label_output"))
        self.output_button.configure(text=self._t("btn_browse"))
        self.cookie_label.configure(text=self._t("label_cookie"))
        self.cookies_button.configure(text=self._t("btn_browse"))
        self.workers_label.configure(text=self._t("label_workers"))
        self.conflict_label.configure(text=self._t("label_conflict"))
        self.language_label.configure(text=self._t("label_language"))
        self.start_button.configure(text=self._t("btn_start"))
        self.pause_button.configure(text=self._t("btn_resume") if self.pause_event.is_set() else self._t("btn_pause"))
        self.stop_button.configure(text=self._t("btn_stop"))
        self.current_version_link.configure(text=self._t("current_version", version=APP_VERSION))
        self.check_updates_link.configure(text=self._t("btn_check_updates"))

        self.resolution_options = tuple(resolution_options_for_language(self.language_code))
        self.resolution_label_to_value = {label: value for value, label in self.resolution_options}
        if self.album_data:
            labels = [label for _, label in self.resolution_options]
            self.resolution_combo.configure(values=labels)
            self.resolution_var.set(next((label for value, label in self.resolution_options if value == resolution_value), labels[0]))
        else:
            self.resolution_combo.configure(values=[self._t("resolution_wait")])
            self.resolution_var.set(self._t("resolution_wait"))

        self.conflict_label_to_value = conflict_label_to_value_map(self.language_code)
        self.conflict_value_to_label = conflict_value_to_label_map(self.language_code)
        conflict_labels = [label for _, label in conflict_options_for_language(self.language_code)]
        self.conflict_combo.configure(values=conflict_labels)
        self.conflict_var.set(self.conflict_value_to_label.get(conflict_value, conflict_labels[0]))

        if not self.preview_photo:
            self.preview_label.configure(text=self._t("no_preview") if not self.album_data else self._t("no_preview_available"))
        self._set_album_info_text()

    def _choose_output(self) -> None:
        initial = Path(self.output_var.get()).expanduser()
        dirname = filedialog.askdirectory(
            title=self._t("label_output"),
            initialdir=str(initial if initial.exists() else Path.home()),
        )
        if dirname:
            self.output_var.set(dirname)

    def _choose_cookies(self) -> None:
        initial = Path(self.cookies_var.get()).expanduser() if self.cookies_var.get() else Path.home()
        filename = filedialog.askopenfilename(
            title=self._t("label_cookie"),
            initialdir=str(initial.parent if initial.parent.exists() else Path.home()),
            filetypes=[("cookies.txt", "*.txt"), (self._t("all_files"), "*.*")],
        )
        if filename:
            self.cookies_var.set(filename)
            set_cookie_file(filename)
            self._log(self._t("log_cookie_set", path=filename))

    def _open_current_release(self, _event=None) -> None:
        self._log(self._t("log_open_current_release", url=APP_CURRENT_RELEASE_URL))
        webbrowser.open(APP_CURRENT_RELEASE_URL)

    def _start_update_check(self, manual: bool) -> None:
        if self.update_check_in_progress:
            if manual:
                self._log(self._t("update_already_running"))
                messagebox.showinfo(self._t("update_dialog_title"), self._t("update_already_running"))
            return
        self.update_check_in_progress = True
        self.check_updates_link.configure(cursor="arrow")
        self._log(self._t("update_check_start_manual" if manual else "update_check_start_auto"))
        threading.Thread(target=self._update_check_worker, args=(manual,), daemon=True).start()

    def _update_check_worker(self, manual: bool) -> None:
        result = check_for_update(current_version=APP_VERSION)
        self.events.put(("update_check_done", manual, result))

    def _finish_update_check(self, manual: bool, result: UpdateCheckResult) -> None:
        self.update_check_in_progress = False
        self.check_updates_link.configure(cursor="hand2")

        if result.error:
            self._log(self._t("update_check_failed", error=result.error))
            if manual:
                messagebox.showerror(
                    self._t("update_dialog_title"),
                    self._t("update_dialog_failed", error=result.error),
                )
            return

        latest_version = result.latest_version or result.current_version
        if result.is_update_available:
            self._log(self._t("update_check_available", current=result.current_version, latest=latest_version))
            if messagebox.askyesno(
                self._t("update_dialog_title"),
                self._t("update_dialog_available", current=result.current_version, latest=latest_version),
            ):
                webbrowser.open(result.release_url)
            return

        self._log(self._t("update_check_latest", version=result.current_version))
        if manual:
            messagebox.showinfo(
                self._t("update_dialog_title"),
                self._t("update_dialog_latest", current=result.current_version, latest=latest_version),
            )

    def _read_thread_count(self) -> int:
        try:
            value = int(self.thread_count_var.get() or 1)
        except (tk.TclError, ValueError):
            value = 1
        return max(1, min(MAX_DOWNLOAD_WORKERS, value))

    def _set_active_worker_count_from_ui(self) -> int:
        value = self._read_thread_count()
        with self.worker_count_lock:
            self.active_worker_count = value
        return value

    def _current_active_worker_count(self) -> int:
        with self.worker_count_lock:
            return self.active_worker_count

    def _set_thread_control_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.thread_spinbox.configure(state=state)

    def _set_busy(self, busy: bool, task: str = "") -> None:
        self.confirm_button.configure(state="disabled" if busy else "normal")
        if busy:
            self.start_button.configure(state="disabled")
            self.status_var.set(task or self._t("status_processing"))
        else:
            self.start_button.configure(state="normal" if self.album_data else "disabled")

    def _confirm_album(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        album_url = self.album_url_var.get().strip()
        if not album_url:
            messagebox.showerror(APP_NAME, self._t("url_required"))
            return
        cookie_file = self.cookies_var.get().strip()
        set_cookie_file(cookie_file if cookie_file else None)

        self.album_data = None
        self.preview_photo = None
        self.preview_label.configure(image="", text=self._t("preview_loading"))
        self.album_info_var.set(self._t("status_confirming"))
        self.progress.configure(value=0)
        self._set_busy(True, self._t("status_confirming"))
        self._log(self._t("log_confirm_start"))
        self.cancel_event.clear()
        self.pause_event.clear()
        self.worker = threading.Thread(target=self._confirm_worker, args=(album_url,), daemon=True)
        self.worker.start()

    def _confirm_worker(self, album_url: str) -> None:
        def log(message: str) -> None:
            self.events.put(("log", message))

        def progress(done: int, total: int, message: str) -> None:
            self.events.put(("progress", done, total, message))

        try:
            album = prepare_album(album_url, log=log, progress=progress, cancel_event=self.cancel_event)
            preview_bytes = None
            if album.preview_url:
                try:
                    request = urllib.request.Request(album.preview_url, headers={"User-Agent": USER_AGENT})
                    with open_with_retries(request, timeout=30, min_interval=IMAGE_REQUEST_INTERVAL) as response:
                        preview_bytes = response.read()
                except Exception as exc:
                    log(tr("preview_failed", error=exc))
            self.events.put(("confirm_done", album, preview_bytes))
        except DownloadCancelled as exc:
            self.events.put(("cancelled", str(exc)))
        except Exception as exc:
            self.events.put(("confirm_error", str(exc)))

    def _start_download(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.album_data:
            messagebox.showerror(APP_NAME, self._t("confirm_album_first"))
            return

        output_dir = Path(self.output_var.get().strip() or str(default_output_dir()))
        resolution = self.resolution_label_to_value.get(self.resolution_var.get(), "best")
        fallback = self.fallback_var.get()
        workers = self._set_active_worker_count_from_ui()
        conflict_mode = self.conflict_label_to_value.get(self.conflict_var.get(), "resume")
        cookie_file = self.cookies_var.get().strip()
        set_cookie_file(cookie_file if cookie_file else None)

        self.config.update(
            {
                "resolution": resolution,
                "fallback": fallback,
                "last_output_dir": str(output_dir),
                "workers": workers,
                "conflict_mode": conflict_mode,
                "cookies_file": cookie_file,
            }
        )
        save_config(self.config)

        self.cancel_event.clear()
        self.pause_event.clear()
        self.progress.configure(value=0)
        self.status_var.set(self._t("status_starting"))
        self.start_button.configure(state="disabled")
        self.confirm_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text=self._t("btn_pause"))
        self.stop_button.configure(state="normal")
        self._log(self._t("log_start_download"))

        self._set_thread_control_enabled(False)

        if workers > 1:
            self._log(worker_limit_notice(workers))

        self.worker = threading.Thread(
            target=self._download_worker,
            args=(self.album_data, output_dir, resolution, fallback, workers, conflict_mode),
            daemon=True,
        )
        self.worker.start()

    def _toggle_pause(self) -> None:
        if self.pause_event.is_set():
            workers = self._set_active_worker_count_from_ui()
            self.config["workers"] = workers
            save_config(self.config)
            self.pause_event.clear()
            self._set_thread_control_enabled(False)
            self.pause_button.configure(text=self._t("btn_pause"))
            self.status_var.set(self._t("status_continue"))
            self._log(self._t("log_resume", workers=workers))
            if workers > 1:
                self._log(worker_limit_notice(workers))
        else:
            self.pause_event.set()
            self._set_thread_control_enabled(True)
            self.pause_button.configure(text=self._t("btn_resume"))
            self.status_var.set(self._t("status_paused"))
            self._log(self._t("log_pause"))

    def _stop_download(self) -> None:
        self.cancel_event.set()
        self.pause_event.clear()
        self.status_var.set(self._t("status_canceling"))
        self._log(self._t("log_stop"))
        self.pause_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self._set_thread_control_enabled(True)

    def _download_worker(
        self,
        album: AlbumData,
        output_dir: Path,
        resolution: str,
        fallback: bool,
        workers: int,
        conflict_mode: str,
    ) -> None:
        def progress(done: int, total: int, message: str) -> None:
            self.events.put(("progress", done, total, message))

        def log(message: str) -> None:
            self.events.put(("log", message))

        try:
            result = download_prepared_album_to_folder(
                album,
                output_dir=output_dir,
                resolution=resolution,
                fallback=fallback,
                workers=workers,
                worker_count_getter=self._current_active_worker_count,
                conflict_mode=conflict_mode,
                progress=progress,
                log=log,
                cancel_event=self.cancel_event,
                pause_event=self.pause_event,
            )
        except DownloadCancelled as exc:
            self.events.put(("cancelled", str(exc)))
        except DownloadSkipped as exc:
            self.events.put(("skipped", str(exc)))
        except Exception as exc:
            self.events.put(("error", str(exc)))
        else:
            self.events.put(("done", str(result)))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "log":
                    self._log(event[1])
                elif kind == "update_check_done":
                    _, manual, result = event
                    self._finish_update_check(manual, result)
                elif kind == "progress":
                    _, done, total, message = event
                    value = 0 if total == 0 else round(done / total * 100, 2)
                    self.progress.configure(value=value)
                    self.status_var.set(message)
                    self._log(message)
                elif kind == "confirm_done":
                    _, album, preview_bytes = event
                    self._finish_busy()
                    self.album_data = album
                    self.resolution_options = tuple(resolution_options_for_language(self.language_code))
                    self.resolution_label_to_value = {label: value for value, label in self.resolution_options}
                    labels = [label for _, label in self.resolution_options]
                    self.resolution_combo.configure(values=labels, state="readonly")
                    saved_resolution = self.config.get("resolution", "original")
                    selected_label = next(
                        (label for value, label in self.resolution_options if value == saved_resolution),
                        labels[0],
                    )
                    self.resolution_var.set(selected_label)
                    self._set_album_info_text()
                    self._show_preview(preview_bytes)
                    self.status_var.set(self._t("confirm_done"))
                    self._log(self._t("log_confirm_done"))
                    self.start_button.configure(state="normal")
                elif kind == "confirm_error":
                    self._finish_busy()
                    self.album_info_var.set(self._t("confirm_error_info"))
                    self.preview_label.configure(image="", text=self._t("no_preview_available"))
                    self.status_var.set(self._t("status_confirm_failed"))
                    self._log(self._t("error", message=event[1]))
                    messagebox.showerror(APP_NAME, event[1])
                elif kind == "done":
                    self._finish_download()
                    path = event[1]
                    self.progress.configure(value=100)
                    self.status_var.set(self._t("done"))
                    self._log(self._t("log_done", path=path))
                    messagebox.showinfo(APP_NAME, self._t("dialog_done", path=path))
                elif kind == "skipped":
                    self._finish_download()
                    self.status_var.set(self._t("skipped"))
                    self._log(event[1])
                    messagebox.showinfo(APP_NAME, event[1])
                elif kind == "cancelled":
                    self._finish_download()
                    self.status_var.set(self._t("cancelled"))
                    self._log(event[1])
                elif kind == "error":
                    self._finish_download()
                    self.status_var.set(self._t("status_error"))
                    self._log(self._t("error", message=event[1]))
                    messagebox.showerror(APP_NAME, event[1])
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_events)

    def _finish_busy(self) -> None:
        self.confirm_button.configure(state="normal")

    def _finish_download(self) -> None:
        self.confirm_button.configure(state="normal")
        self.start_button.configure(state="normal" if self.album_data else "disabled")
        self.pause_button.configure(state="disabled", text=self._t("btn_pause"))
        self.stop_button.configure(state="disabled")
        self._set_thread_control_enabled(True)
        self.pause_event.clear()

    def _show_preview(self, preview_bytes: bytes | None) -> None:
        if not preview_bytes or Image is None or ImageTk is None:
            self.preview_label.configure(image="", text=self._t("no_preview_available"))
            return
        try:
            image = Image.open(io.BytesIO(preview_bytes))
            image.thumbnail((190, 140))
            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self.preview_photo, text="")
        except Exception:
            self.preview_label.configure(image="", text=self._t("no_preview_available"))

    def _log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def run_cli(args: argparse.Namespace) -> int:
    set_app_language(args.language or "zh")
    cancel_event = threading.Event()
    if args.cookies:
        set_cookie_file(args.cookies)

    def log(message: str) -> None:
        print(message)

    def progress(done: int, total: int, message: str) -> None:
        percent = 0 if total == 0 else done / total * 100
        print(f"[{percent:6.2f}%] {message}")

    if args.workers > 1:
        log(worker_limit_notice(args.workers))

    try:
        result = download_album_to_folder(
            api_key=args.api_key or None,
            album_url=args.url,
            output_dir=Path(args.output),
            resolution=args.resolution,
            fallback=not args.no_fallback,
            workers=args.workers,
            conflict_mode=args.conflict,
            progress=progress,
            log=log,
            cancel_event=cancel_event,
        )
    except KeyboardInterrupt:
        cancel_event.set()
        print(tr("cancelled"), file=sys.stderr)
        return 130
    except Exception as exc:
        print(tr("error", message=exc), file=sys.stderr)
        return 1

    print(tr("done_folder", path=result))
    return 0


def language_from_argv(argv: list[str]) -> str:
    for index, arg in enumerate(argv):
        if arg == "--language" and index + 1 < len(argv):
            return normalize_language(argv[index + 1])
        if arg.startswith("--language="):
            return normalize_language(arg.split("=", 1)[1])
    return normalize_language(os.environ.get("FLICKR_DOWNLOADER_LANG") or "zh")


def parse_args(argv: list[str]) -> argparse.Namespace:
    help_language = language_from_argv(argv)
    parser = argparse.ArgumentParser(description=tr("cli_description", help_language))
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument("--cli", action="store_true", help=tr("help_cli", help_language))
    parser.add_argument("--api-key", default=os.environ.get("FLICKR_API_KEY", ""), help=tr("help_api_key", help_language))
    parser.add_argument("--cookies", help=tr("help_cookies", help_language))
    parser.add_argument(
        "--language",
        choices=[code for code, _ in LANGUAGE_OPTIONS],
        default=os.environ.get("FLICKR_DOWNLOADER_LANG", ""),
        help=tr("help_language", help_language),
    )
    parser.add_argument("--url", help=tr("help_url", help_language))
    parser.add_argument("--output", help=tr("help_output", help_language))
    parser.add_argument(
        "--resolution",
        default="original",
        help=tr("help_resolution", help_language),
    )
    parser.add_argument("--workers", type=int, default=1, help=tr("help_workers", help_language))
    parser.add_argument(
        "--conflict",
        choices=[value for value, _ in CONFLICT_OPTIONS],
        default="resume",
        help=tr("help_conflict", help_language),
    )
    parser.add_argument("--no-fallback", action="store_true", help=tr("help_no_fallback", help_language))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    set_app_language(args.language or "zh")
    if args.cli:
        missing = []
        if not args.url:
            missing.append("--url")
        if not args.output:
            missing.append("--output")
        if missing:
            print(tr("cli_missing", items=", ".join(missing)), file=sys.stderr)
            return 2
        return run_cli(args)

    if tk is None:
        print(tr("cli_tk_missing"), file=sys.stderr)
        return 2

    if sys.platform == "win32":
        try:
            from ctypes import windll

            windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_IDENTIFIER)
        except Exception:
            pass

    root = tk.Tk()
    try:
        if sys.platform == "win32":
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    DownloaderApp(root, initial_language=args.language or None)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
