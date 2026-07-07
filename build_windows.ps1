param(
    [string]$Python = "python",
    [string]$Name = "Flickr Album Downloader"
)

$ErrorActionPreference = "Stop"

$Prefix = & $Python -c "import sys; print(sys.base_prefix)"
$DllDir = Join-Path $Prefix "DLLs"
$TclDir = Join-Path $Prefix "tcl"

& $Python ".\tools\generate_icons.py"
& $Python ".\tools\generate_windows_version_info.py"

& $Python -m PyInstaller `
    --clean `
    -y `
    --onefile `
    --windowed `
    --name $Name `
    --icon ".\assets\icon.ico" `
    --version-file ".\build\version_info.txt" `
    --additional-hooks-dir ".\pyinstaller_hooks" `
    --runtime-hook ".\pyinstaller_hooks\pyi_rth_tcl_find_executable.py" `
    --hidden-import tkinter `
    --hidden-import tkinter.ttk `
    --hidden-import tkinter.filedialog `
    --hidden-import tkinter.messagebox `
    --add-binary "$DllDir\_tkinter.pyd;." `
    --add-binary "$DllDir\tcl86t.dll;." `
    --add-binary "$DllDir\tk86t.dll;." `
    --add-data "$TclDir\tcl8.6;_tcl_data" `
    --add-data "$TclDir\tk8.6;_tk_data" `
    --add-data "$TclDir\tcl8;tcl8" `
    --add-data ".\assets\icon.ico;assets" `
    --add-data ".\assets\icon.png;assets" `
    ".\flickr_album_downloader.py"

$Version = & $Python -c "from app_metadata import APP_VERSION; print(APP_VERSION)"
$WindowsArch = & $Python -c "import platform; machine=platform.machine().lower(); bits=platform.architecture()[0]; print('windows-arm64' if 'arm' in machine or 'aarch64' in machine else 'windows-x86' if bits == '32bit' else 'windows-x64')"
$ReleaseExe = "FlickrAlbumDownloader-$Version-$WindowsArch.exe"
Copy-Item -LiteralPath (Join-Path "dist" "$Name.exe") -Destination (Join-Path "dist" $ReleaseExe) -Force
