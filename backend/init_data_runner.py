import os
from pathlib import Path

import django


def main() -> None:
    # Ensure Django settings are available for standalone execution.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dollshop.settings")
    django.setup()

    init_path = Path(__file__).with_name("init_data.py")

    # Best-effort encoding fallback (some Windows editors/save paths may not be UTF-8).
    try:
        code = init_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        code = init_path.read_text(encoding="gbk")

    # Execute the existing init_data.py as a script.
    globals_dict = {"__name__": "__main__"}
    exec(compile(code, str(init_path), "exec"), globals_dict)


if __name__ == "__main__":
    main()

