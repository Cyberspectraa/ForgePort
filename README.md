# OmniIsle — native Forge 1.20.1 port (development)

This repository is for a standalone **Minecraft Forge 1.20.1** port of **OmniIsle 0.5.0**. It is not yet a working Forge mod.

## Canonical upstream references

- **Exact Minecraft version:** [OmniIsle `fabric/1.20.1`](https://github.com/y9hack337/OmniIsle/tree/fabric/1.20.1), pinned at commit [`5f4b5bf`](https://github.com/y9hack337/OmniIsle/commit/5f4b5bf94761d640f5351ca90cb6825c6e9f6dac).
- **Loader conversion reference:** [OmniIsle `neoforge/1.21.1`](https://github.com/y9hack337/OmniIsle/tree/neoforge/1.21.1), pinned at [`051aba8`](https://github.com/y9hack337/OmniIsle/commit/051aba887c0c05346b8cbe6eab0e5434d6503b9c).
- [Main upstream repository](https://github.com/y9hack337/OmniIsle). **Do not use `main` as the source for Minecraft 1.20.1**; it targets newer Minecraft APIs.

Target: **Minecraft 1.20.1 · Forge 47.3.0 · Java 17**. This is **Forge**, not NeoForge, Fabric, or a Connector/Sinytra wrapper.

## Requirements for feature parity

The port must preserve the original island generation, coastline/deep-ocean transition, biome selection, world-creation preset, custom brush editor, custom mask export/persistence, structure placement, and original supported commands. The editor and per-world datapack persistence are not optional features.

**Current status:** repository initialized and upstream versions identified. No native Forge JAR has been compiled or verified. The existing experimental local source snapshot is separate from this repository and still needs to be integrated and built.

## Licensing

Upstream GitHub source is distributed under GPL-3.0. Retain copyright notices and the GPL license when porting. The separately distributed 1.20.1 Fabric JAR carries a different license declaration in its metadata, so clarify rights before distributing a binary publicly. This is an unofficial port.
