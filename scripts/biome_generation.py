#!/usr/bin/env python3
"""Registry-driven biome integration and structure compatibility.

No per-biome weighting controls: the editor's enabled/disabled choices are
authoritative. Vanilla-only worlds keep the original climate algorithm.
This script executes after modded_biomes.py during Forge conversion.
"""

# Preserve inference for standard registered land-only structures; retain
# the explicit larger-footprint Ice & Fire / datapack structure tag.
patch_once("worldgen/OmniBiomeSource.java",
    """    @Override
    protected Stream<Holder<Biome>> collectPossibleBiomes() {""",
    """    public boolean allowsLandOnly(net.minecraft.core.HolderSet<Biome> allowed) {
        boolean hasLand = allowed.stream().anyMatch(enabledLandBiomes::contains);
        boolean hasMarine = allowed.stream().anyMatch(h -> enabledOceanBiomes.contains(h)
            || enabledShoreBiomes.contains(h) || enabledRiverBiomes.contains(h)
            || enabledCaveBiomes.contains(h));
        return hasLand && !hasMarine;
    }

    @Override
    protected Stream<Holder<Biome>> collectPossibleBiomes() {""")
patch_once("mixin/client/StructureLandGuardMixin.java",
    """        if (holder.isEmpty() || !holder.get().is(OMNI_LAND_ONLY)) return;

        int x = chunkPos.getMiddleBlockX();""",
    """        boolean explicitlyLandOnly = holder.isPresent() && holder.get().is(OMNI_LAND_ONLY);
        boolean inferredLandOnly = ((OmniBiomeSource) biomeSource).allowsLandOnly(structure.biomes());
        if (!explicitlyLandOnly && !inferredLandOnly) return;

        int x = chunkPos.getMiddleBlockX();""")
patch_once("mixin/client/StructureLandGuardMixin.java",
    """        int margin = FOOTPRINT_MARGIN;""",
    """        int margin = explicitlyLandOnly ? FOOTPRINT_MARGIN : 48;""")

# Smooth organic, seed-stable biome regions instead of previous noisy patch
# thresholds, which clustered around middle-index custom biomes and could
# starve first and last entries. Region assignment uses a uniform hash, so
# every registered mod biome has an equal opportunity to appear.
patches = JAVA / "worldgen/ModdedBiomePatches.java"
patches.write_text("""package com.hack337.omniisle.worldgen;

/**
 * Smooth, deterministic regions for installed mod biomes.
 * Used by both the editor preview and the worldgen biome source.
 * Zero configured mod biomes -> no change to the original climate layout.
 */
public final class ModdedBiomePatches {
    private ModdedBiomePatches() {}
    private static final int CELL_SIZE = 310;

    /** -1 leaves the existing vanilla climate biome in place. */
    public static int index(int x, int z, long seed, int count, int category) {
        if (count <= 0) return -1;
        long region = regionHash(x, z, seed, category);
        // Several ordinary-climate regions for each mod biome: keeps the
        // overall island recognizable without burying the custom biomes.
        // Additional selected mod biomes receive their own equal-sized regions.
        int roll = (int)Math.floorMod(mix(region + 0x41f9a6d217bL), (long)count + 3L);
        return roll < 3 ? -1 : roll - 3;
    }

    /** Used when a category has ONLY modded biomes: never return vanilla. */
    public static int modOnlyIndex(int x, int z, long seed, int count, int category) {
        if (count <= 0) return -1;
        return (int)Math.floorMod(mix(regionHash(x, z, seed, category) + 0x41f9a6d217bL), count);
    }

    private static long regionHash(int x, int z, long seed, int category) {
        double warpedX = x + 75.0 * noise(x / 925.0, z / 925.0, seed + category * 571L);
        double warpedZ = z + 75.0 * noise(x / 925.0 + 37.0, z / 925.0 - 71.0,
            seed + category * 571L + 11L);
        int cellX = (int)Math.floor(warpedX / CELL_SIZE);
        int cellZ = (int)Math.floor(warpedZ / CELL_SIZE);
        double best = Double.MAX_VALUE;
        long nearest = 0;
        for (int dz = -1; dz <= 1; dz++) {
            for (int dx = -1; dx <= 1; dx++) {
                int gx = cellX + dx, gz = cellZ + dz;
                long h = hash(gx, gz, seed + category * 3571L);
                double px = (gx + 0.1 + unit(h) * 0.8) * CELL_SIZE;
                double pz = (gz + 0.1 + unit(mix(h + 0x9e3779b97f4a7c15L)) * 0.8)
                    * CELL_SIZE;
                double distX = px - warpedX, distZ = pz - warpedZ;
                double distance = distX * distX + distZ * distZ;
                if (distance < best) {
                    best = distance;
                    nearest = h;
                }
            }
        }
        return nearest;
    }

    private static double noise(double x, double z, long seed) {
        int ix = (int)Math.floor(x), iz = (int)Math.floor(z);
        double fx = x - ix, fz = z - iz;
        fx = fx * fx * (3.0 - 2.0 * fx);
        fz = fz * fz * (3.0 - 2.0 * fz);
        double a = lerp(unit(hash(ix, iz, seed)), unit(hash(ix + 1, iz, seed)), fx);
        double b = lerp(unit(hash(ix, iz + 1, seed)),
            unit(hash(ix + 1, iz + 1, seed)), fx);
        return 2.0 * lerp(a, b, fz) - 1.0;
    }

    private static double unit(long value) {
        return (value >>> 11) * 0x1.0p-53;
    }

    private static double lerp(double a, double b, double t) { return a + (b - a) * t; }

    private static long hash(long x, long z, long seed) {
        return mix(seed ^ (x * 0x9e3779b97f4a7c15L)
            ^ (z * 0xc2b2ae3d27d4eb4fL));
    }

    private static long mix(long value) {
        value = (value ^ (value >>> 30)) * 0xbf58476d1ce4e5b9L;
        value = (value ^ (value >>> 27)) * 0x94d049bb133111ebL;
        return value ^ (value >>> 31);
    }
}
""", encoding="utf-8")

# The old sampler returned the first mod biome for most regions when all
# vanilla biomes in the category had been disabled. Select ONLY modded biomes
# in that case, with consistent preview and worldgen.
patch_once("worldgen/OmniBiomeSource.java",
    """        int index = ModdedBiomePatches.index(biomeX << 2, biomeZ << 2, biomeSeed, extra.size(), category);
        return index < 0 ? base : extra.get(index);""",
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
        return index < 0 ? base : extra.get(index);""")
patch_once("client/IslandDraft.java",
    """        int index = com.hack337.omniisle.worldgen.ModdedBiomePatches.index(
            (int)worldX, (int)worldZ, biomeSeed, mods.size(), vanilla.category.ordinal());
        if (index < 0) return vanilla.color;""",
    """        int index = enabledBiomes(vanilla.category).isEmpty()
            ? com.hack337.omniisle.worldgen.ModdedBiomePatches.modOnlyIndex(
                (int)worldX, (int)worldZ, biomeSeed, mods.size(), vanilla.category.ordinal())
            : com.hack337.omniisle.worldgen.ModdedBiomePatches.index(
                (int)worldX, (int)worldZ, biomeSeed, mods.size(), vanilla.category.ordinal());
        if (index < 0) return vanilla.color;""")
# A completely mod-only land category has no compatible vanilla choices.
# Keep a surrogate climate preference for the UI rather than crashing on
# empty lists; previewColor always displays the actual selected mod region.
patch_once("client/IslandDraft.java",
    """        List<BiomePreview.Type> compatible = compatibleChoices(preferred);
        if (compatible.size() == 1) return compatible.get(0);""",
    """        List<BiomePreview.Type> compatible = compatibleChoices(preferred);
        if (compatible.isEmpty()) return preferred;
        if (compatible.size() == 1) return compatible.get(0);""")
# Structure set export uses vanilla climate preview samples; when all
# vanilla land biomes are disabled, skip fixed structures with no eligible
# vanilla placement rather than failing world creation. Registry-driven
# modded structures still spawn by their proper biome predicates.
patch_once("client/WorldPackBuilder.java",
    """            boolean enabled = state.isStructureEnabled(IslandDraft.StructureOption.values()[structureIndex])
                && (generic || state.isAnyRequiredBiomeEnabled(definition.biomes))
                && (!definition.deepDark || state.isBiomeEnabled(BiomePreview.Type.DEEP_DARK));""",
    """            boolean eligibleBiomes = definition.biomes.stream()
                .anyMatch(type -> !state.compatibleChoices(type).isEmpty());
            boolean enabled = state.isStructureEnabled(IslandDraft.StructureOption.values()[structureIndex])
                && eligibleBiomes
                && (generic || state.isAnyRequiredBiomeEnabled(definition.biomes))
                && (!definition.deepDark || state.isBiomeEnabled(BiomePreview.Type.DEEP_DARK));""")

# A biome ID, by itself, cannot provide biome-specific dirt, rock or custom
# surface materials. TerraBlender uses an optional extended NoiseGeneratorSettings
# mixin to attach namespace-aware surface rules to its Overworld generator. Our
# bespoke OmniIsle noise settings were never marked as an Overworld generator,
# so surface rules from mods depending on TerraBlender did not run.
#
# Fix: mark ONLY OmniIsle's chunk generator settings as Overworld terrain
# before chunks generate. Reflection keeps TerraBlender an optional dependency.
# Noise density and island shape are not modified.
surface = JAVA / "mixin/client/TerraBlenderSurfaceMixin.java"
surface.write_text("""package com.hack337.omniisle.mixin.client;

import com.hack337.omniisle.worldgen.OmniBiomeSource;
import java.lang.reflect.Method;
import net.minecraft.core.Holder;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraftforge.fml.ModList;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Opt-in interop with TerraBlender 3.x, which gates its biome surface rules
 * behind an Overworld region marker on NoiseGeneratorSettings.
 *
 * OmniIsle uses a custom registered noise settings entry; without this marker,
 * namespace-specific ground/topsoil rules are silently skipped despite a
 * correctly reported biome ID. Never modify non-OmniIsle generators.
 */
@Mixin(NoiseBasedChunkGenerator.class)
public abstract class TerraBlenderSurfaceMixin {
    @Inject(method = "<init>", at = @At("RETURN"))
    private void omniisle$enableModdedSurfaces(
        BiomeSource biomeSource,
        Holder<NoiseGeneratorSettings> settings,
        CallbackInfo ci
    ) {
        if (!(biomeSource instanceof OmniBiomeSource)) return;
        if (!ModList.get().isLoaded("terrablender")) return;
        try {
            Class<?> extended = Class.forName("terrablender.worldgen.IExtendedNoiseGeneratorSettings");
            Class<?> region = Class.forName("terrablender.api.RegionType");
            NoiseGeneratorSettings actualSettings = settings.value();
            if (!extended.isInstance(actualSettings)) return;
            @SuppressWarnings({"unchecked", "rawtypes"})
            Object overworld = Enum.valueOf((Class<? extends Enum>) region.asSubclass(Enum.class), "OVERWORLD");
            Method setter = extended.getMethod("setRegionType", region);
            setter.invoke(actualSettings, overworld);
            org.slf4j.LoggerFactory.getLogger("OmniIsle").info(
                "OmniIsle TerraBlender biome surface rules activated");
        } catch (ReflectiveOperationException | LinkageError exception) {
            // Optional integration: a different TerraBlender version must not
            // crash or invalidate worlds that are otherwise working.
            org.slf4j.LoggerFactory.getLogger("OmniIsle").warn(
                "TerraBlender surface-rule bridge unavailable; modded biome surfaces may use vanilla blocks",
                exception);
        }
    }
}
""", encoding="utf-8")

mixins = RES / "omniisle.client.mixins.json"
import json
configuration = json.loads(mixins.read_text(encoding="utf-8"))
configuration["mixins"] = list(dict.fromkeys(
    [*configuration.get("mixins", []), "TerraBlenderSurfaceMixin"]))
mixins.write_text(json.dumps(configuration, indent=2) + "\n", encoding="utf-8")

print("Original biome selection preserved; improved organic mod biome regions and mod-only categories.")
