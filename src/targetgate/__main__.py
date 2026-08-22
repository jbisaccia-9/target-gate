"""CLI:  python -m targetgate run [fixture|corrupted|nppes]"""
import sys
from .pipeline import run

if __name__ == "__main__":
    source = sys.argv[2] if len(sys.argv) > 2 else (
        sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "run" else "fixture")
    sys.exit(run(source=source))
