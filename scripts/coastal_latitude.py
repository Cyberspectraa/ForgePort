#!/usr/bin/env python3
"""Protect the visible sand/snow beach rim and reinforce latitude in both preview and worldgen.

Applied after coherent_modded_biomes.py and automatic_biome_replacements.py.
Keep the original land shape, islands, coast continentalness thresholds, opt-outs,
structure rules, and native large biome regions.
"""

# Vanilla shore must frame the exterior coastline even if an enabled mod adds
# shore variants such as Blooming Biosphere's tidepools. Reserve the outer
# coastal shelf (continentalness -0.30 .. -0.08); leave the inner shore open
# for the mod's native-region biome substitution. This check is on the actual
# biome resolver, not only the editor's colour palette.
coastal_java = JAVA / "worldgen/CoastalBiomeBands.java"
coastal_java.write_text("""package com.hack337.omniisle.worldgen;

/** Preserve the seaward part of the natural beach without changing terrain. */
public final class CoastalBiomeBands {
    private CoastalBiomeBands() {}
    public static boolean preserveNativeRim(double continentalness) {
        return continentalness >= -0.30 && continentalness < -0.08;
    }
}
""", encoding="utf-8")

patch_once("worldgen/OmniBiomeSource.java",
    """        Holder<Biome> base = originalNoiseBiome(biomeX, biomeY, biomeZ, sampler);
        String replacement = base.unwrapKey().map(key ->""",
    """        Holder<Biome> base = originalNoiseBiome(biomeX, biomeY, biomeZ, sampler);
        // Keep the outer sandy / snowy / stony shoreline visible even when
        // an installed mod supplies a matching coastal replacement. Inward
        // shore sections can still use Tidepools or manual modded coast biomes.
        // Disabled native shore biomes are never forced back into the palette.
        if (enabledShoreBiomes.contains(base)
                && base.unwrapKey().map(key ->
                    "minecraft".equals(key.location().getNamespace())).orElse(false)
                && CoastalBiomeBands.preserveNativeRim(
                    net.minecraft.world.level.biome.Climate.unquantizeCoord(
                        sampler.sample(biomeX, biomeY, biomeZ).continentalness())))
            return base;
        String replacement = base.unwrapKey().map(key ->""")

# Editor bitmap coast is two pixels wide on the land side. At one-pixel
# distance from water it represents the protected seaward beach. The inner
# portion still shows any modded beach alternatives in the correct climate.
patch_once("client/OmniIsleEditorScreen.java",
    """                int color = state.previewColor(state.selectBiome(preferred, state.worldX(x), state.worldZ(z)),
                    state.worldX(x), state.worldZ(z));
                image.setPixelRGBA(x, z, argbToAbgr(color));""",
    """                BiomePreview.Type nativeChoice = state.selectBiome(preferred, state.worldX(x), state.worldZ(z));
                int color = state.previewColor(nativeChoice, state.worldX(x), state.worldZ(z));
                if (land && preferred.category == BiomePreview.Category.SHORE
                        && hasOppositeNearby(x, z, true, 1)
                        && !state.enabledBiomes(BiomePreview.Category.SHORE).isEmpty())
                    color = nativeChoice.color; // seaward sand/snow/stone border
                image.setPixelRGBA(x, z, argbToAbgr(color));""")

# Original temperature latitude already points north=-Z, south=+Z, but
# excess noise produces warm northern pockets and humid hot southern areas.
# Stronger global latitude and less fine noise makes north reliably cold
# and south reliably arid while keeping temperate transitions in the middle.
patch_once("worldgen/OmniBiomeSource.java",
    """double temperature = clamp01(0.50 + wz / 3200.0 + fbm(wx / (scale * 1.35), wz / (scale * 1.35), saltedSeed(biomeSeed, 307)) * 0.17);""",
    """double temperature = clamp01(0.50 + wz / 2600.0 + fbm(wx / (scale * 1.35), wz / (scale * 1.35), saltedSeed(biomeSeed, 307)) * 0.10);""")
patch_once("client/BiomePreview.java",
    """double temperature = clamp01(0.50 + wz / 3200.0 + fbm(wx / (scale * 1.35), wz / (scale * 1.35), saltedSeed(seed, 307)) * 0.17);""",
    """double temperature = clamp01(0.50 + wz / 2600.0 + fbm(wx / (scale * 1.35), wz / (scale * 1.35), saltedSeed(seed, 307)) * 0.10);""")

# Distinct sandy southern belt with occasional dry badlands, ahead of the
# mountain branch. If desert/badlands are disabled, existing fallback logic
# chooses an enabled land biome; never resurrect a deselected vanilla biome.
patch_once("worldgen/OmniBiomeSource.java",
    """        if (continentalness > 0.18 && c.mountains > 0.68) {""",
    """        if (c.temperature > 0.84)
            return c.humidity > 0.76 ? enabledLand(13, x, z) : enabledLand(12, x, z);

        if (continentalness > 0.18 && c.mountains > 0.68) {""")
patch_once("client/BiomePreview.java",
    """        if (continentalness > 0.18 && c.mountains > 0.68) {""",
    """        if (c.temperature > 0.84)
            return c.humidity > 0.76 ? Type.BADLANDS : Type.DESERT;
        if (continentalness > 0.18 && c.mountains > 0.68) {""")

print("Natural beach rim and north-to-south climate bands applied.")
