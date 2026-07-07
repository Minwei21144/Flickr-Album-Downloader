import ctypes
import sys
from pathlib import Path

_TCL_DLL_REF = None


def _prepare_tcl_runtime() -> None:
    if sys.platform != "win32":
        return
    global _TCL_DLL_REF

    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    dll_path = base_dir / "tcl86t.dll"
    if not dll_path.exists():
        return
    tcl_dll = ctypes.CDLL(str(dll_path))
    tcl_dll.Tcl_FindExecutable.argtypes = [ctypes.c_wchar_p]
    tcl_dll.Tcl_FindExecutable(str(Path(sys.executable).resolve()))
    _TCL_DLL_REF = tcl_dll


try:
    _prepare_tcl_runtime()
except Exception:
    pass
