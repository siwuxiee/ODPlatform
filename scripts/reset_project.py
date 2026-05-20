import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLATFORM_SRC = REPO_ROOT / "apps" / "platform" / "src"

sys.path.insert(0, str(PLATFORM_SRC))

# 🌟 修改点：导入包含 argparse 逻辑的函数（假设叫 main）
from odp_platform.cli.reset_project import main

if __name__ == "__main__":
    main() # main() 函数会自动读取终端里的 sys.argv，从而抓到 --yes