#!/usr/bin/env python3
"""Keep Aquamirae 6.x's Ice Maze biome features in a northern offshore ocean.

Ice Maze is NOT a stand-alone biome or a land-only structure: Aquamirae 6.4
registers features on minecraft:frozen_ocean and deep_frozen_ocean through the
#aquamirae:ice_maze biome tag. Both require a contiguous biome region at sea.
Only apply with Aquamirae installed and at least one eligible vanilla frozen
ocean biome enabled. Explicitly disabled biomes stay disabled.
"""

f = JAVA / "worldgen/AquamiraeNorthOcean.java"
f.write_text("""package com.hack337.omniisle.worldgen;

import net.minecraftforge.fml.ModList;

/**
 * Retains the native frozen-ocean biome under Aquamirae's Ice Maze, rather
 * than permitting a later modded-ocean climate substitution in the north.
 *
 * The cold sea starts beyond the coastline, not on the shore or on land.
 * This does not inject Aquamirae structures or features: their owning mod
 * still controls all decorations and start placement.
 */
public final class AquamiraeNorthOcean {
    private AquamiraeNorthOcean() {}
    private static final java.util.concurrent.atomic.AtomicBoolean REPORTED =
        new java.util.concurrent.atomic.AtomicBoolean();

    public static void reportSelected(String biome) {
        if (REPORTED.compareAndSet(false, true)) {
            org.slf4j.LoggerFactory.getLogger("OmniIsle").info(
                "OmniIsle reserved northern frozen ocean for Aquamirae Ice Maze: {}", biome);
        }
    }
    public static boolean isNorthernMazeSea(double continentalness, int worldZ) {
        return continentalness < -0.30 && worldZ <= -700;
    }
    public static boolean installed() {
        return ModList.get().isLoaded("aquamirae");
    }
}
""", encoding="utf-8")

patch_once("worldgen/OmniBiomeSource.java",
    """        Holder<Biome> base = originalNoiseBiome(biomeX, biomeY, biomeZ, sampler);
        // Keep the outer sandy""",
    """        Holder<Biome> base = originalNoiseBiome(biomeX, biomeY, biomeZ, sampler);
        // Aquamirae Ice Maze decorates the ORIGINAL frozen-ocean biome ID,
        // not a modded ice-maze ID. Give the northern sea a contiguous
        // eligible biome instead of scattering/replacing its ocean climate.
        // Respect the editor: if both frozen oceans are disabled, do nothing.
        double oceanContinentalness = net.minecraft.world.level.biome.Climate.unquantizeCoord(
            sampler.sample(biomeX, biomeY, biomeZ).continentalness());
        if (AquamiraeNorthOcean.installed()
                && AquamiraeNorthOcean.isNorthernMazeSea(oceanContinentalness, biomeZ << 2)) {
            String priority = oceanContinentalness < -0.58
                ? "minecraft:deep_frozen_ocean" : "minecraft:frozen_ocean";
            for (String target : new String[] {priority, "minecraft:frozen_ocean",
                    "minecraft:deep_frozen_ocean"}) {
                for (Holder<Biome> candidate : enabledOceanBiomes) {
                    if (candidate.unwrapKey().map(key ->
                            key.location().toString().equals(target)).orElse(false)) {
                        AquamiraeNorthOcean.reportSelected(target);
                        return candidate;
                    }
                }
            }
        }
        // Keep the outer sandy""")

# Reflect the actual selected frozen ocean in the custom island editor.
patch_once("client/OmniIsleEditorScreen.java",
    """                int color = state.previewColor(nativeChoice, state.worldX(x), state.worldZ(z));
                if (land && preferred.category""",
    """                if (com.hack337.omniisle.worldgen.AquamiraeNorthOcean.installed()
                        && com.hack337.omniisle.worldgen.AquamiraeNorthOcean.isNorthernMazeSea(
                            continentalness, (int)state.worldZ(z))) {
                    if (continentalness < -0.58 && state.isBiomeEnabled(BiomePreview.Type.DEEP_FROZEN_OCEAN))
                        nativeChoice = BiomePreview.Type.DEEP_FROZEN_OCEAN;
                    else if (state.isBiomeEnabled(BiomePreview.Type.FROZEN_OCEAN))
                        nativeChoice = BiomePreview.Type.FROZEN_OCEAN;
                    else if (state.isBiomeEnabled(BiomePreview.Type.DEEP_FROZEN_OCEAN))
                        nativeChoice = BiomePreview.Type.DEEP_FROZEN_OCEAN;
                }
                int color = state.previewColor(nativeChoice, state.worldX(x), state.worldZ(z));
                if (land && preferred.category""")
print("Aquamirae northern offshore Ice Maze biome preservation installed.")
