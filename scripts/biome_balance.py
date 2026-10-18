#!/usr/bin/env python3
"""Category-specific biome abundance and generic structure placement compatibility.
Runs after scripts/modded_biomes.py. Existing original generation is preserved
unless a player explicitly changes a biome percentage.
"""
from pathlib import Path

# Per-world, normalized biome shares; original climate defaults are unchanged.
patch_once("client/IslandDraft.java",
    "    private final java.util.EnumMap<BiomePreview.Category, java.util.LinkedHashSet<String>> customBiomes =",
    """    private final java.util.LinkedHashMap<String, Integer> biomeWeights = new java.util.LinkedHashMap<>();
    private final java.util.EnumMap<BiomePreview.Category, java.util.LinkedHashSet<String>> customBiomes =""")
patch_once("client/IslandDraft.java",
    """        for (var entry : customBiomes.entrySet())
            copy.customBiomes.put(entry.getKey(), new java.util.LinkedHashSet<>(entry.getValue()));
        return copy;""",
    """        for (var entry : customBiomes.entrySet())
            copy.customBiomes.put(entry.getKey(), new java.util.LinkedHashSet<>(entry.getValue()));
        copy.biomeWeights.putAll(biomeWeights);
        return copy;""")
patch_once("client/IslandDraft.java",
    "    public boolean isStructureEnabled(StructureOption option) {",
    """    /** Explicit weights are optional; defaults retain the original climate layout. */
    public java.util.Map<String, Integer> biomeWeights() {
        java.util.LinkedHashMap<String, Integer> result = new java.util.LinkedHashMap<>();
        for (var category : BiomePreview.Category.values())
            for (String id : enabledBiomeIds(category))
                if (biomeWeights.containsKey(id)) result.put(id, biomeWeights.get(id));
        return java.util.Map.copyOf(result);
    }

    public boolean hasBiomeWeights(BiomePreview.Category category) {
        return enabledBiomeIds(category).stream().anyMatch(biomeWeights::containsKey);
    }

    public int[] categoryWeights(BiomePreview.Category category) {
        return enabledBiomeIds(category).stream().mapToInt(id -> biomeWeights.getOrDefault(id, 1000)).toArray();
    }

    /** Return the normalized target percentage, not the relative weight. */
    public int targetPercent(String id, BiomePreview.Category category) {
        java.util.List<String> ids = enabledBiomeIds(category);
        if (!ids.contains(id)) return 0;
        long sum = ids.stream().mapToLong(s -> biomeWeights.getOrDefault(s, 1000)).sum();
        return sum == 0 ? 0 : (int)Math.round(100.0 * biomeWeights.getOrDefault(id, 1000) / sum);
    }

    /** Change one biome's category-wide target share; preserve all other ratios. */
    public boolean setTargetPercent(String id, BiomePreview.Category category, int percent) {
        java.util.List<String> ids = enabledBiomeIds(category);
        if (!ids.contains(id)) return false;
        if (ids.size() == 1) return true;
        int target = Math.max(1, Math.min(99, percent));
        long others = ids.stream().filter(s -> !s.equals(id))
            .mapToLong(s -> biomeWeights.getOrDefault(s, 1000)).sum();
        long newWeight = Math.round(others * (target / (100.0 - target)));
        // Renormalize before overflow, retaining other-biome proportions.
        if (newWeight > 10_000_000L || others > 10_000_000L) {
            double factor = 1_000_000.0 / Math.max(newWeight, others);
            for (String other : ids) {
                if (!other.equals(id))
                    biomeWeights.put(other, Math.max(1, (int)Math.round(biomeWeights.getOrDefault(other, 1000) * factor)));
            }
            others = ids.stream().filter(s -> !s.equals(id))
                .mapToLong(s -> biomeWeights.getOrDefault(s, 1000)).sum();
            newWeight = Math.round(others * (target / (100.0 - target)));
        }
        biomeWeights.put(id, (int)Math.max(1, Math.min(10_000_000, newWeight)));
        return true;
    }

    public boolean isStructureEnabled(StructureOption option) {""")
# Preview remains coherent with server distribution, including mod biomes.
patch_once("client/IslandDraft.java",
    """        java.util.LinkedHashSet<String> mods = customBiomes.get(vanilla.category);
        if (mods == null || mods.isEmpty()) return vanilla.color;""",
    """        java.util.LinkedHashSet<String> mods = customBiomes.get(vanilla.category);
        if (hasBiomeWeights(vanilla.category)) {
            java.util.List<String> enabled = enabledBiomeIds(vanilla.category);
            int index = com.hack337.omniisle.worldgen.BiomeShareSampler.index(
                (int)worldX, (int)worldZ, biomeSeed, vanilla.category.ordinal(),
                categoryWeights(vanilla.category));
            if (index < 0) return vanilla.color;
            String id = enabled.get(index);
            for (BiomePreview.Type biome : BiomePreview.Type.values())
                if (biome.biomeId().equals(id)) return biome.color;
            return colorForModBiome(id);
        }
        if (mods == null || mods.isEmpty()) return vanilla.color;""")
patch_once("client/IslandDraft.java",
    """        // Distinct but stable dark green/teal colour for modded biome patches.
        return 0xFF000000 | (0x40 + ((rgb >>> 16) & 0x5F)) << 16
            | (0x60 + ((rgb >>> 8) & 0x6F)) << 8 | (0x40 + (rgb & 0x5F));
    }""",
    """        return colorForModBiomeHash(rgb);
    }

    private static int colorForModBiome(String id) { return colorForModBiomeHash(id.hashCode()); }
    private static int colorForModBiomeHash(int rgb) {
        return 0xFF000000 | (0x40 + ((rgb >>> 16) & 0x5F)) << 16
            | (0x60 + ((rgb >>> 8) & 0x6F)) << 8 | (0x40 + (rgb & 0x5F));
    }""")
patch_once("client/IslandDraft.java",
    """        List<BiomePreview.Type> compatible = compatibleChoices(preferred);
        if (compatible.size() == 1) return compatible.get(0);""",
    """        List<BiomePreview.Type> compatible = compatibleChoices(preferred);
        if (compatible.isEmpty()) return preferred;
        if (compatible.size() == 1) return compatible.get(0);""")

# If all vanilla biomes in a category are unchecked and modded biomes remain,
# the map preview must not paint disabled vanilla regions in the patch gaps.
patch_once("client/IslandDraft.java",
    """        if (index < 0) return vanilla.color;
        int rgb = 0, cursor = 0;""",
    """        if (index < 0) {
            if (!enabledBiomes(vanilla.category).isEmpty()) return vanilla.color;
            index = 0;
        }
        int rgb = 0, cursor = 0;""")

# The newly selected shares are serialized into the generated per-world preset.
patch_once("client/WorldPackBuilder.java",
    """                biomeSource.addProperty("biome_seed", state.biomeSeed());""",
    """                biomeSource.addProperty("biome_seed", state.biomeSeed());
                JsonObject weights = new JsonObject();
                state.biomeWeights().forEach(weights::addProperty);
                biomeSource.add("biome_weights", weights);""")

# Weighted mode only when explicitly requested: default noise/climate layout
# is intentionally untouched to preserve already verified original behaviour.
patch_once("worldgen/OmniBiomeSource.java",
    """        Codec.LONG.optionalFieldOf("biome_seed", 0L).forGetter(s -> s.biomeSeed)""",
    """        Codec.LONG.optionalFieldOf("biome_seed", 0L).forGetter(s -> s.biomeSeed),
        Codec.unboundedMap(Codec.STRING, Codec.intRange(1, 10_000_000))
            .optionalFieldOf("biome_weights", java.util.Map.of()).forGetter(s -> s.biomeWeights)""")
patch_once("worldgen/OmniBiomeSource.java",
    """    private final List<Holder<Biome>> modLandBiomes, modShoreBiomes, modOceanBiomes,
        modRiverBiomes, modCaveBiomes;""",
    """    private final List<Holder<Biome>> modLandBiomes, modShoreBiomes, modOceanBiomes,
        modRiverBiomes, modCaveBiomes;
    private final java.util.Map<String, Integer> biomeWeights;
    private final int[][] categoryWeights = new int[5][];
    private final boolean[] categoryWeighted = new boolean[5];""")
patch_once("worldgen/OmniBiomeSource.java",
    """                             int climateScale,
                             long biomeSeed) {""",
    """                             int climateScale,
                             long biomeSeed,
                             java.util.Map<String, Integer> biomeWeights) {""")
patch_once("worldgen/OmniBiomeSource.java",
    """        this.modCaveBiomes = moddedOnly(this.enabledCaveBiomes);""",
    """        this.modCaveBiomes = moddedOnly(this.enabledCaveBiomes);
        this.biomeWeights = java.util.Map.copyOf(biomeWeights);
        java.util.List<List<Holder<Biome>>> categories = java.util.List.of(
            this.enabledLandBiomes, this.enabledShoreBiomes, this.enabledOceanBiomes,
            this.enabledRiverBiomes, this.enabledCaveBiomes);
        for (int category = 0; category < categories.size(); category++) {
            java.util.List<Holder<Biome>> ids = categories.get(category);
            int[] weights = new int[ids.size()];
            for (int i = 0; i < ids.size(); i++) {
                String id = ids.get(i).unwrapKey()
                    .map(key -> key.location().toString()).orElse("");
                weights[i] = biomeWeights.getOrDefault(id, 1000);
                categoryWeighted[category] |= biomeWeights.containsKey(id);
            }
            categoryWeights[category] = weights;
        }""")
patch_once("worldgen/OmniBiomeSource.java",
    """        int index = ModdedBiomePatches.index(biomeX << 2, biomeZ << 2, biomeSeed, extra.size(), category);
        return index < 0 ? base : extra.get(index);""",
    """        if (categoryWeighted[category]) {
            int index = BiomeShareSampler.index(biomeX << 2, biomeZ << 2,
                biomeSeed, category, categoryWeights[category]);
            if (index >= 0) {
                return switch (category) {
                    case 0 -> enabledLandBiomes.get(index);
                    case 1 -> enabledShoreBiomes.get(index);
                    case 2 -> enabledOceanBiomes.get(index);
                    case 3 -> enabledRiverBiomes.get(index);
                    default -> enabledCaveBiomes.get(index);
                };
            }
        }
        int index = ModdedBiomePatches.index(biomeX << 2, biomeZ << 2, biomeSeed, extra.size(), category);
        return index < 0 ? base : extra.get(index);""")

# A stable, seeded Voronoi tile selector (organic regions, rather than
# independent individual-block randomness). Grid over land approximates target
# percentages, but irregular island shape means percentages aren't mathematically exact.
weighted = JAVA/"worldgen/BiomeShareSampler.java"
weighted.write_text("""package com.hack337.omniisle.worldgen;

/** Category-wide, deterministic biome weight sampling shared with editor preview. */
public final class BiomeShareSampler {
    private BiomeShareSampler() {}
    private static final int CELL_SIZE = 192;

    public static int index(int x, int z, long seed, int category, int[] weights) {
        if (weights.length == 0) return -1;
        if (weights.length == 1) return 0;
        int cx = Math.floorDiv(x, CELL_SIZE);
        int cz = Math.floorDiv(z, CELL_SIZE);
        double best = Double.POSITIVE_INFINITY;
        int result = 0;
        long closestSeed = 0;
        int closestX = cx, closestZ = cz;
        for (int zz = cz - 1; zz <= cz + 1; zz++) {
            for (int xx = cx - 1; xx <= cx + 1; xx++) {
                long h = hash(xx, zz, seed + category * 7919L);
                double jitterX = unit(h) * 0.84 + 0.08;
                double jitterZ = unit(hash(xx, zz, h)) * 0.84 + 0.08;
                double dx = (xx + jitterX) * CELL_SIZE - x;
                double dz = (zz + jitterZ) * CELL_SIZE - z;
                double distance = dx * dx + dz * dz;
                if (distance < best) {
                    best = distance;
                    closestSeed = h;
                    closestX = xx;
                    closestZ = zz;
                }
            }
        }
        long sum = 0;
        for (int weight : weights) sum += Math.max(1, weight);
        double pick = unit(hash(closestX, closestZ, closestSeed + 0x71d9a53L)) * sum;
        for (int i = 0; i < weights.length; i++) {
            pick -= Math.max(1, weights[i]);
            if (pick < 0) return i;
        }
        return weights.length - 1;
    }

    private static double unit(long h) { return (h >>> 11) * 0x1.0p-53; }

    private static long hash(long x, long z, long seed) {
        long h = seed ^ (x * 0x9e3779b97f4a7c15L) ^ (z * 0xc2b2ae3d27d4eb4fL);
        h = (h ^ (h >>> 30)) * 0xbf58476d1ce4e5b9L;
        h = (h ^ (h >>> 27)) * 0x94d049bb133111ebL;
        return h ^ (h >>> 31);
    }
}
""", encoding="utf-8")

# Shares are editable from the existing Mods selection page, even with only
# vanilla biomes installed. Each category is normalized to 100% in the UI.
balance = JAVA/"client/BiomeBalanceScreen.java"
balance.write_text("""package com.hack337.omniisle.client;

import java.util.List;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.CycleButton;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Controls normalized target proportions among all enabled vanilla + mod biomes. */
public final class BiomeBalanceScreen extends Screen {
    private final Screen parent;
    private final IslandDraft draft;
    private BiomePreview.Category category = BiomePreview.Category.LAND;
    private int scroll, chosen;
    private int x, y, w, h;

    BiomeBalanceScreen(Screen parent, IslandDraft draft) {
        super(Component.literal("OmniIsle - Biome Balance"));
        this.parent = parent;
        this.draft = draft;
    }

    private List<String> options() { return draft.enabledBiomeIds(category); }

    @Override
    protected void init() {
        w = Math.min(440, width - 20);
        x = (width - w) / 2;
        y = 66;
        h = Math.max(48, height - 152);
        addRenderableWidget(CycleButton.<BiomePreview.Category>builder(c -> Component.literal(c.name()))
            .withValues(List.of(BiomePreview.Category.values())).withInitialValue(category)
            .create(width / 2 - 98, 26, 196, 20, Component.literal("Terrain category"),
                (button, next) -> { category=next; scroll=0; chosen=0; }));
        addRenderableWidget(Button.builder(Component.literal("-5%"), b -> adjust(-5))
            .bounds(width / 2 - 136, height - 57, 63, 20).build());
        addRenderableWidget(Button.builder(Component.literal("-1%"), b -> adjust(-1))
            .bounds(width / 2 - 69, height - 57, 63, 20).build());
        addRenderableWidget(Button.builder(Component.literal("+1%"), b -> adjust(1))
            .bounds(width / 2 + 6, height - 57, 63, 20).build());
        addRenderableWidget(Button.builder(Component.literal("+5%"), b -> adjust(5))
            .bounds(width / 2 + 73, height - 57, 63, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Back"), b -> onClose())
            .bounds(width / 2 - 75, height - 28, 150, 20).build());
    }

    private void adjust(int delta) {
        List<String> values = options();
        if (values.isEmpty()) return;
        String id = values.get(Math.min(chosen, values.size() - 1));
        draft.setTargetPercent(id, category, draft.targetPercent(id, category) + delta);
        if (parent instanceof ModdedBiomeScreen screen) screen.refreshOwnerPreview();
    }

    @Override
    public void render(GuiGraphics g, int mx, int my, float delta) {
        renderBackground(g);
        super.render(g, mx, my, delta);
    }

    @Override
    public void renderBackground(GuiGraphics g) {
        super.renderBackground(g);
        g.drawCenteredString(font, title, width / 2, 9, 0xFFF4E8C1);
        g.drawCenteredString(font, "Approximate target share within this terrain category",
            width / 2, 51, 0xFFE0E0E0);
        g.fill(x - 2, y - 2, x + w + 2, y + h + 2, 0xFF566158);
        g.fill(x, y, x + w, y + h, 0xEE101817);
        List<String> values=options();
        int visible=Math.max(1, (h - 4) / 17);
        int max=Math.max(0, values.size()-visible);
        scroll=Math.max(0, Math.min(scroll, max));
        chosen=Math.max(0, Math.min(chosen, Math.max(0,values.size()-1)));
        for (int row=0; row<visible; row++) {
            int i=scroll+row;
            if(i>=values.size()) break;
            int ry=y+2+row*17;
            String id=values.get(i);
            if(i==chosen) g.fill(x+2, ry, x+w-2, ry+16, 0xFF355841);
            g.drawString(font, font.plainSubstrByWidth(id, w-70), x+8,ry+3,0xFFF0F0F0);
            String percent=draft.targetPercent(id,category)+"%";
            g.drawString(font, percent,x+w-36,ry+3,0xFF90E8AB);
        }
        if(max>0) {
            int th=Math.max(10,h*visible/values.size());
            int at=y+(h-th)*scroll/max;
            g.fill(x+w-4,at,x+w-2,at+th,0xFFC1D8CB);
        }
    }

    @Override
    public boolean mouseClicked(double mx, double my, int button) {
        if(button==0 && mx>=x && mx<x+w && my>=y && my<y+h) {
            int index=scroll+((int)my-y-2)/17;
            if(index>=0 && index<options().size()) chosen=index;
            return true;
        }
        return super.mouseClicked(mx,my,button);
    }

    @Override
    public boolean mouseScrolled(double mx, double my, double delta) {
        if(mx>=x && mx<x+w && my>=y && my<y+h) {
            int visible=Math.max(1,(h-4)/17);
            scroll=Math.max(0,Math.min(Math.max(0,options().size()-visible),
                scroll-(int)Math.signum(delta)));
            return true;
        }
        return super.mouseScrolled(mx,my,delta);
    }

    @Override public void onClose() { minecraft.setScreen(parent); }
}
""", encoding="utf-8")

patch_once("client/ModdedBiomeScreen.java",
    """        top = 67;""",
    """        top = 79;
        panelHeight = Math.max(55, height - 129);""")
patch_once("client/ModdedBiomeScreen.java",
    """        addRenderableWidget(Button.builder(Component.literal("Back to OmniIsle editor"), b -> onClose())""",
    """        addRenderableWidget(Button.builder(Component.literal("Biome balance / percentages"),
            b -> minecraft.setScreen(new BiomeBalanceScreen(this, draft)))
            .bounds(width / 2 - 116, 52, 232, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Back to OmniIsle editor"), b -> onClose())""")
patch_once("client/ModdedBiomeScreen.java",
    """    @Override
    public void onClose() {""",
    """    void refreshOwnerPreview() {
        if (owner instanceof OmniIsleEditorScreen editor) editor.refreshPreview();
    }

    @Override
    public void onClose() {""")

# Generic land classification derived from the selected, *enabled* biome groups.
# The 96-block tag remains available for specially large structures; untagged
# mod structures exclusively permitted in land biomes gain a 48-block buffer.
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

print("Per-category biome percentages and generic land-structure protection installed")
