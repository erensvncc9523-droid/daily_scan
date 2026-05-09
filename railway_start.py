import subprocess
import sys


def main() -> int:
    print("Starting Railway job: daily_scan")
    return subprocess.call([sys.executable, "daily_scan_telegram.py"])


if __name__ == "__main__":
    sys.exit(main())
