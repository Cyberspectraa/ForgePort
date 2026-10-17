#!/usr/bin/env python3
"""Retrieve the exact original OmniIsle 0.5.0 Fabric 1.20.1 worldgen data.
Downloads *only* public release resources; never republishes the Fabric JAR."""
import hashlib, io, json, pathlib, urllib.request, zipfile

SHA256="ad520b4b880da4635180a8129bf0bd11847373da6165bd9d77db22fcadea9883"
URL="https://api.modrinth.com/v2/project/omniisle/version"
request=urllib.request.Request(URL,headers={"User-Agent":"OmniIsle-ForgePort/0.1 (source restoration)"})
versions=json.load(urllib.request.urlopen(request,timeout=45))
candidates=[v for v in versions if "1.20.1" in v["game_versions"] and "fabric" in v["loaders"] and v["version_number"].startswith("0.5.0")]
if not candidates: raise SystemExit("Could not find upstream OmniIsle 0.5.0 Fabric 1.20.1 release")
release=candidates[0]
print("Original resource release:",release["id"],release["version_number"])
files=release["files"]
url=next((f["url"] for f in files if f.get("primary")),files[0]["url"])
request=urllib.request.Request(url,headers={"User-Agent":"OmniIsle-ForgePort/0.1"})
data=urllib.request.urlopen(request,timeout=120).read()
digest=hashlib.sha256(data).hexdigest()
if digest!=SHA256: raise SystemExit(f"Source JAR hash mismatch: {digest}; refusing unverified build")
root=pathlib.Path("src/main/resources")
accepted=[]
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    for name in archive.namelist():
        if name.startswith("data/omniisle/worldgen/") and name.endswith(".json"):
            accepted.append(name)
        elif name=="data/minecraft/tags/worldgen/world_preset/normal.json":
            accepted.append(name)
        elif name.startswith("assets/omniisle/lang/") and name.endswith(".json"):
            accepted.append(name)
    for name in accepted:
        destination=root/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(archive.read(name))
print(f"Restored {len(accepted)} original 1.20.1 resource files")
