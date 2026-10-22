#!/usr/bin/env python3
"""Integrate replacement-style worldgen biomes with OmniIsle climate families.

Blooming Biosphere 1.1.0 provides a full Overworld multi_noise biome source,
not merely stand-alone opt-in biomes. The island generator must not install that
competing noise source, but may inherit its replacement biome identities in the
existing climate regions without imposing a tiny, random checkerboard.
"""

# The replacement mapping is explicit and reviewable, not inferred from the
# existence of an arbitrary registered biome. Some mods register biomes used
# only in separate dimensions. Never auto-enable those.
bridge = JAVA / "worldgen/AutomaticBiomeReplacements.java"
bridge.write_text("""package com.hack337.omniisle.worldgen;

import com.hack337.omniisle.client.BiomePreview;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraftforge.fml.ModList;

/**
 * Recognized mods explicitly replacing/expanding the standard Overworld
 * biome distribution. Only enable when the original climate family is active.
 *
 * Other mods' unique biomes remain opt-in: their presence in a registry alone
 * is NOT evidence that they should generate in the Overworld.
 */
public final class AutomaticBiomeReplacements {
    private AutomaticBiomeReplacements() {}

    // Mapping inferred from Blooming Biosphere 1.1.0's own overworld.json
    // multi_noise climate points and vanilla biome equivalents.
    private static final Map<String, String> BLOOMING = Map.ofEntries(
        Map.entry("minecraft:forest", "blooming_biosphere:oak_woodland"),
        Map.entry("minecraft:taiga", "blooming_biosphere:autumnal_forest"),
        Map.entry("minecraft:swamp", "blooming_biosphere:marsh"),
        Map.entry("minecraft:jungle", "blooming_biosphere:rainforest"),
        Map.entry("minecraft:savanna", "blooming_biosphere:chaparral"),
        Map.entry("minecraft:snowy_plains", "blooming_biosphere:snowy_cherry_grove"),
        Map.entry("minecraft:beach", "blooming_biosphere:tidepools")
    );

    public static boolean active() {
        return ModList.get().isLoaded("mr_blooming_biosphere");
    }

    public static String mappedId(String base) {
        return active() ? BLOOMING.get(base) : null;
    }

    public static boolean isAutomatic(String id) {
        return active() && BLOOMING.containsValue(id);
    }

    public static Map<String, String> all() {
        return active() ? BLOOMING : Map.of();
    }
}
""", encoding="utf-8")

# The editor exports biome IDs only for selected vanilla biome families. New
# replacement biomes are included automatically; no Mods-tab check required.
patch_once("client/IslandDraft.java",
    """        ids.addAll(customBiomeIds(category));
        return java.util.List.copyOf(ids);""",
    """        for (BiomePreview.Type type : enabledBiomes(category)) {
            String replacement = com.hack337.omniisle.worldgen.AutomaticBiomeReplacements.mappedId(type.biomeId());
            if (replacement != null && !ids.contains(replacement)) ids.add(replacement);
        }
        ids.addAll(customBiomeIds(category).stream().filter(id -> !ids.contains(id)).toList());
        return java.util.List.copyOf(ids);""")

# Use the same visible climate regions in the preview rather than a randomized
# Voronoi tile overlay for automatic replacements.
patch_once("client/IslandDraft.java",
    """        java.util.LinkedHashSet<String> mods = customBiomes.get(vanilla.category);
        if (mods == null || mods.isEmpty()) return vanilla.color;""",
    """        String mapped = com.hack337.omniisle.worldgen.AutomaticBiomeReplacements.mappedId(vanilla.biomeId());
        if (mapped != null && enabledBiomes.contains(vanilla)) {
            int rgb = mapped.hashCode();
            return 0xFF000000 | (0x50 + ((rgb >>> 16) & 0x4F)) << 16
                | (0x60 + ((rgb >>> 8) & 0x5F)) << 8 | (0x40 + (rgb & 0x5F));
        }
        java.util.LinkedHashSet<String> mods = customBiomes.get(vanilla.category);
        if (mods == null || mods.isEmpty()) return vanilla.color;""")

# Mapped replacement biomes should NOT join the random patch pool: they are
# selected whenever their associated vanilla climate region is selected.
patch_once("worldgen/OmniBiomeSource.java",
    """        Holder<Biome> base = originalNoiseBiome(biomeX, biomeY, biomeZ, sampler);
        List<Holder<Biome>> extra;""",
    """        Holder<Biome> base = originalNoiseBiome(biomeX, biomeY, biomeZ, sampler);
        String replacement = base.unwrapKey().map(key ->
            AutomaticBiomeReplacements.mappedId(key.location().toString())).orElse(null);
        if (replacement != null) {
            for (Holder<Biome> holder : Stream.of(enabledLandBiomes, enabledShoreBiomes,
                    enabledOceanBiomes, enabledRiverBiomes, enabledCaveBiomes)
                    .flatMap(List::stream).toList()) {
                if (holder.unwrapKey().map(key ->
                        key.location().toString().equals(replacement)).orElse(false)) {
                    return holder;
                }
            }
        }
        List<Holder<Biome>> extra;""")
patch_once("worldgen/OmniBiomeSource.java",
    """            .map(key -> !"minecraft".equals(key.location().getNamespace())).orElse(false)).toList();""",
    """            .map(key -> !"minecraft".equals(key.location().getNamespace())
                && !AutomaticBiomeReplacements.isAutomatic(key.location().toString()))
            .orElse(false)).toList();""")

# Hide auto replacements from the manual picker to prevent redundant choices.
patch_once("client/ModdedBiomeScreen.java",
    """            .sorted(Comparator.comparing(ResourceLocation::toString)).toList();""",
    """            .filter(id -> !com.hack337.omniisle.worldgen.AutomaticBiomeReplacements.isAutomatic(
                id.toString()))
            .sorted(Comparator.comparing(ResourceLocation::toString)).toList();""")
print("Automatic Blooming Biosphere climate-family replacements installed.")
