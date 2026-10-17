# OmniIsle — native Forge 1.20.1 port (development)

This repository is for a standalone **Minecraft Forge 1.20.1** port of **OmniIsle 0.5.0**. A native Forge JAR now builds and passes automated editor interaction, datapack export, and installed dedicated-server smoke tests on **Forge 47.4.10**. It remains an unofficial test build until verified with a real desktop client and larger modpacks.

## Canonical upstream references

- **Exact Minecraft version:** [OmniIsle `fabric/1.20.1`](https://github.com/y9hack337/OmniIsle/tree/fabric/1.20.1), pinned at commit [`5f4b5bf`](https://github.com/y9hack337/OmniIsle/commit/5f4b5bf94761d640f5351ca90cb6825c6e9f6dac).
- **Loader conversion reference:** [OmniIsle `neoforge/1.21.1`](https://github.com/y9hack337/OmniIsle/tree/neoforge/1.21.1), pinned at [`051aba8`](https://github.com/y9hack337/OmniIsle/commit/051aba887c0c05346b8cbe6eab0e5434d6503b9c).
- [Main upstream repository](https://github.com/y9hack337/OmniIsle). **Do not use `main` as the source for Minecraft 1.20.1**; it targets newer Minecraft APIs.

Target: **Minecraft 1.20.1 · Forge 47.4.10 · Java 17**. This is **Forge**, not NeoForge, Fabric, or a Connector/Sinytra wrapper.

## Requirements for feature parity

The port must preserve the original island generation, coastline/deep-ocean transition, biome selection, world-creation preset, custom brush editor, custom mask export/persistence, structure placement, and original supported commands. The editor and per-world datapack persistence are not optional features.

**Current status:** [GitHub Actions build 39036829484](https://github.com/Cyberspectraa/ForgePort/actions/runs/39036829484) passed compile/reobfuscation, resource checks, dedicated server generation, selection of the OmniIsle world preset, click-through on the Forge-native Customize OmniIsle button, editor rendering, editor datapack export and a separate installed production Forge 47.4.10 server launch with the packaged mod JAR. The previous JAR distributed before this run was missing `omniisle.refmap.json` and must not be used.

## Installation / support

1. Download `OmniIsle-Forge-1.20.1` from the successful run's Artifacts and extract its JAR (not the artifact ZIP) into the `mods` directory of Minecraft 1.20.1 Forge 47.4.10.
2. Remove all prior OmniIsle Fabric, Connector, and experimental Forge JARs first. You do not need Sinytra Connector or Fabric API.
3. Create a **new test world** with world type OmniIsle; back up existing worlds before testing.
4. This release was automatically validated in Forge development client and installed dedicated-server environments. **Normal Windows launcher and full modpack compatibility are not yet proven.** For a Windows launch failure, attach the latest complete `logs/debug.log` and the crash report or launcher exit/console log; logs that stop before mod discovery cannot establish which mod failed.

## Licensing

Upstream GitHub source is distributed under GPL-3.0. Retain copyright notices and the GPL license when porting. The separately distributed 1.20.1 Fabric JAR carries a different license declaration in its metadata, so maintain GPL compliance for public distribution and check upstream licensing details. This is an unofficial port.
