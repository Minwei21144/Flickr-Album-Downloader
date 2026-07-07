from __future__ import annotations

import plistlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_metadata import (
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_IDENTIFIER,
    APP_NAME,
    APP_VERSION,
)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: update_macos_info_plist.py <Info.plist>", file=sys.stderr)
        return 2

    plist_path = Path(argv[1])
    data = plistlib.loads(plist_path.read_bytes())
    data.update(
        {
            "CFBundleDisplayName": APP_NAME,
            "CFBundleExecutable": APP_NAME,
            "CFBundleIdentifier": APP_IDENTIFIER,
            "CFBundleName": APP_NAME,
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHumanReadableCopyright": APP_COPYRIGHT,
            "NSPrincipalClass": "NSApplication",
            "NSHighResolutionCapable": True,
            "CFBundleGetInfoString": f"{APP_NAME} {APP_VERSION}, {APP_DESCRIPTION}",
        }
    )
    plist_path.write_bytes(plistlib.dumps(data, sort_keys=False))
    print(plist_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
