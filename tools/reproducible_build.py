"""Build DNC artifacts with stable timestamps and hash seeding."""

from __future__ import annotations

import argparse
import gzip
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


DEFAULT_SOURCE_DATE_EPOCH = "1785456000"  # 2026-07-31T00:00:00Z


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--source-date-epoch", default=DEFAULT_SOURCE_DATE_EPOCH)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment["SOURCE_DATE_EPOCH"] = args.source_date_epoch
    environment["PYTHONHASHSEED"] = "0"
    command = [
        sys.executable,
        "-m",
        "build",
        "--no-isolation",
        "--outdir",
        str(args.outdir.resolve()),
    ]
    result = subprocess.run(command, env=environment, check=False)
    if result.returncode == 0:
        for archive in args.outdir.glob("*.tar.gz"):
            _normalize_sdist(archive, int(args.source_date_epoch))
    return result.returncode


def _normalize_sdist(archive: Path, timestamp: int) -> None:
    """Rewrite gzip and tar metadata so repeated source builds are identical."""

    with tarfile.open(archive, "r:gz") as source:
        members = [(member, source.extractfile(member)) for member in source.getmembers()]
        with tempfile.NamedTemporaryFile(delete=False, dir=archive.parent) as raw_output:
            temporary = Path(raw_output.name)
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=timestamp) as zipped:
                with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as target:
                    for member, content in members:
                        member.mtime = timestamp
                        member.uid = 0
                        member.gid = 0
                        member.uname = ""
                        member.gname = ""
                        member.pax_headers = {}
                        target.addfile(member, content)
    temporary.replace(archive)


if __name__ == "__main__":
    raise SystemExit(main())
