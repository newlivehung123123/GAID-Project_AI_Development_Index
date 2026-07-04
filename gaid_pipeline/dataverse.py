"""Harvard Dataverse sync for the GAID Project.

Detects the latest published GAID wave in the `gaidproject` dataverse,
downloads the main compiled archive (gaid_w{wave}_v{version}.zip), verifies
its MD5 checksum, extracts it, and records what is installed in a manifest
so downstream stages can tell when a new wave has arrived.

No API key is required: all GAID datasets are public.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://dataverse.harvard.edu/api"
DATAVERSE_ALIAS = "gaidproject"
WAVE_FILE_RE = re.compile(r"gaid_w(\d+)_v(\d+)\.zip$", re.IGNORECASE)
TIMEOUT = 120


class DataverseError(RuntimeError):
    """Raised when the Dataverse API returns something we cannot proceed with."""


@dataclass
class WaveFile:
    """The main compiled GAID archive for one (wave, version)."""

    wave: int
    version: int
    filename: str
    file_id: int
    md5: str
    size: int
    dataset_doi: str
    dataset_version: str

    @property
    def tag(self) -> str:
        return f"w{self.wave}_v{self.version}"


def _get(path: str, **params) -> dict | list:
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != "OK":
        raise DataverseError(f"Dataverse API error on {path}: {body}")
    return body["data"]


def list_dataset_dois() -> list[str]:
    """Every dataset DOI currently published in the gaidproject dataverse.

    Future waves may be published either as new versions of an existing
    dataset or as entirely new datasets, so we enumerate the whole dataverse
    rather than pinning one DOI.
    """
    contents = _get(f"/dataverses/{DATAVERSE_ALIAS}/contents")
    dois = [
        f"{d['protocol']}:{d['authority']}/{d['identifier']}"
        for d in contents
        if d.get("type") == "dataset"
    ]
    if not dois:
        raise DataverseError(f"No datasets found in dataverse '{DATAVERSE_ALIAS}'")
    return dois


def find_wave_files() -> list[WaveFile]:
    """All gaid_w{wave}_v{version}.zip files across every published dataset."""
    waves: list[WaveFile] = []
    for doi in list_dataset_dois():
        version = _get(
            "/datasets/:persistentId/versions/:latest-published", persistentId=doi
        )
        version_label = f"{version.get('versionNumber')}.{version.get('versionMinorNumber')}"
        for entry in version.get("files", []):
            df = entry.get("dataFile", {})
            name = df.get("filename", "")
            m = WAVE_FILE_RE.search(name)
            if not m:
                continue
            waves.append(
                WaveFile(
                    wave=int(m.group(1)),
                    version=int(m.group(2)),
                    filename=name,
                    file_id=df["id"],
                    md5=df.get("md5") or df.get("checksum", {}).get("value", ""),
                    size=df.get("filesize", 0),
                    dataset_doi=doi,
                    dataset_version=version_label,
                )
            )
    if not waves:
        raise DataverseError(
            "No file matching gaid_w{N}_v{N}.zip found in any gaidproject dataset. "
            "If the naming convention changed, update WAVE_FILE_RE."
        )
    return waves


def latest_wave() -> WaveFile:
    return max(find_wave_files(), key=lambda w: (w.wave, w.version))


# --- manifest -----------------------------------------------------------

def manifest_path(data_dir: Path) -> Path:
    return data_dir / "manifest.json"


def load_manifest(data_dir: Path) -> dict | None:
    path = manifest_path(data_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_manifest(data_dir: Path, wave: WaveFile, extracted_to: Path) -> dict:
    manifest = {
        "installed": asdict(wave),
        "extracted_to": str(extracted_to),
        "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path(data_dir).write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def is_new(latest: WaveFile, manifest: dict | None) -> bool:
    if manifest is None:
        return True
    installed = manifest["installed"]
    return (latest.wave, latest.version, latest.md5) != (
        installed["wave"],
        installed["version"],
        installed["md5"],
    )


# --- download & extract -------------------------------------------------

def download(wave: WaveFile, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / wave.filename
    url = f"{BASE_URL}/access/datafile/{wave.file_id}"
    md5 = hashlib.md5()
    with requests.get(url, stream=True, timeout=TIMEOUT) as resp:
        resp.raise_for_status()
        with open(target, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
                md5.update(chunk)
    digest = md5.hexdigest()
    if wave.md5 and digest != wave.md5:
        target.unlink(missing_ok=True)
        raise DataverseError(
            f"Checksum mismatch for {wave.filename}: expected {wave.md5}, got {digest}"
        )
    return target


def extract(archive: Path, wave: WaveFile, data_dir: Path) -> Path:
    out_dir = data_dir / "wave" / wave.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        members = [
            m for m in zf.namelist()
            if not m.startswith("__MACOSX/") and not Path(m).name.startswith("._")
        ]
        zf.extractall(out_dir, members=members)
    return out_dir


# --- top-level operations ------------------------------------------------

def check(data_dir: Path) -> tuple[WaveFile, dict | None, bool]:
    """Return (latest wave on Dataverse, installed manifest, whether it's new)."""
    latest = latest_wave()
    manifest = load_manifest(data_dir)
    return latest, manifest, is_new(latest, manifest)


def sync(data_dir: Path, force: bool = False) -> dict:
    """Fetch the latest wave if it is newer than what is installed."""
    latest, manifest, new = check(data_dir)
    if not new and not force:
        return {"changed": False, "manifest": manifest}
    archive = download(latest, data_dir / "raw")
    extracted = extract(archive, latest, data_dir)
    manifest = save_manifest(data_dir, latest, extracted)
    return {"changed": True, "manifest": manifest}
