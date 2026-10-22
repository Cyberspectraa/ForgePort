#!/usr/bin/env python3
"""Reproduce the user's five uploaded Forge 1.20.1 mod versions in CI.

Fetch SHA-512-identical public Modrinth artifacts rather than committing
third-party binaries. Client-only Polytone is staged separately; the other
four run on the dedicated-server smoke test. Optional Architectury 9.2.14 is
needed by Terrain Slabs and Smooth Steps. See --client for the client set.

This script is only used for validation; it is not packaged in the mod JAR.
"""
import argparse
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
import zipfile

USER_UPLOADS = [
    # Original uploaded JAR SHA-512 values, checked against the downloaded bytes.
    ("polytone-1.20-3.5.26.jar",
     "574664c5f0aacf2450aae924eab1df9b4b6064ce01ec3f6531740f143e4eb1b5895c4c5e1cc60bc04d8d41af7acd6ba01611e627faf8557eb088f7d28f7ae8a2",
     "polytone", True),
    ("terrain_slabs-forge-3.1.1.jar",
     "dc0d625bf16ded8979042f1e7cdd5e1cf548a9cc91d949e65d2847966961eb69be78584a5957638cffd63326cda9cfb1a439e707e162031ae6e332da7e41cf63",
     "countereds-terrain-slabs", False),
    ("smooth_steps-forge-1.1.0.jar",
     "c77517af6b459a6bf2dea6104a3c8ec7bdbf61d5fe838536898268ac7fc47e6ee3121df46e291a70c0c574b8f2d3d2f1db67b53e52603d2425917fd357ea5605",
     "countereds-smooth-steps", False),
    ("roadweaver-forge-2.1.1-1.20.1.jar",
     "00dc2636279d2758bbe9f2b8c67b09d7e4badc79e2e0eca934f01d6279579c8d972e11c6077f043809c02d0421f5bb98d53be4b8758c1bea23a167585f489544",
     "roadweaver", False),
    ("blooming-biosphere-1.1.0-1.20.1.jar",
     "011d8869b0d6b12e05ddf47bd00bffeaedfd1b34927981e0584b3d39414fc9ef93a1264b215879da9443aa6e1b56cf9adfaf997d435ce68faf328119f63bfea4",
     "blooming-biosphere", False),
]
API = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "OmniIsleForgeRemake/0.5-compat-test (Github Actions)"}

def download(url):
    last_error = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=HEADERS), timeout=100
            ) as response:
                return response.read()
        except (OSError, urllib.error.HTTPError) as exc:
            last_error = exc
            if attempt != 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")

def json_api(url):
    return json.loads(download(url))

def resolve_file(filename, sha512, slug):
    # Preferred: exact uploaded file version and hash, no guesswork on releases.
    metadata = None
    try:
        metadata = json_api(f"{API}/version_file/{sha512}?algorithm=sha512")
    except RuntimeError:
        pass
    if metadata is None:
        from urllib.parse import quote
        variants = json_api(f"{API}/project/{slug}/version?game_versions=%5B%221.20.1%22%5D")
        for release in variants:
            matching = [f for f in release["files"] if
                f.get("hashes", {}).get("sha512") == sha512]
            if matching:
                metadata = release
                break
    if metadata is None:
        # Some user-uploaded CurseForge artifacts differ from the Modrinth
        # release for the same nominal version. Only use known official CF
        # file IDs, then check the exact uploaded SHA-512 after downloading.
        curseforge_files = {"roadweaver": 7517344, "polytone": 8042889}
        file_id = curseforge_files.get(slug)
        if file_id is None:
            raise RuntimeError(f"No publicly verifiable exact matching release for {filename} (SHA-512={sha512}).")
        from urllib.parse import quote
        return (f"https://mediafilez.forgecdn.net/files/{file_id // 1000}/"
                f"{file_id % 1000}/{quote(filename)}")
    candidates = [f for f in metadata["files"]
                  if f.get("hashes", {}).get("sha512") == sha512]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected a single exact match for {filename}, got {len(candidates)}")
    return candidates[0]["url"]

def install_one(filename, sha512, slug, dest):
    url = resolve_file(filename, sha512, slug)
    raw = download(url)
    actual = hashlib.sha512(raw).hexdigest()
    if actual != sha512:
        raise RuntimeError(f"Uploaded JAR differs from public download: {filename}")
    with zipfile.ZipFile(__import__('io').BytesIO(raw)) as jar:
        if "META-INF/mods.toml" not in jar.namelist():
            raise RuntimeError(f"Forge mod metadata missing: {filename}")
        if filename.startswith("blooming"):
            assert "data/minecraft/dimension/overworld.json" in jar.namelist()
            assert "data/blooming_biosphere/worldgen/biome/autumnal_forest.json" in jar.namelist()
            assert "data/blooming_biosphere/worldgen/biome/tidepools.json" in jar.namelist()
        if filename.startswith("terrain_slabs"):
            assert "data/terrain_slabs/forge/biome_modifier/add_slab_feature_overworld.json" in jar.namelist()
        if filename.startswith("roadweaver"):
            assert "data/roadweaver/forge/biome_modifier/road_feature.json" in jar.namelist()
    dest.mkdir(parents=True, exist_ok=True)
    (dest / filename).write_bytes(raw)
    print("Verified exact uploaded mod:", filename, len(raw), flush=True)

def architectury(dest):
    # Both Terrain Slabs and Smooth Steps require Architectury 9.2.14 for Forge.
    versions = json_api(
        f"{API}/project/architectury-api/version?game_versions=%5B%221.20.1%22%5D&loaders=%5B%22forge%22%5D"
    )
    matches = [v for v in versions if "9.2.14" in v.get("version_number", "")]
    if not matches:
        raise RuntimeError("Architectury Forge 1.20.1 9.2.14 not available")
    files = [f for v in matches for f in v["files"] if f["filename"].endswith(".jar")
             and "forge" in f["filename"].lower()]
    if not files:
        raise RuntimeError("Architectury Forge JAR not found")
    file = files[0]
    raw = download(file["url"])
    if hashlib.sha512(raw).hexdigest() != file["hashes"]["sha512"]:
        raise RuntimeError("Architectury SHA-512 mismatch")
    (dest / "architectury-9.2.14-forge.jar").write_bytes(raw)
    print("Verified Architectury 9.2.14 Forge:", len(raw), flush=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("target", type=pathlib.Path)
    p.add_argument("--client", action="store_true")
    args = p.parse_args()
    args.target.mkdir(parents=True, exist_ok=True)
    for filename, sha512, slug, client_only in USER_UPLOADS:
        if client_only and not args.client:
            continue
        install_one(filename, sha512, slug, args.target)
    architectury(args.target)
    print("All uploaded worldgen mods staged for", "client" if args.client else "server", flush=True)

if __name__ == "__main__":
    main()
