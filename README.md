# OmniIsle — native Forge 1.20.1 port (development)

This repository is for a standalone **Minecraft Forge 1.20.1** port of **OmniIsle 0.5.0**. A native Forge JAR now builds and passes automated editor interaction, datapack export, and installed dedicated-server smoke tests on **Forge 47.4.10**. It remains an unofficial test build until verified with a real desktop client and larger modpacks. The CI workflow pulls exact, pinned upstream Git revisions, and restores its temporary editor test hook before uploading the full source archive.

## Canonical upstream references

- **Exact Minecraft version:** [OmniIsle `fabric/1.20.1`](https://github.com/y9hack337/OmniIsle/tree/fabric/1.20.1), pinned at commit [`5f4b5bf`](https://github.com/y9hack337/OmniIsle/commit/5f4b5bf94761d640f5351ca90cb6825c6e9f6dac).
- **Loader conversion reference:** [OmniIsle `neoforge/1.21.1`](https://github.com/y9hack337/OmniIsle/tree/neoforge/1.21.1), pinned at [`051aba8`](https://github.com/y9hack337/OmniIsle/commit/051aba887c0c05346b8cbe6eab0e5434d6503b9c).
- [Main upstream repository](https://github.com/y9hack337/OmniIsle). **Do not use `main` as the source for Minecraft 1.20.1**; it targets newer Minecraft APIs.

Target: **Minecraft 1.20.1 · Forge 47.4.10 · Java 17**. This is **Forge**, not NeoForge, Fabric, or a Connector/Sinytra wrapper.

## Requirements for feature parity

The port must preserve the original island generation, coastline/deep-ocean transition, biome selection, world-creation preset, custom brush editor, custom mask export/persistence, structure placement, and original supported commands. The editor and per-world datapack persistence are not optional features.

**Current status:** [GitHub Actions build 39036829484](https://github.com/Cyberspectraa/OmniIsleForgeRemake/actions/runs/39036829484) passed compile/reobfuscation, resource checks, dedicated server generation, selection of the OmniIsle world preset, click-through on the Forge-native Customize OmniIsle button, editor rendering, editor datapack export and a separate installed production Forge 47.4.10 server launch with the packaged mod JAR. The previous JAR distributed before this run was missing `omniisle.refmap.json` and must not be used.

## Biome editor selections (Forge 1.20.1)

The Forge world-creation screen must select the freshly reloaded OmniIsle preset after the editor's generated datapack is applied. Otherwise it may retain the previous biome source and generate biomes that were just disabled. The editor now refreshes the world preset after a successful save, and OmniIsle reports only the enabled biome palette as possible biomes.

The automated client test disables Plains, Beach, Deep Ocean, Frozen River and Dripstone Caves, exports the customized datapack, applies it in the real Create World screen, and checks that the selected biome source and sampled generation do not return the disabled biomes. This test passed on Forge 47.4.10.

**Create a new test world** to evaluate biome selection changes. Already-generated chunks are not rewritten. Keep at least one biome enabled in each category.

## Adding biomes from other Forge mods

The island editor now has **Biomes | Structures | Mods** tabs. Choose **Mods** to open the modded-biome selection page. It discovers biome IDs in the Minecraft world-creation registry, including data-driven biomes installed by Forge mods. Select a terrain category (Land, Shore, Ocean, River, or Cave) and tick the biomes to generate. Mod biomes are opt-in, and each is assigned to at most one category.

When you press **Done**, OmniIsle writes the selected registry IDs into the generated **per-world datapack**. The server biome source uses deterministic regions for the selected modded biomes, and only enabled biomes are advertised to worldgen and other mods. This affects both the island layout preview (modded regions use a distinctive preview colour) and actual generation. You must keep the mod that owns each selected biome installed in the world: missing registry IDs can prevent world loading.

Custom biomes do not necessarily have terrain-aware climate placement rules of their originating mod. Assign each custom biome to the appropriate category; OmniIsle's own region sampling decides where within that category it appears.

## Biome generation and modded biomes

OmniIsle keeps its original climate-driven distribution for vanilla biomes. The editor's **Mods** tab lets you opt into biomes from installed mods, assigning each to Land, Shore, Ocean, River, or Cave. These added biomes generate in larger, smooth, deterministic regions, shared by the preview and server worldgen. Every selected mod biome has a fair opportunity to appear rather than being biased toward the middle of a biome list.

**No biome percentage controls or weight settings are provided.** Enabling or disabling biomes is the only selection control; the mod decides the distribution based on the seed and terrain. A category can contain only modded biomes, in which case disabled vanilla entries are not regenerated. Generated datapacks no longer serialize `biome_weights`, and an existing world preset with that old property no longer changes biome proportions. New chunks follow the saved enabled-biome selection; already-generated terrain is not replaced.

## Modded biome appearance and terrain surfaces

A selected biome ID alone does not guarantee its intended ground blocks, trees or decorations. Minecraft separates the **biome registry** (climate, features, spawns, visual effects) from the **noise generator surface rules** (biome-specific topsoil, stones and material transitions). The OmniIsle world preset uses its own noise settings to keep the island shape.

For mods using **TerraBlender 3.x on Forge 1.20.1**, OmniIsle now marks its own noise-generator settings as Overworld settings when TerraBlender is installed. This lets TerraBlender apply the other mod's registered namespace-specific surface rules to OmniIsle, rather than showing that biome's ID with inappropriate default surface blocks. TerraBlender remains **optional**; the bridge does not modify the generator of other worlds or dimensions. The integration logs `OmniIsle TerraBlender biome surface rules activated` when it runs.

Surface rules are just one aspect of a biome's appearance. Mods that use a different surface-rule system, rely on their own terrain generator, require custom dimension logic, or use features with special placement predicates may still need an explicit adapter. In particular, the modded biome's **trees and configured features come from the original mod**, not from the name shown in F3. For a biome that still looks incorrect, capture the exact F3 `Biome: namespace:id`, the biome-owning mod and version, and a screenshot of the blocks and trees so its actual worldgen assets can be compared with OmniIsle.

## Cross-mod compatibility boundaries

* Registered biomes from installed datapacks/mods are found in the worldgen biome registry and available for opt-in. The biome's owning mod or datapack **must remain installed** for the saved world to load.
* Registered Minecraft structures are checked against their biome registry holder sets. If no permitted biome is active, they cannot start. Structures whose currently permitted biomes are **land only** additionally get a 48-block coastline margin; larger structures can opt in to the existing 96-block `#omniisle:land_only` tag. Mixed-biome and aquatic structures are not automatically relocated to land.
* "Universal" here refers to conventional Minecraft/Forge registry-driven biome and structure generation. A mod using custom feature generation, direct block placement, custom dimension logic, or special spawn-event placement may bypass these hooks and can require its own integration. This version does **not** claim arbitrary third-party mod compatibility without in-game testing. Already generated chunks are unaffected.

## Biome-specific structures

The Forge port checks a structure's allowed biome registry entries against the biomes enabled in the OmniIsle world. If **none** of the structure's permitted biomes remain enabled, its start is rejected. OmniIsle's custom fixed vanilla structure sets are also switched off when their explicitly required biome is disabled (and Ancient Cities require Deep Dark to be enabled). Land-only structure footprint protections for Ice and Fire are preserved. Modded ocean structures are not indiscriminately filtered out.

This applies to **registered Minecraft structures**. Mods that generate structures through features, block placement callbacks, or custom systems may require separate integrations. Already-generated chunks and structure starts are not retroactively removed.

For release validation, the CI client loads a test-only custom biome, selects it, verifies its datapack export and real biome-source sampling, checks that a biome-dependent structure is disabled when its required biome is switched off, and checks stable and contiguous modded biome regions, including mod-only categories. The test biome is not included in the distributable JAR.

## Installation / support

1. Download `OmniIsle-Forge-1.20.1` from the successful run's Artifacts and extract its JAR (not the artifact ZIP) into the `mods` directory of Minecraft 1.20.1 Forge 47.4.10.
2. Remove all prior OmniIsle Fabric, Connector, and experimental Forge JARs first. You do not need Sinytra Connector or Fabric API.
3. Create a **new test world** with world type OmniIsle; back up existing worlds before testing.
4. This release was automatically validated in Forge development client and installed dedicated-server environments. **Normal Windows launcher and full modpack compatibility are not yet proven.** For a Windows launch failure, attach the latest complete `logs/debug.log` and the crash report or launcher exit/console log; logs that stop before mod discovery cannot establish which mod failed.

## Modded structure placement (Forge 1.20.1)

On an OmniIsle world, **land-only structures** can otherwise select starting chunks too close to the island coastline and carve into the surrounding sea. The native Forge port now supports the datapack structure tag `#omniisle:land_only`. Structures in this tag are rejected at start-generation time unless the start and eight points in a 96-block surrounding footprint are all on inland terrain. This is world-specific: it follows the current OmniIsle island preset, including customized editor masks.

Ice and Fire Community Edition land structures are included by default (dragon caves, roosts, cyclops/hydra caves, gorgon temples, graveyards, mausoleums and pixie villages). Ocean-specific features such as siren islands are deliberately **not** included. The IDs are optional; Ice and Fire is not a required dependency.

For another mod's land structures, include its **structure registry IDs** in `data/omniisle/tags/worldgen/structure/land_only.json` in your own datapack (do not replace the default list unless intentionally changing it). Example:

```json
{
  "replace": false,
  "values": [
    {"id": "anothermod:land_ruin", "required": false}
  ]
}
```

This prevents invalid starts; it **does not relocate** structures from ocean chunks to the island and cannot fix already generated chunks. Larger structures may require more than the current footprint margin, and mod-specific features not registered as Minecraft structures need separate integration. Keep backups and test with a new world or newly generated chunks.

## Licensing

Upstream GitHub source is distributed under GPL-3.0. Retain copyright notices and the GPL license when porting. The separately distributed 1.20.1 Fabric JAR carries a different license declaration in its metadata, so maintain GPL compliance for public distribution and check upstream licensing details. This is an unofficial port.
