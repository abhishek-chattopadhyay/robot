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
    zip_base = tmpdir / crate_dir.name
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", root_dir=str(crate_dir)))
    return zip_path


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _http_json(method: str, url: str, token: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {"Authorization": f"Bearer {token}"}

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=data, method=method, headers=headers)

    try:
        with urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Zenodo HTTPError {e.code} for {url}: {msg}") from e
    except URLError as e:
        raise RuntimeError(f"Zenodo URLError for {url}: {e}") from e


def _http_upload_put(url: str, token: str, filepath: Path) -> Dict[str, Any]:
    data = filepath.read_bytes()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }
    req = Request(url, data=data, method="PUT", headers=headers)

    try:
        with urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Zenodo upload HTTPError {e.code} for {url}: {msg}") from e
    except URLError as e:
        raise RuntimeError(f"Zenodo upload URLError for {url}: {e}") from e


def _extract_zenodo_metadata(metadata_path: Path, crate_name: str) -> Dict[str, Any]:
    title = f"PBPK RO-Crate: {crate_name}"
    description = "RO-Crate packaging of a PBPK model and its metadata."
    creators = [{"name": "Unknown"}]
    license_value = None
    keywords: list[str] = ["PBPK", "RO-Crate", "metadata"]

    try:
        obj = _read_json(metadata_path)
        graph = obj.get("@graph", [])
        dataset = None

        for item in graph:
            if item.get("@id") == "./":
                dataset = item
                break

        if dataset:
            name_val = dataset.get("name")
            desc_val = dataset.get("description")
            lic_val = dataset.get("license")
            keywords_val = dataset.get("keywords")
            creator_val = dataset.get("creator")

            if isinstance(name_val, str) and name_val.strip():
                title = name_val.strip()

            if isinstance(desc_val, str) and desc_val.strip():
                description = desc_val.strip()

            if isinstance(lic_val, str) and lic_val.strip():
                license_value = lic_val.strip()

            if isinstance(keywords_val, list):
                keywords = [str(x).strip() for x in keywords_val if str(x).strip()]
            elif isinstance(keywords_val, str) and keywords_val.strip():
                keywords = [keywords_val.strip()]

            creator_ids: list[str] = []
            if isinstance(creator_val, dict) and "@id" in creator_val:
                creator_ids = [creator_val["@id"]]
            elif isinstance(creator_val, list):
                for c in creator_val:
                    if isinstance(c, dict) and "@id" in c:
                        creator_ids.append(c["@id"])

            extracted_creators: list[dict[str, str]] = []
            if creator_ids:
                by_id = {item.get("@id"): item for item in graph if isinstance(item, dict) and "@id" in item}
                for cid in creator_ids:
                    cobj = by_id.get(cid)
                    if not cobj:
                        continue
                    name = cobj.get("name")
                    aff = cobj.get("affiliation")
                    if isinstance(name, str) and name.strip():
                        entry: dict[str, str] = {"name": name.strip()}
                        if isinstance(aff, str) and aff.strip():
                            entry["affiliation"] = aff.strip()
                        extracted_creators.append(entry)

            if extracted_creators:
                creators = extracted_creators

    except Exception:
        pass

    md: Dict[str, Any] = {
        "title": title,
        "upload_type": "software",
        "description": description,
        "creators": creators,
        "keywords": keywords,
    }

    if license_value:
        md["license"] = license_value

    return md


@register("zenodo")
class ZenodoDepositor:
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

        zip_path: Optional[Path] = None

        try:
            zip_path = _zip_dir(crate_dir)

            md = _extract_zenodo_metadata(metadata_path, crate_dir.name)
            if title:
                md["title"] = title
            if description:
                md["description"] = description
            if creators:
                md["creators"] = creators

            create_url = f"{base}/api/deposit/depositions"
            create_body: Dict[str, Any] = {"metadata": md}
            dep = _http_json("POST", create_url, access_token, create_body)

            dep_id = str(dep.get("id")) if dep.get("id") is not None else None
            links = dep.get("links") or {}
            bucket = links.get("bucket")
            html_url = links.get("html")
            record_url = html_url

            if not dep_id:
                return DepositionResult(
                    ok=False,
                    platform="zenodo",
                    message="Zenodo response missing deposition id.",
                    raw=dep,
                )

            if not bucket:
                return DepositionResult(
                    ok=False,
                    platform="zenodo",
                    record_id=dep_id,
                    url=record_url,
                    message="Zenodo response missing upload bucket.",
                    raw=dep,
                )

            filename = zip_path.name
            upload_url = f"{bucket}/{filename}?{urlencode({'access_token': access_token})}"
            upload_result = _http_upload_put(upload_url, access_token, zip_path)

            publish_result: Dict[str, Any] | None = None
            doi = None
            was_published = False

            if publish:
                publish_url = f"{base}/api/deposit/depositions/{dep_id}/actions/publish"
                publish_result = _http_json("POST", publish_url, access_token, None)
                was_published = True

                doi = (
                    publish_result.get("doi")
                    or (publish_result.get("metadata") or {}).get("prereserve_doi", {}).get("doi")
                )

                record_url = (publish_result.get("links") or {}).get("html") or record_url
            else:
                doi = (
                    dep.get("doi")
                    or (dep.get("metadata") or {}).get("prereserve_doi", {}).get("doi")
                )

            return DepositionResult(
                ok=True,
                platform="zenodo",
                record_id=dep_id,
                doi=doi,
                url=record_url,
                bucket_url=bucket,
                file_name=filename,
                published=was_published,
                message="Deposited successfully." + (" Published." if publish else " Draft created."),
                raw={
                    "deposition": dep,
                    "upload": upload_result,
                    "publish": publish_result,
                },
            )

        except Exception as e:
            return DepositionResult(
                ok=False,
                platform="zenodo",
                message=str(e),
            )

        finally:
            try:
                if zip_path and zip_path.exists():
                    shutil.rmtree(zip_path.parent, ignore_errors=True)
            except Exception:
                pass