# OmniIsle — native Forge 1.20.1 port

**Development work in progress — not a finished or game-tested release.** This is source for a Forge-only implementation, with no Fabric API or Sinytra Connector dependency.

## Build and test

Java 17, Forge 47.3.0, Minecraft 1.20.1, Gradle 8.9 and an internet connection are required.

```bash
python3 tools/restore_worldgen.py
gradle --no-daemon build
```

The resource script downloads the public original Fabric 1.20.1 release from Modrinth, validates its exact SHA-256, and extracts only its original worldgen/translation JSON; no Fabric code or binary is included in the Forge JAR. GitHub Actions runs this automatically. Never install both the original Fabric JAR and this Forge port.

## Roadmap

Core density, island masks, climate biome selection, fixed structure placements, commands, river spawns. The original visual island editor, biome picker and per-world datapack generator are **not yet ported**. A green compilation is NOT proof of generation parity or modpack compatibility.

This is an **unofficial** derivative of [OmniIsle by Hack337](https://github.com/y9hack337/OmniIsle). Public source is GPL-3.0-only; the supplied Fabric 1.20.1 JAR metadata says All-Rights-Reserved, so **public release licensing needs clarification with the author first**. 
