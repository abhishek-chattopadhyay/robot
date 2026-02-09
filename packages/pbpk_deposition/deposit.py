from __future__ import annotations

import argparse
from pathlib import Path

from pbpk_deposition.base import available_depositors, get_depositor


def main():
    ap = argparse.ArgumentParser(description="Deposit a PBPK RO-Crate using pluggable adapters.")
    ap.add_argument("--platform", required=True, choices=available_depositors())
    ap.add_argument("--crate-dir", required=True, type=str)
    ap.add_argument("--token", required=True, type=str)
    ap.add_argument("--sandbox", action="store_true")
    ap.add_argument("--publish", action="store_true", help="(Zenodo) publish the deposition after upload")
    ap.add_argument("--title", default=None, help="(Zenodo) deposition title override")
    ap.add_argument("--description", default=None, help="(Zenodo) deposition description override")
    ap.add_argument("--dry-run", action="store_true", help="Do not upload; just check inputs")
    args = ap.parse_args()

    crate_dir = Path(args.crate_dir).resolve()
    metadata_path = crate_dir / "ro-crate-metadata.json"

    if not crate_dir.exists():
        raise SystemExit(f"[ERROR] crate dir not found: {crate_dir}")
    if not metadata_path.exists():
        raise SystemExit(f"[ERROR] missing ro-crate-metadata.json in crate dir: {metadata_path}")

    if args.dry_run:
        print("[OK] Dry run: crate dir and metadata exist.")
        return

    depositor_cls = get_depositor(args.platform)
    depositor = depositor_cls()

    res = depositor.deposit(
        crate_dir=crate_dir,
        metadata_path=metadata_path,
        access_token=args.token,
        sandbox=args.sandbox,
        publish=args.publish,
        title=args.title,
        description=args.description,
    )

    if not res.ok:
        print(f"[ERROR] Deposition failed ({res.platform}): {res.message or 'unknown error'}")
        raise SystemExit(1)

    print(f"[OK] Deposited to {res.platform}")
    if res.record_id:
        print(f"Record ID: {res.record_id}")
    if res.doi:
        print(f"DOI: {res.doi}")
    if res.url:
        print(f"URL: {res.url}")


if __name__ == "__main__":
    main()