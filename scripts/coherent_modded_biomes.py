#!/usr/bin/env python3
"""Reuse OmniIsle's native climate regions and import explicit Overworld replacements.

Runs after biome_generation.py. The separate 310-block Voronoi mosaic is removed.
"""

# The base OmniIsle algorithm already generates large curved temperature,
# moisture and terrain regions. A manually selected mod biome should share one
# of those native regions, not paint a second checkerboard over the island.
# The selection is stable per native biome ID (and seed), so it NEVER introduces
# an extra spatial boundary inside that vanilla biome's contiguous patches.
patches = JAVA / "worldgen/ModdedBiomePatches.java"
patches.write_text("""package com.hack337.omniisle.worldgen;

import java.util.List;

/** Shares exactly the native OmniIsle climate region boundaries. */
public final class ModdedBiomePatches {
    private ModdedBiomePatches() {}

    /**
     * For a native biome climate region return one compatible enabled mod
     * biome, or -1 to keep the original. Stable across the whole region.
     */
    public static int forBase(String nativeId, List<String> mods, long seed, int category) {
        if (mods.isEmpty()) return -1;
        int baseClimate = climate(nativeId);
        java.util.ArrayList<Integer> compatible = new java.util.ArrayList<>();
        for (int i = 0; i < mods.size(); i++) {
            if (category != 0 || baseClimate == 0 || climate(mods.get(i)) == 0
                    || baseClimate == climate(mods.get(i))) {
                compatible.add(i);
            }
        }
        if (compatible.isEmpty()) return -1;
        long hash = scramble(seed ^ nativeId.hashCode() * 0x9e3779b97f4a7c15L
            ^ category * 0xc2b2ae3d27d4eb4fL);
        // Two native slots avoid exhausting the recognizable vanilla regions.
        int choice = (int)Math.floorMod(hash, (long)compatible.size() + 2L);
        return choice < 2 ? -1 : compatible.get(choice - 2);
    }

    /**
     * Cold / mild / hot grouping. Unknown mod names stay eligible rather than
     * silently suppressing a biome whose climate naming we don't recognise.
     * This is only a conservative broad-climate check, not fake biome metadata.
     */
    private static int climate(String id) {
        String path = id.substring(id.indexOf(':') + 1);
        if (contains(path, "snow", "frozen", "ice_", "icy", "glacier", "tundra",
                "cold", "alpine", "dread")) return 1;
        if (contains(path, "desert", "badlands", "savanna", "rainforest", "tropic",
                "jungle", "chaparral", "arid", "hot", "volcanic")) return 3;
        if (contains(path, "plains", "forest", "woodland", "grove", "swamp",
                "marsh", "taiga", "meadow", "autumn", "birch", "cherry")) return 2;
        return 0;
    }

    private static boolean contains(String path, String... parts) {
        for (String part : parts) if (path.contains(part)) return true;
        return false;
    }

    /** Retained for mod-only categories: the original climate patch owns them. */
    public static int modOnlyIndex(int x, int z, long seed, int count, int category) {
        if (count <= 0) return -1;
        return (int)Math.floorMod(scramble(seed ^ ((long)x / 768) * 0x9e3779b97f4a7c15L
            ^ ((long)z / 768) * 0xc2b2ae3d27d4eb4fL ^ category), count);
    }

    // Compatibility helper for saved older previews and historical tests.
    public static int index(int x, int z, long seed, int count, int category) {
        if (count <= 0) return -1;
        return Math.floorMod((int)scramble(seed ^ (((long)x / 768) << 32)
            ^ ((long)z / 768) ^ category), count + 1) - 1;
    }

    private static long scramble(long n) {
        n = (n ^ (n >>> 30)) * 0xbf58476d1ce4e5b9L;
        n = (n ^ (n >>> 27)) * 0x94d049bb133111ebL;
        return n ^ (n >>> 31);
    }
}
""", encoding="utf-8")

# Preserve original native selection in mod-only categories too: it already
# uses climate-aware landBiome()/choosePatch() and has no injected grid.
patch_once("worldgen/OmniBiomeSource.java",
    """        if (extra.isEmpty()) return base;
        boolean modOnly = switch (category) {
            case 0 -> enabledLandBiomes.size() == extra.size();
            case 1 -> enabledShoreBiomes.size() == extra.size();
            case 2 -> enabledOceanBiomes.size() == extra.size();
            case 3 -> enabledRiverBiomes.size() == extra.size();
            default -> enabledCaveBiomes.size() == extra.size();
        };
        int index = modOnly
            ? ModdedBiomePatches.modOnlyIndex(biomeX << 2, biomeZ << 2, biomeSeed, extra.size(), category)
            : ModdedBiomePatches.index(biomeX << 2, biomeZ << 2, biomeSeed, extra.size(), category);
        return index < 0 ? base : extra.get(index);""",
    """        if (extra.isEmpty()) return base;
        // All-modded category: originalNoiseBiome already chose among the
        // registered mod biome holders using native climate/patch logic.
        if (switch (category) {
            case 0 -> enabledLandBiomes.size() == extra.size();
            case 1 -> enabledShoreBiomes.size() == extra.size();
            case 2 -> enabledOceanBiomes.size() == extra.size();
            case 3 -> enabledRiverBiomes.size() == extra.size();
            default -> enabledCaveBiomes.size() == extra.size();
        }) return base;

        List<String> ids = extra.stream().map(holder -> holder.unwrapKey()
            .map(key -> key.location().toString()).orElse("")).toList();
        String nativeId = base.unwrapKey().map(key -> key.location().toString()).orElse("");
        int index = ModdedBiomePatches.forBase(nativeId, ids, biomeSeed, category);
        return index < 0 ? base : extra.get(index);""")
patch_once("client/IslandDraft.java",
    """        int index = enabledBiomes(vanilla.category).isEmpty()
            ? com.hack337.omniisle.worldgen.ModdedBiomePatches.modOnlyIndex(
                (int)worldX, (int)worldZ, biomeSeed, mods.size(), vanilla.category.ordinal())
            : com.hack337.omniisle.worldgen.ModdedBiomePatches.index(
                (int)worldX, (int)worldZ, biomeSeed, mods.size(), vanilla.category.ordinal());
        if (index < 0) return vanilla.color;""",
    """        if (enabledBiomes(vanilla.category).isEmpty()) return vanilla.color;
        int index = com.hack337.omniisle.worldgen.ModdedBiomePatches.forBase(
            vanilla.biomeId(), java.util.List.copyOf(mods), biomeSeed, vanilla.category.ordinal());
        if (index < 0) return vanilla.color;""")

# A mod that deliberately replaces minecraft:forest via data/minecraft/
# worldgen/biome/forest.json is already automatic: it keeps the vanilla registry
# ID. For new registry IDs, be conservative: only import them automatically when
# the supplying mod explicitly places them in its minecraft:overworld dimension
# biome-source mapping. Do not auto-import IceAndFire's separate Dread dimension.
auto = JAVA / "client/AutomaticOverworldBiomes.java"
auto.write_text("""package com.hack337.omniisle.client;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.EnumMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipFile;
import net.minecraftforge.fml.ModList;

/** Reads explicit Overworld biome-source declarations from installed mod JARs. */
public final class AutomaticOverworldBiomes {
    private AutomaticOverworldBiomes() {}
    private static final org.slf4j.Logger LOG =
        org.slf4j.LoggerFactory.getLogger("OmniIsle");
    private static volatile Map<BiomePreview.Category, Set<String>> cached;

    public static Map<BiomePreview.Category, Set<String>> discover() {
        Map<BiomePreview.Category, Set<String>> ready = cached;
        if (ready != null) return ready;
        synchronized (AutomaticOverworldBiomes.class) {
            if (cached != null) return cached;
            EnumMap<BiomePreview.Category, Set<String>> result =
                new EnumMap<>(BiomePreview.Category.class);
            for (BiomePreview.Category category : BiomePreview.Category.values())
                result.put(category, new LinkedHashSet<>());

            java.util.HashSet<Path> visited = new java.util.HashSet<>();
            for (var mod : ModList.get().getMods()) {
                Path path = mod.getOwningFile().getFile().getFilePath();
                if (!visited.add(path) || !path.toString().endsWith(".jar")) continue;
                try (ZipFile jar = new ZipFile(path.toFile())) {
                    var dimensionFile = jar.getEntry("data/minecraft/dimension/overworld.json");
                    if (dimensionFile == null) continue;
                    try (var input = jar.getInputStream(dimensionFile)) {
                        JsonObject root = JsonParser.parseString(
                            new String(input.readAllBytes(), StandardCharsets.UTF_8)).getAsJsonObject();
                        JsonObject generator = root.getAsJsonObject("generator");
                        if (generator == null) continue;
                        JsonObject biomeSource = generator.getAsJsonObject("biome_source");
                        if (biomeSource == null || !biomeSource.has("biomes")
                                || !biomeSource.get("biomes").isJsonArray()) continue;
                        for (JsonElement point : biomeSource.getAsJsonArray("biomes")) {
                            if (!point.isJsonObject()) continue;
                            JsonElement element = point.getAsJsonObject().get("biome");
                            if (element == null || !element.isJsonPrimitive()) continue;
                            String id = element.getAsString();
                            if (!id.contains(":") || id.startsWith("minecraft:")
                                    || id.equals("terrablender:deferred_placeholder")) continue;
                            result.get(classify(id)).add(id);
                        }
                    }
                } catch (Exception ex) {
                    LOG.warn("Could not inspect mod's explicit Overworld biome mapping: {}", path.getFileName(), ex);
                }
            }
            EnumMap<BiomePreview.Category, Set<String>> immutable =
                new EnumMap<>(BiomePreview.Category.class);
            result.forEach((k, v) -> immutable.put(k,
                java.util.Collections.unmodifiableSet(new LinkedHashSet<>(v))));
            cached = Map.copyOf(immutable);
            if (result.values().stream().anyMatch(set -> !set.isEmpty()))
                LOG.info("Recognized explicitly declared Overworld replacement biomes: {}", result);
            return cached;
        }
    }

    public static boolean automatic(String id) {
        return discover().values().stream().anyMatch(set -> set.contains(id));
    }

    public static void apply(IslandDraft draft) {
        discover().forEach((category, ids) -> {
            // Idempotent; don't flip an already-active checkbox OFF.
            for (String id : ids) if (!draft.isCustomBiomeEnabled(id, category))
                draft.toggleCustomBiome(id, category);
        });
    }

    private static BiomePreview.Category classify(String id) {
        String path = id.substring(id.indexOf(':') + 1).toLowerCase(java.util.Locale.ROOT);
        if (path.contains("tidepool") || path.contains("beach") ||
                path.contains("shore") || path.contains("coast"))
            return BiomePreview.Category.SHORE;
        if (path.contains("ocean") || path.contains("reef") || path.contains("sea_"))
            return BiomePreview.Category.OCEAN;
        if (path.contains("river")) return BiomePreview.Category.RIVER;
        if (path.contains("cave") || path.contains("underground"))
            return BiomePreview.Category.CAVE;
        return BiomePreview.Category.LAND;
    }
}
""", encoding="utf-8")

patch_once("client/OmniIsleEditorScreen.java",
    """        this.state = EditorDraftStore.openDraft(parent);""",
    """        this.state = EditorDraftStore.openDraft(parent);
        AutomaticOverworldBiomes.apply(this.state);""")
patch_once("client/WorldPackBuilder.java",
    """        IslandDraft state = source.copy();""",
    """        IslandDraft state = source.copy();
        AutomaticOverworldBiomes.apply(state);""")
patch_once("client/ModdedBiomeScreen.java",
    """            .filter(id -> !("terrablender".equals(id.getNamespace())
                && "deferred_placeholder".equals(id.getPath())))""",
    """            .filter(id -> !("terrablender".equals(id.getNamespace())
                && "deferred_placeholder".equals(id.getPath())))
            // These are automatic because the mod explicitly replaced the
            // Overworld biome map; they are not manual opt-in choices.
            .filter(id -> !AutomaticOverworldBiomes.automatic(id.toString()))""")

print("Modded biome selection now follows native climate regions; explicit Overworld biome entries auto-import.")
