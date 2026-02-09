from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base import DepositionResult, register


def _zip_dir(crate_dir: Path) -> Path:
    crate_dir = crate_dir.resolve()
    if not crate_dir.exists():
        raise FileNotFoundError(crate_dir)
    tmpdir = Path(tempfile.mkdtemp(prefix="pbpk_zenodo_"))
    zip_base = tmpdir / "ro-crate"
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", root_dir=str(crate_dir)))
    return zip_path


def _http_json(method: str, url: str, token: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Zenodo HTTPError {e.code} for {url}: {msg}") from e
    except URLError as e:
        raise RuntimeError(f"Zenodo URLError for {url}: {e}") from e


def _http_upload_put(url: str, token: str, filepath: Path) -> None:
    data = filepath.read_bytes()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }
    req = Request(url, data=data, method="PUT", headers=headers)
    try:
        with urlopen(req) as resp:
            resp.read()
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Zenodo upload HTTPError {e.code} for {url}: {msg}") from e
    except URLError as e:
        raise RuntimeError(f"Zenodo upload URLError for {url}: {e}") from e


@register("zenodo")
class ZenodoDepositor:
    """
    Minimal Zenodo depositor for RO-Crates.

    Environment overrides (optional):
    - ZENODO_BASE_URL (default: https://zenodo.org)
    - ZENODO_SANDBOX_BASE_URL (default: https://sandbox.zenodo.org)
    """

    def deposit(
        self,
        *,
        crate_dir: Path,
        metadata_path: Path,
        access_token: str,
        sandbox: bool = False,
        publish: bool = False,
        title: Optional[str] = None,
        description: Optional[str] = None,
        creators: Optional[list[dict]] = None,
        **kwargs: Any,
    ) -> DepositionResult:
        base = os.environ.get(
            "ZENODO_SANDBOX_BASE_URL" if sandbox else "ZENODO_BASE_URL",
            "https://sandbox.zenodo.org" if sandbox else "https://zenodo.org",
        ).rstrip("/")

        # 1) Zip crate
        try:
            zip_path = _zip_dir(crate_dir)
        except Exception as e:
            return DepositionResult(ok=False, platform="zenodo", message=f"Failed to zip crate: {e}")

        try:
            # 2) Create deposition draft
            create_url = f"{base}/api/deposit/depositions"
            payload: Dict[str, Any] = {"metadata": {}}

            # Minimal metadata; Zenodo requires title + creators at minimum
            payload["metadata"]["title"] = title or f"PBPK RO-Crate: {crate_dir.name}"
            payload["metadata"]["upload_type"] = "dataset"
            payload["metadata"]["description"] = description or "RO-Crate packaging of a PBPK model and its metadata."
            payload["metadata"]["creators"] = creators or [{"name": "Unknown"}]

            dep = _http_json("POST", create_url, access_token, payload)

            dep_id = str(dep.get("id"))
            links = dep.get("links") or {}
            bucket = links.get("bucket")
            html_url = links.get("html")

            if not bucket:
                return DepositionResult(
                    ok=False, platform="zenodo", message="Zenodo response missing upload bucket.", raw=dep
                )

            # 3) Upload file to bucket
            # Zenodo bucket upload uses PUT to {bucket}/{filename}?access_token=...
            filename = zip_path.name
            upload_url = f"{bucket}/{filename}?{urlencode({'access_token': access_token})}"
            _http_upload_put(upload_url, access_token, zip_path)

            # 4) (Optional) publish
            doi = None
            rec_url = html_url
            if publish:
                publish_url = f"{base}/api/deposit/depositions/{dep_id}/actions/publish"
                pub = _http_json("POST", publish_url, access_token, None)
                # published record info can include doi
                doi = (pub.get("doi") or (pub.get("metadata") or {}).get("prereserve_doi", {}).get("doi"))
                rec_url = (pub.get("links") or {}).get("html") or rec_url

            return DepositionResult(
                ok=True,
                platform="zenodo",
                record_id=dep_id,
                doi=doi,
                url=rec_url,
                message="Deposited successfully." + (" Published." if publish else " Draft created."),
                raw={"deposition": dep_id},
            )
        except Exception as e:
            return DepositionResult(ok=False, platform="zenodo", message=str(e))
        finally:
            # cleanup temp zip dir
            try:
                if zip_path and zip_path.exists():
                    shutil.rmtree(zip_path.parent, ignore_errors=True)
            except Exception:
                pass