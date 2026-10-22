#!/usr/bin/env python3
"""Fetch Aquamirae 6.4.0 + Obscure API 18 from official Modrinth releases.

These are the versions in the reported 1.20.1 modpack. Validate the exact
Ice Maze biome tag and Forge placed-feature modifiers before server startup.
Never redistribute Aquamirae in the OmniIsle release artifact.
"""
import hashlib
import json
import pathlib
import zipfile
from verify_modpack_compat import json_api, download

def install(release, expected_name, target):
    info = json_api("https://api.modrinth.com/v2/version/" + release)
    assert "1.20.1" in info["game_versions"] and "forge" in info["loaders"], info
    matches = [entry for entry in info["files"] if
               entry["filename"] == expected_name or
               (expected_name == "obscure_api-18.jar" and
                entry["filename"].lower().endswith("-18.jar"))]
    if len(matches) != 1:
        raise RuntimeError(f"No unique official Forge JAR for {expected_name}: {[e['filename'] for e in info['files']]}")
    artifact = matches[0]
    raw = download(artifact["url"])
    if hashlib.sha512(raw).hexdigest() != artifact["hashes"]["sha512"]:
        raise ValueError(f"JAR integrity mismatch: {expected_name}")
    target.mkdir(parents=True, exist_ok=True)
    path = target / expected_name
    path.write_bytes(raw)
    return path

def verify_aquamirae(jar):
    with zipfile.ZipFile(jar) as z:
        files = set(z.namelist())
        ice_tag = "data/aquamirae/tags/worldgen/biome/ice_maze.json"
        assert ice_tag in files
        tag = json.loads(z.read(ice_tag))
        assert {"minecraft:frozen_ocean", "minecraft:deep_frozen_ocean"}.issubset(
            {item if isinstance(item,str) else item["id"] for item in tag["values"]})
        for suffix in ["surface_walls", "surface_cracked_ice"]:
            modifier = json.loads(z.read(
                f"data/aquamirae/forge/biome_modifier/{suffix}.json"))
            assert modifier["biomes"] == "#aquamirae:ice_maze", modifier
            assert modifier["type"] == "forge:add_features", modifier
            assert f"aquamirae:{suffix}" in str(modifier), modifier
        assert "com/obscuria/aquamirae/common/worldgen/feature/placement/ChunkSampledBiomeFilter.class" in files
    print("Verified Aquamirae 6.4.0 really attaches Ice Maze to both frozen oceans", flush=True)

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("target", type=pathlib.Path)
    args=p.parse_args()
    aquamirae=install("A6aIqoJZ","aquamirae-forge-1.20.1-6.4.0.jar", args.target)
    install("7sZmDObM","obscure_api-18.jar",args.target)
    verify_aquamirae(aquamirae)
    print("Ready to test Aquamirae on the actual Forge 1.20.1 server",flush=True)

if __name__ == "__main__":
    main()
