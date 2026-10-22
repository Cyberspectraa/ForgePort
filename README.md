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

## Feature-order cycle compatibility (mixed Forge modpacks)

Combining installed modded biomes with vanilla biomes can expose Minecraft's
`FeatureSorter` failure (`Feature order cycle found`). This was reproduced
by the real crash reports for `iceandfire:dread_forest` and
`minecraft:frozen_river` with Ice and Fire Community Edition 1.2.10.

OmniIsle keeps Minecraft's original feature order whenever it is valid. If a
feature-order cycle occurs in **an OmniIsle world only**, the fallback
constructs a deterministic, per-decoration-stage feature order from all enabled
biomes. It prioritizes original vanilla precedence and retains every feature
even if a conflicting ordering constraint must be skipped. No biome, vegetation,
or structure is disabled, and non-OmniIsle worlds retain vanilla behavior.
The server logs the number of ordering constraints skipped.

Regression coverage creates two deliberately conflicting registered mod biomes,
checks that vanilla `FeatureSorter` fails, and verifies recovery retains all
their placed features. Real-world validation should also be performed with the
original Ice and Fire Community Edition mod and the player's other worldgen mods.

## Native-region modded biomes and automatic vanilla replacements

The OmniIsle biome editor now integrates selected extra modded biomes into its
**existing broad, curving native biome regions** rather than painting a separate
310-block Voronoi grid over the island. When there are enough enabled native
climate slots, each selected mod biome occupies a whole compatible native
region, so the island retains the readable climate-zone layout seen with
vanilla biomes. Very large modded palettes can exceed the available native
slots; preserving broad regions takes priority over forcing every installed
biome to appear as a tiny patch. Mod-only categories instead use broader
roughly 1,500-block softly warped regions in both the editor preview and world.

Mods replacing the registered data for an existing `minecraft:` biome ID (for
example a replacement `data/minecraft/worldgen/biome/forest.json`) are
**already automatic**—that vanilla registry ID keeps the new decorations,
climate and other data. Mods that explicitly include *new biome IDs* in their
own `data/minecraft/dimension/overworld.json` multi-noise biome map (as
Blooming Biosphere does) are now automatically imported as Overworld biomes
without requiring manual checkboxes. Such automatically included entries
are omitted from the manual Mods tab. A mod defining entirely separate
dimensions does **not** have those biomes automatically injected into OmniIsle.
Manual opt-in remains for extra biomes not declared in an Overworld map.

This integration reuses **OmniIsle's** original terrain/climate boundaries;
it does not recreate the other mod's exact climate-noise parameter ranges.
The 1.20.1 Forge world-specific datapack still retains OmniIsle as the
Overworld generator and the existing biome/structure restrictions. Create a
new world or generate new chunks to compare regions; existing chunks will not
be reshaped retroactively.

## Modded biome appearance and terrain surfaces

A selected biome ID alone does not guarantee its intended ground blocks, trees or decorations. Minecraft separates the **biome registry** (climate, features, spawns, visual effects) from the **noise generator surface rules** (biome-specific topsoil, stones and material transitions). The OmniIsle world preset uses its own noise settings to keep the island shape.

For mods using **TerraBlender 3.x on Forge 1.20.1**, OmniIsle now marks its own noise-generator settings as Overworld settings when TerraBlender is installed. This lets TerraBlender apply the other mod's registered namespace-specific surface rules to OmniIsle, rather than showing that biome's ID with inappropriate default surface blocks. TerraBlender remains **optional**; the bridge does not modify the generator of other worlds or dimensions. The integration logs `OmniIsle TerraBlender biome surface rules activated` when it runs.

Surface rules are just one aspect of a biome's appearance. Mods that use a different surface-rule system, rely on their own terrain generator, require custom dimension logic, or use features with special placement predicates may still need an explicit adapter. In particular, the modded biome's **trees and configured features come from the original mod**, not from the name shown in F3. For a biome that still looks incorrect, capture the exact F3 `Biome: namespace:id`, the biome-owning mod and version, and a screenshot of the blocks and trees so its actual worldgen assets can be compared with OmniIsle.

## Compatibility with the October 2026 five-mod test set

OmniIsle was evaluated against these exact user-provided Forge 1.20.1 JARs:

* **Polytone 1.20-3.5.26:** Client-only biome colours and resource-pack visual effects. No terrain-generator adapter is appropriate; visual behaviour must be checked in-game with the user's actual resource packs.
* **Terrain Slabs 3.1.1:** Adds the `terrain_slabs:slab_feature_placed` feature to `#minecraft:is_overworld` at the `underground_structures` generation step. OmniIsle now tags each **enabled modded biome** as Overworld within the generated, world-specific datapack, allowing Terrain Slabs and similarly tagged Forge biome modifiers to target it. This never enables a biome the player disabled.
* **Smooth Steps 1.1.0:** Alters movement and camera handling, not biome or chunk generation; Architectury API 9.2.14 is required. It is not an alternative to Terrain Slabs.
* **RoadWeaver 2.1.1-1.20.1:** Adds highway and road placed features at `top_layer_modification`. Registered roads can execute in OmniIsle's Overworld; bridges, road targeting and performance still need in-game exploration of populated islands. Roads are not limited to the original fixed vanilla structure set.
* **Blooming Biosphere 1.1.0:** Replaces numerous `minecraft:` biome definitions, adds seven `blooming_biosphere:` biomes, and includes a competing `minecraft:overworld` dimension/noise definition. Vanilla biome **features** are available through their registries; new biomes are opt-in from **Mods** (e.g., Tidepools should go in Shore). Because Blooming Biosphere ships a competing `data/minecraft/dimension/overworld.json`, the OmniIsle editor now includes **the matching Overworld dimension entry in its world-specific generated datapack**, at the same time as the island world preset. This preserves OmniIsle's island noise and enabled biome selections while using compatible Blooming biome features. Do not make this a global mod asset: it would overwrite ordinary Overworld worlds. Blooming Biosphere's own biome distribution and terrain noise are not transplanted wholesale because that would destroy OmniIsle's island layout.

Run `scripts/verify_modpack_compat.py` to download matching public mod JARs with their uploaded SHA-512 fingerprints into a temporary CI test directory; the workflow uses them to test real Forge server startup and inspect the saved preset. These checks do **not** guarantee every road, slab or vegetation placement behaves identically to each standalone mod.

## Coastline ring and north-to-south climate

OmniIsle preserves a **seaward beach outline** around the landmass even when
Blooming Biosphere, or an optional shore biome, replaces parts of the inner
coastal climate region. The outer coast keeps the player's enabled native
sand, snowy beach or stony-shore biome; farther inland along the same shore,
automatically selected Tidepools may still appear. This is applied to real
quart-biome generation and represented in the editor's outer coastline pixel.
The underlying island geometry, water threshold and coastline mask are unchanged.

The shared editor-preview and worldgen climate now use a clearer north-to-south
temperature progression: cold snowy/taiga climates in the north, temperate
forests/plains/swamps between, and a predominantly desert/badlands climate
in the far south. Climate boundaries still curve organically and respect
per-world enabled/disabled biomes: a player who disables Desert will not
have Desert silently reintroduced. Mod-only land palettes retain their
separate compatibility limitations and may use broader stand-in regions.

A new world is required to see the new biome distribution in newly generated
chunks; existing world terrain is not rewritten.

## Organic modded biomes and automatic Overworld replacements

Optional modded biomes now use **larger, approximately 1,100-block warped
regions** rather than the former 310-block independent patch grid. This
reduces the patchwork effect in the editor and worldgen; optional modded
biomes are still only generated when explicitly selected.

**Blooming Biosphere 1.1.0 is different:** its datapack explicitly replaces
the Overworld biome distribution. With that mod installed, OmniIsle includes
its seven Overworld variants **automatically**, aligned with matching
selected vanilla climate regions rather than assigned random isolated cells.
The mappings cover its oak woodland, autumnal forest, marsh, rainforest,
chaparral, snowy cherry grove and tidepools biomes. They are not separate
Mods-tab selections. Disabling the associated vanilla biome also prevents
the corresponding automatic variant from being introduced, preserving
per-world biome opt-outs. The original island geometry and coastal placement
remain OmniIsle-controlled rather than replacing its world generator.

This integration is deliberately **opt-in per recognized mod**, not a blanket
rule that all registry biomes should generate: other mods may register biomes
for separate dimensions, structures or disabled content. New biomes from
such mods remain selectable in the Mods tab unless their owning mod has
an explicit Overworld replacement integration.

The editor preview uses the automatic climate-family mapping too. Existing
worlds are not retroactively repainted; test on a new world.

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
