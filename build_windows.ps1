param(
    [string]$Python = "python",
    [string]$Name = "FlickrAlbumDownloader"
)

$ErrorActionPreference = "Stop"

$Prefix = & $Python -c "import sys; print(sys.base_prefix)"
$DllDir = Join-Path $Prefix "DLLs"
$TclDir = Join-Path $Prefix "tcl"

& $Python -m PyInstaller `
    --clean `
    -y `
    --onefile `
    --windowed `
    --name $Name `
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
    ".\flickr_album_downloader.py"
