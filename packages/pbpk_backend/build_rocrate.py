from __future__ import annotations

import argparse
import json
from pathlib import Path

from rocrate_builder import build_rocrate_from_pbpk_metadata


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(
        description="Build a PBPK RO-Crate (ro-crate-metadata.json) from pbpk-metadata.json"
    )
    ap.add_argument("metadata", type=str, help="Path to pbpk-metadata.json (domain payload)")
    ap.add_argument("crate_dir", type=str, help="Output crate directory")
    ap.add_argument(
        "--template",
        type=str,
        default="packages/pbpk-metadata-spec/jsonld/pbpk-core-template.jsonld",
        help="Path to pbpk-core-template.jsonld",
    )
    ap.add_argument(
        "--source-files-dir",
        type=str,
        default=None,
        help="Optional directory containing user-provided files to copy into the crate (same relative paths as artifact_location).",
    )
    args = ap.parse_args()

    md = load_json(Path(args.metadata))

    src_dir = Path(args.source_files_dir).resolve() if args.source_files_dir else None

    res = build_rocrate_from_pbpk_metadata(
        pbpk_metadata=md,
        crate_dir=Path(args.crate_dir),
        template_path=Path(args.template),
        source_files_dir=src_dir,
    )
    print(f"Built RO-Crate metadata: {res.metadata_path}")


if __name__ == "__main__":
    main()