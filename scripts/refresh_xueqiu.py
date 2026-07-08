from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from market_radar.market.collector import collect_and_save


def main() -> None:
    out_path = collect_and_save()
    print(out_path.resolve())


if __name__ == "__main__":
    main()
