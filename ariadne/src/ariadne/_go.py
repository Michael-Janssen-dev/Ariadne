import subprocess
import sys
from pathlib import Path

_GO_PROGRAMS_DIR = Path(__file__).parent / "go"


def collect(duration: str):
    path = _GO_PROGRAMS_DIR / "collect"
    subprocess.run(
        ["go", "run", path, "--duration", duration],
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
