from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_metadata import (
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_NAME,
    APP_PUBLISHER,
    APP_VERSION,
)


OUTPUT = ROOT / "build" / "version_info.txt"


def version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".")]
    return tuple((parts + [0, 0, 0, 0])[:4])


def main() -> None:
    file_version = version_tuple(APP_VERSION)
    file_version_text = ".".join(str(part) for part in file_version)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={file_version},
    prodvers={file_version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{APP_PUBLISHER}'),
          StringStruct('FileDescription', '{APP_DESCRIPTION}'),
          StringStruct('FileVersion', '{file_version_text}'),
          StringStruct('InternalName', '{APP_NAME}'),
          StringStruct('LegalCopyright', '{APP_COPYRIGHT}'),
          StringStruct('OriginalFilename', '{APP_NAME}.exe'),
          StringStruct('ProductName', '{APP_NAME}'),
          StringStruct('ProductVersion', '{APP_VERSION}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
