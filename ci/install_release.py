#!/usr/bin/env python3
"""Install a versioned hydrated OBC corpus release from one immutable manifest.

The manifest maps flat release asset names to their runtime paths inside the
repository. All requested artifacts are staged and hash/size verified before
anything is installed, so a corrupt or partial release cannot leave the tree in
an indeterminate state.

Examples:

    python3 ci/install_release.py \
      --manifest data/releases/obc-corpus-2024.2025-01-16.json \
      --archive /path/to/obc-hydrated.zip

    python3 ci/install_release.py \
      --manifest https://.../obc-corpus-2024.2025-01-16.json

If neither --archive nor --base-url is supplied, artifact_base_url from the
manifest is used and assets are downloaded individually.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import tempfile
from urllib.parse import urljoin
from urllib.request import urlopen, urlretrieve
import zipfile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(location: str) -> tuple[dict, bytes]:
    if location.startswith(("http://", "https://")):
        with urlopen(location) as response:
            raw = response.read()
    else:
        raw = Path(location).read_bytes()
    return json.loads(raw), raw


def safe_relpath(value: str) -> Path:
    posix = PurePosixPath(value)
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    return Path(*posix.parts)


def verify(path: Path, artifact: dict) -> None:
    expected_bytes = int(artifact["bytes"])
    expected_hash = artifact["sha256"].lower()
    if not path.is_file():
        raise RuntimeError(f"missing artifact {artifact['asset']}: {path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise RuntimeError(
            f"size mismatch for {artifact['asset']}: {actual_bytes} != {expected_bytes}"
        )
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"sha256 mismatch for {artifact['asset']}: {actual_hash} != {expected_hash}"
        )


def existing_is_correct(root: Path, artifact: dict) -> bool:
    target = root / safe_relpath(artifact["install_path"])
    try:
        verify(target, artifact)
        return True
    except (RuntimeError, OSError):
        return False


def stage_from_zip(archive: Path, artifacts: list[dict], staging: Path) -> dict[str, Path]:
    wanted = {artifact["asset"]: artifact for artifact in artifacts}
    staged: dict[str, Path] = {}
    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        for asset in wanted:
            if asset not in names:
                raise RuntimeError(f"release archive does not contain required asset: {asset}")
            safe_relpath(asset)
            destination = staging / "assets" / safe_relpath(asset)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with package.open(asset) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            staged[asset] = destination
    return staged


def stage_from_tar(archive: Path, artifacts: list[dict], staging: Path) -> dict[str, Path]:
    wanted = {artifact["asset"] for artifact in artifacts}
    staged: dict[str, Path] = {}
    with tarfile.open(archive) as package:
        members = {member.name.lstrip("./"): member for member in package.getmembers()}
        for asset in wanted:
            safe_relpath(asset)
            member = members.get(asset)
            if member is None or not member.isfile():
                raise RuntimeError(f"release archive does not contain required asset: {asset}")
            source = package.extractfile(member)
            if source is None:
                raise RuntimeError(f"cannot read required asset from archive: {asset}")
            destination = staging / "assets" / safe_relpath(asset)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            staged[asset] = destination
    return staged


def materialize_archive(location: str, staging: Path) -> Path:
    if location.startswith(("http://", "https://")):
        suffix = ".zip" if location.lower().split("?", 1)[0].endswith(".zip") else ".tar.gz"
        destination = staging / f"release{suffix}"
        print(f"downloading archive: {location}")
        urlretrieve(location, destination)
        return destination
    return Path(location)


def stage_from_base_url(base_url: str, artifacts: list[dict], staging: Path) -> dict[str, Path]:
    staged: dict[str, Path] = {}
    base = base_url.rstrip("/") + "/"
    for artifact in artifacts:
        asset = artifact["asset"]
        safe_relpath(asset)
        destination = staging / "assets" / safe_relpath(asset)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_url = urljoin(base, asset)
        print(f"downloading asset: {source_url}")
        urlretrieve(source_url, destination)
        staged[asset] = destination
    return staged


def write_stamp(root: Path, manifest: dict, manifest_bytes: bytes) -> None:
    stamp = {
        "schema_version": 1,
        "release": manifest["release"],
        "edition": manifest.get("edition"),
        "current_through": manifest.get("current_through"),
        "through_instrument": manifest.get("through_instrument"),
        "source_commit": manifest.get("source_commit"),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    destination = root / ".obc-release.json"
    temporary = destination.with_suffix(".json.part")
    temporary.write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, destination)


def install(args: argparse.Namespace) -> int:
    manifest, manifest_bytes = read_json(args.manifest)
    if manifest.get("schema_version") != 1:
        raise RuntimeError(f"unsupported manifest schema_version: {manifest.get('schema_version')!r}")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise RuntimeError("release manifest has no artifacts")

    seen_assets: set[str] = set()
    seen_targets: set[str] = set()
    for artifact in artifacts:
        for key in ("asset", "install_path", "bytes", "sha256"):
            if key not in artifact:
                raise RuntimeError(f"artifact is missing required field {key!r}: {artifact}")
        safe_relpath(artifact["asset"])
        safe_relpath(artifact["install_path"])
        if artifact["asset"] in seen_assets:
            raise RuntimeError(f"duplicate release asset: {artifact['asset']}")
        if artifact["install_path"] in seen_targets:
            raise RuntimeError(f"duplicate install target: {artifact['install_path']}")
        seen_assets.add(artifact["asset"])
        seen_targets.add(artifact["install_path"])

    root = Path(args.root).resolve()
    correct = [artifact for artifact in artifacts if existing_is_correct(root, artifact)]
    needed = [artifact for artifact in artifacts if artifact not in correct]
    print(
        f"release {manifest['release']}: {len(correct)} already correct; "
        f"{len(needed)} need installation"
    )

    if args.check_only:
        if needed:
            for artifact in needed:
                print(f"MISSING/MISMATCH {artifact['install_path']}")
            return 1
        print("all release artifacts match the manifest")
        return 0

    if not needed:
        write_stamp(root, manifest, manifest_bytes)
        return 0

    with tempfile.TemporaryDirectory(prefix="obc-release-") as tmp:
        staging = Path(tmp)
        if args.archive:
            archive = materialize_archive(args.archive, staging)
            lower = archive.name.lower()
            if lower.endswith(".zip"):
                staged = stage_from_zip(archive, needed, staging)
            elif lower.endswith((".tar.gz", ".tgz", ".tar")):
                staged = stage_from_tar(archive, needed, staging)
            else:
                raise RuntimeError(f"unsupported release archive format: {archive}")
        else:
            base_url = args.base_url or manifest.get("artifact_base_url")
            if not base_url:
                raise RuntimeError(
                    "no --archive, --base-url, or artifact_base_url in the manifest"
                )
            staged = stage_from_base_url(base_url, needed, staging)

        # Verify every required staged file before mutating the working tree.
        for artifact in needed:
            verify(staged[artifact["asset"]], artifact)
            print(
                f"verified {artifact['bytes']:>11,}  {artifact['asset']} -> "
                f"{artifact['install_path']}"
            )

        # Install atomically file-by-file only after the full staged set passed.
        for artifact in needed:
            target = root / safe_relpath(artifact["install_path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".part")
            shutil.copyfile(staged[artifact["asset"]], temporary)
            os.replace(temporary, target)

    # Verify the installed tree again before recording the release stamp.
    failed = [artifact for artifact in artifacts if not existing_is_correct(root, artifact)]
    if failed:
        raise RuntimeError(
            "post-install verification failed for: "
            + ", ".join(artifact["install_path"] for artifact in failed)
        )
    write_stamp(root, manifest, manifest_bytes)
    print(f"installed and verified {manifest['release']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="local path or HTTPS URL")
    parser.add_argument("--archive", help="local path or HTTPS URL to a ZIP/TAR release bundle")
    parser.add_argument("--base-url", help="base URL containing flat release assets")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        return install(args)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
