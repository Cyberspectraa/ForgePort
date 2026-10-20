#!/usr/bin/env python3
"""Keep OmniIsle registered mod biomes when incompatible decoration order cycles.

Run after scripts/biome_generation.py. Only OmniIsle noise generators are
affected; vanilla worlds and other mod dimensions retain their usual sorter.
"""

# In a mixed Forge modpack some registered biomes specify the SAME placed
# features in contradictory orders. The vanilla FeatureSorter throws before
# the first chunks are decorated, even when both biomes generate perfectly
# valid terrain. This happened with IceAndFireCE dread_forest + frozen_river.
#
# Retain normal vanilla sorting whenever possible. If (and only if) the
# FeatureSorter fails with a feature order cycle on an OmniBiomeSource,
# rebuild a global, per-decoration-step ordering, respecting as many original
# precedence relationships as possible. The conflicting edge is skipped,
# but NO placed feature, biome, or decoration step is removed.
recovery = JAVA / "worldgen/OmniFeatureCycleRecovery.java"
recovery.write_text("""package com.hack337.omniisle.worldgen;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.function.Function;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.FeatureSorter;
import net.minecraft.world.level.levelgen.placement.PlacedFeature;

/**
 * Recover from conflicting registered biome feature orders without removing
 * modded features, changing biome identities or modifying global registries.
 *
 * Only used when the vanilla sorter throws on an OmniIsle world generator.
 * Earlier biome feature order edges are preferred; vanilla biome definitions
 * are considered before modded ones, for predictable conflict resolution.
 */
public final class OmniFeatureCycleRecovery {
    private static final org.slf4j.Logger LOG =
        org.slf4j.LoggerFactory.getLogger("OmniIsle");
    private OmniFeatureCycleRecovery() {}

    public static List<FeatureSorter.StepFeatureData> recover(
            Iterable<Holder<Biome>> possible,
            Function<Holder<Biome>, List<HolderSet<PlacedFeature>>> featuresFor) {
        List<Holder<Biome>> biomes = new ArrayList<>();
        possible.forEach(biomes::add);
        biomes.sort(Comparator.comparingInt((Holder<Biome> holder) ->
                holder.unwrapKey().map(key -> key.location().getNamespace().equals("minecraft") ? 0 : 1)
                    .orElse(2))
            .thenComparing(holder -> holder.unwrapKey()
                .map(key -> key.location().toString()).orElse("~")));

        List<List<List<PlacedFeature>>> perBiome = new ArrayList<>();
        int stepCount = 0;
        for (Holder<Biome> biome : biomes) {
            List<List<PlacedFeature>> steps = new ArrayList<>();
            for (HolderSet<PlacedFeature> step : featuresFor.apply(biome)) {
                List<PlacedFeature> entries = new ArrayList<>();
                for (Holder<PlacedFeature> holder : step) entries.add(holder.value());
                steps.add(entries);
            }
            perBiome.add(steps);
            stepCount = Math.max(stepCount, steps.size());
        }

        List<FeatureSorter.StepFeatureData> result = new ArrayList<>(stepCount);
        int droppedEdges = 0;
        for (int step = 0; step < stepCount; step++) {
            IdentityHashMap<PlacedFeature, List<PlacedFeature>> edges = new IdentityHashMap<>();
            IdentityHashMap<PlacedFeature, Integer> ranks = new IdentityHashMap<>();
            IdentityHashMap<PlacedFeature, Integer> incoming = new IdentityHashMap<>();
            List<PlacedFeature> all = new ArrayList<>();

            for (List<List<PlacedFeature>> biome : perBiome) {
                if (step >= biome.size()) continue;
                for (PlacedFeature feature : biome.get(step)) {
                    if (!ranks.containsKey(feature)) {
                        ranks.put(feature, all.size());
                        all.add(feature);
                        edges.put(feature, new ArrayList<>());
                        incoming.put(feature, 0);
                    }
                }
            }

            for (List<List<PlacedFeature>> biome : perBiome) {
                if (step >= biome.size()) continue;
                List<PlacedFeature> entries = biome.get(step);
                for (int i = 1; i < entries.size(); i++) {
                    PlacedFeature before = entries.get(i - 1);
                    PlacedFeature after = entries.get(i);
                    if (before == after || containsIdentity(edges.get(before), after)) continue;
                    if (canReach(after, before, edges)) {
                        droppedEdges++;
                        continue; // Reject only the order constraint, not the feature.
                    }
                    edges.get(before).add(after);
                    incoming.put(after, incoming.get(after) + 1);
                }
            }

            PriorityQueue<PlacedFeature> ready =
                new PriorityQueue<>(Comparator.comparingInt(ranks::get));
            for (PlacedFeature feature : all) if (incoming.get(feature) == 0) ready.add(feature);
            List<PlacedFeature> sorted = new ArrayList<>(all.size());
            while (!ready.isEmpty()) {
                PlacedFeature feature = ready.remove();
                sorted.add(feature);
                for (PlacedFeature dependent : edges.get(feature)) {
                    int remaining = incoming.get(dependent) - 1;
                    incoming.put(dependent, remaining);
                    if (remaining == 0) ready.add(dependent);
                }
            }
            if (sorted.size() != all.size()) {
                throw new IllegalStateException("OmniIsle feature-order recovery could not sort step " + step);
            }

            IdentityHashMap<PlacedFeature, Integer> index = new IdentityHashMap<>();
            for (int i = 0; i < sorted.size(); i++) index.put(sorted.get(i), i);
            result.add(new FeatureSorter.StepFeatureData(List.copyOf(sorted),
                feature -> index.getOrDefault(feature, -1)));
        }
        LOG.warn("Resolved incompatible modded biome feature order for OmniIsle: {} "
            + "conflicting order edges skipped across {} decoration steps; "
            + "all {} biome feature sets retained.", droppedEdges, stepCount, biomes.size());
        return List.copyOf(result);
    }

    private static boolean containsIdentity(List<PlacedFeature> values, PlacedFeature target) {
        for (PlacedFeature value : values) if (value == target) return true;
        return false;
    }

    private static boolean canReach(PlacedFeature start, PlacedFeature target,
            Map<PlacedFeature, List<PlacedFeature>> edges) {
        ArrayDeque<PlacedFeature> pending = new ArrayDeque<>();
        IdentityHashMap<PlacedFeature, Boolean> visited = new IdentityHashMap<>();
        pending.add(start);
        while (!pending.isEmpty()) {
            PlacedFeature current = pending.removeFirst();
            if (current == target) return true;
            if (visited.put(current, true) != null) continue;
            pending.addAll(edges.get(current));
        }
        return false;
    }
}
""", encoding="utf-8")

mixin = JAVA / "mixin/client/ChunkGeneratorFeatureCycleMixin.java"
mixin.write_text("""package com.hack337.omniisle.mixin.client;

import com.google.common.base.Suppliers;
import com.hack337.omniisle.worldgen.OmniBiomeSource;
import com.hack337.omniisle.worldgen.OmniFeatureCycleRecovery;
import java.util.List;
import java.util.function.Function;
import java.util.function.Supplier;
import net.minecraft.core.Holder;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.BiomeGenerationSettings;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.biome.FeatureSorter;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.placement.PlacedFeature;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Mutable;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Vanilla sorting stays unchanged unless an OmniIsle world has a cycle.
 * Do not modify the registered BiomeGenerationSettings of either mod.
 */
@Mixin(ChunkGenerator.class)
public abstract class ChunkGeneratorFeatureCycleMixin {
    @Shadow @Final protected BiomeSource biomeSource;
    @Shadow @Final private Function<Holder<Biome>, BiomeGenerationSettings> generationSettingsGetter;
    @Shadow @Final @Mutable private Supplier<List<FeatureSorter.StepFeatureData>> featuresPerStep;

    @Inject(method = "<init>(Lnet/minecraft/world/level/biome/BiomeSource;Ljava/util/function/Function;)V",
            at = @At("RETURN"))
    private void omniisle$repairFeatureCycle(
            BiomeSource source, Function<Holder<Biome>, BiomeGenerationSettings> getter, CallbackInfo ci) {
        if (!(source instanceof OmniBiomeSource)) return;
        Supplier<List<FeatureSorter.StepFeatureData>> ordinary = this.featuresPerStep;
        this.featuresPerStep = Suppliers.memoize(() -> {
            try {
                return ordinary.get();
            } catch (IllegalStateException exception) {
                if (exception.getMessage() == null
                        || !exception.getMessage().startsWith("Feature order cycle found")) {
                    throw exception;
                }
                return OmniFeatureCycleRecovery.recover(source.possibleBiomes(),
                    biome -> this.generationSettingsGetter.apply(biome).features());
            }
        });
    }
}
""", encoding="utf-8")

import json
cfg_file = RES / "omniisle.client.mixins.json"
cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
cfg["mixins"] = list(dict.fromkeys(
    [*cfg.get("mixins", []), "ChunkGeneratorFeatureCycleMixin"]))
cfg_file.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
print("OmniIsle-only feature-order cycle protection installed.")
