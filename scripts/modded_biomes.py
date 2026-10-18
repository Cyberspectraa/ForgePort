#!/usr/bin/env python3
"""Extra, opt-in Forge 1.20.1 biome palette and structure gating patches.

Executed by scripts/convert.py, after the pinned upstream sources have been copied.
JAVA, RES, and replace are provided by that script.
"""
from pathlib import Path


def patch_once(relative_path, old, new):
    p = JAVA / relative_path
    contents = p.read_text(encoding="utf-8")
    n = contents.count(old)
    if n != 1:
        raise RuntimeError(f"{relative_path}: expected exactly one patch anchor, found {n}: {old[:95]}")
    p.write_text(contents.replace(old, new, 1), encoding="utf-8")


# Persistent, per-world editor choices. Optional custom biomes are always opt-in.
patch_once("client/IslandDraft.java",
    "    private EnumSet<StructureOption> enabledStructures;",
    """    private EnumSet<StructureOption> enabledStructures;
    private final java.util.EnumMap<BiomePreview.Category, java.util.LinkedHashSet<String>> customBiomes =
        new java.util.EnumMap<>(BiomePreview.Category.class);
""")
patch_once("client/IslandDraft.java",
    """    public IslandDraft copy() {
        return new IslandDraft(Arrays.copyOf(land, land.length), islandSize, shapeSeed, biomeSeed, preset,
            EnumSet.copyOf(enabledBiomes), EnumSet.copyOf(enabledStructures));
    }""",
    """    public IslandDraft copy() {
        IslandDraft copy = new IslandDraft(Arrays.copyOf(land, land.length), islandSize, shapeSeed, biomeSeed, preset,
            EnumSet.copyOf(enabledBiomes), EnumSet.copyOf(enabledStructures));
        for (var entry : customBiomes.entrySet())
            copy.customBiomes.put(entry.getKey(), new java.util.LinkedHashSet<>(entry.getValue()));
        return copy;
    }""")
patch_once("client/IslandDraft.java",
    """            if (remainingInCategory == 1) return false;""",
    """            if (remainingInCategory == 1 && customBiomeIds(type.category).isEmpty()) return false;""")
patch_once("client/IslandDraft.java",
    "    public boolean isStructureEnabled(StructureOption option) {",
    """    /** A mod biome may be assigned to precisely one terrain category. */
    public boolean toggleCustomBiome(String id, BiomePreview.Category category) {
        if (id == null || !id.contains(":") || id.startsWith("minecraft:")) return false;
        if (customBiomes.getOrDefault(category, new java.util.LinkedHashSet<>()).contains(id)) {
            if (enabledBiomes(category).isEmpty() && customBiomeIds(category).size() == 1) return false;
            customBiomes.get(category).remove(id);
            return true;
        }
        for (var entries : customBiomes.values()) entries.remove(id);
        customBiomes.computeIfAbsent(category, ignored -> new java.util.LinkedHashSet<>()).add(id);
        return true;
    }

    public java.util.List<String> customBiomeIds(BiomePreview.Category category) {
        return java.util.List.copyOf(customBiomes.getOrDefault(category, new java.util.LinkedHashSet<>()));
    }

    public boolean isCustomBiomeEnabled(String id, BiomePreview.Category category) {
        return customBiomeIds(category).contains(id);
    }

    public java.util.List<String> enabledBiomeIds(BiomePreview.Category category) {
        java.util.ArrayList<String> ids = new java.util.ArrayList<>();
        enabledBiomes(category).forEach(type -> ids.add(type.biomeId()));
        ids.addAll(customBiomeIds(category));
        return java.util.List.copyOf(ids);
    }

    public boolean isAnyRequiredBiomeEnabled(java.util.Set<BiomePreview.Type> required) {
        return required.stream().anyMatch(this::isBiomeEnabled);
    }

    /** The editor preview uses the same low-frequency patch choice as server generation. */
    public int previewColor(BiomePreview.Type vanilla, double worldX, double worldZ) {
        java.util.List<String> mods = customBiomeIds(vanilla.category);
        int index = com.hack337.omniisle.worldgen.ModdedBiomePatches.index(
            (int)worldX, (int)worldZ, biomeSeed, mods.size(), vanilla.category.ordinal());
        if (index < 0) return vanilla.color;
        int rgb = mods.get(index).hashCode();
        // Distinct but stable dark green/teal colour for modded biome patches.
        return 0xFF000000 | (0x40 + ((rgb >>> 16) & 0x5F)) << 16
            | (0x60 + ((rgb >>> 8) & 0x6F)) << 8 | (0x40 + (rgb & 0x5F));
    }

    public boolean isStructureEnabled(StructureOption option) {""")

# Preserve per-world selections in the exported datapack rather than editing
# global Minecraft biome tags / other mods' registry data.
patch_once("client/WorldPackBuilder.java",
    """        state.enabledBiomes(category).forEach(type -> enabled.add(type.biomeId()));""",
    """        state.enabledBiomeIds(category).forEach(enabled::add);""")
patch_once("client/WorldPackBuilder.java",
    """            boolean enabled = state.isStructureEnabled(IslandDraft.StructureOption.values()[structureIndex]);""",
    """            // A structure tied to a specific biome must not silently migrate to
            // a different biome when its required biome has been turned off.
            boolean enabled = state.isStructureEnabled(IslandDraft.StructureOption.values()[structureIndex])
                && state.isAnyRequiredBiomeEnabled(definition.biomes)
                && (!definition.deepDark || state.isBiomeEnabled(BiomePreview.Type.DEEP_DARK));""")

# Generated terrain, preview and structure compatibility share the same stable
# biome-patch choice. Each enabled mod biome gets an organic-looking patch of
# land/ocean/etc without overriding vanilla palette definitions.
patches = JAVA / "worldgen/ModdedBiomePatches.java"
patches.write_text("""package com.hack337.omniisle.worldgen;

/** Deterministic modded-biome patch selector, shared by the editor and biome source. */
public final class ModdedBiomePatches {
    private ModdedBiomePatches() {}

    /** Returns -1 for vanilla, otherwise an index in the selected mod biome list. */
    public static int index(int x, int z, long seed, int count, int category) {
        if (count == 0) return -1;
        double nx = x / 540.0;
        double nz = z / 540.0;
        double value = noise(nx, nz, seed + category * 1997L);
        if (value < 0.22) return -1;
        double choice = noise(nx * 0.62 + 103.0, nz * 0.62 - 47.0, seed + 5003L + category * 101L);
        return Math.min(count - 1, Math.max(0, (int)Math.floor((choice + 1.0) * 0.5 * count)));
    }

    private static double noise(double x, double z, long seed) {
        int ix = (int)Math.floor(x), iz = (int)Math.floor(z);
        double fx = x - ix, fz = z - iz;
        fx = fx * fx * (3.0 - 2.0 * fx);
        fz = fz * fz * (3.0 - 2.0 * fz);
        double a = mix(unit(ix, iz, seed), unit(ix + 1, iz, seed), fx);
        double b = mix(unit(ix, iz + 1, seed), unit(ix + 1, iz + 1, seed), fx);
        return mix(a, b, fz);
    }

    private static double unit(int x, int z, long seed) {
        long n = seed ^ (x * 0x9E3779B97F4A7C15L) ^ (z * 0xC2B2AE3D27D4EB4FL);
        n = (n ^ (n >>> 30)) * 0xBF58476D1CE4E5B9L;
        n = (n ^ (n >>> 27)) * 0x94D049BB133111EBL;
        return ((n ^ (n >>> 31)) >>> 11) * 0x1.0p-52 * 2.0 - 1.0;
    }

    private static double mix(double a, double b, double t) { return a + (b - a) * t; }
}
""", encoding="utf-8")

# Add modded biomes to the actual biome-source sampling, not just to the codec.
patch_once("worldgen/OmniBiomeSource.java",
    """    @Override
    public Holder<Biome> getNoiseBiome(int biomeX, int biomeY, int biomeZ, net.minecraft.world.level.biome.Climate.Sampler sampler) {""",
    """    @Override
    public Holder<Biome> getNoiseBiome(int biomeX, int biomeY, int biomeZ, net.minecraft.world.level.biome.Climate.Sampler sampler) {
        Holder<Biome> base = originalNoiseBiome(biomeX, biomeY, biomeZ, sampler);
        List<Holder<Biome>> group;
        int category;
        if (enabledLandBiomes.contains(base)) { group = enabledLandBiomes; category = 0; }
        else if (enabledShoreBiomes.contains(base)) { group = enabledShoreBiomes; category = 1; }
        else if (enabledOceanBiomes.contains(base)) { group = enabledOceanBiomes; category = 2; }
        else if (enabledRiverBiomes.contains(base)) { group = enabledRiverBiomes; category = 3; }
        else { group = enabledCaveBiomes; category = 4; }
        List<Holder<Biome>> extra = group.stream()
            .filter(holder -> holder.unwrapKey().map(key -> !"minecraft".equals(key.location().getNamespace())).orElse(false))
            .toList();
        int index = ModdedBiomePatches.index(biomeX << 2, biomeZ << 2, biomeSeed, extra.size(), category);
        return index < 0 ? base : extra.get(index);
    }

    private Holder<Biome> originalNoiseBiome(int biomeX, int biomeY, int biomeZ, net.minecraft.world.level.biome.Climate.Sampler sampler) {""")

# Dedicated selection page avoids squeezing a long mod registry into the small
# original editor. A mod biome can be assigned to land, shore, ocean, river, cave.
modscreen = JAVA / "client/ModdedBiomeScreen.java"
modscreen.write_text("""package com.hack337.omniisle.client;

import java.util.Comparator;
import java.util.List;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.CycleButton;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.worldselection.CreateWorldScreen;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;

/** A discoverable, registry-driven list of installed mods' biomes. */
public final class ModdedBiomeScreen extends Screen {
    private final Screen owner;
    private final IslandDraft draft;
    private final CreateWorldScreen createWorld;
    private List<ResourceLocation> available = List.of();
    private BiomePreview.Category category = BiomePreview.Category.LAND;
    private int scroll;
    private int left, top, panelWidth, panelHeight;

    ModdedBiomeScreen(Screen owner, IslandDraft draft, CreateWorldScreen createWorld) {
        super(Component.literal("OmniIsle - Modded Biomes"));
        this.owner = owner;
        this.draft = draft;
        this.createWorld = createWorld;
    }

    @Override
    protected void init() {
        var registry = createWorld.getUiState().getSettings().worldgenRegistries()
            .registryOrThrow(Registries.BIOME);
        available = registry.keySet().stream()
            .filter(id -> !"minecraft".equals(id.getNamespace()))
            .sorted(Comparator.comparing(ResourceLocation::toString)).toList();
        panelWidth = Math.min(420, width - 24);
        panelHeight = Math.max(65, height - 117);
        left = (width - panelWidth) / 2;
        top = 67;
        addRenderableWidget(CycleButton.<BiomePreview.Category>builder(c -> Component.literal(c.name()))
            .withValues(List.of(BiomePreview.Category.values()))
            .withInitialValue(category)
            .create(width / 2 - 96, 27, 192, 20, Component.literal("Biome category"), (b, c) -> {
                category = c;
                scroll = 0;
            }));
        addRenderableWidget(Button.builder(Component.literal("Back to OmniIsle editor"), b -> onClose())
            .bounds(width / 2 - 105, height - 27, 210, 20).build());
    }

    @Override
    public void render(GuiGraphics g, int mx, int my, float delta) {
        renderBackground(g);
        super.render(g, mx, my, delta);
    }

    @Override
    public void renderBackground(GuiGraphics g) {
        super.renderBackground(g);
        g.drawCenteredString(font, title, width / 2, 10, 0xFFF4E8C1);
        g.drawCenteredString(font, "Enable mod biomes in the chosen terrain category", width / 2, 52, 0xFFE0E0E0);
        g.fill(left - 2, top - 2, left + panelWidth + 2, top + panelHeight + 2, 0xFF26312D);
        g.fill(left, top, left + panelWidth, top + panelHeight, 0xEE101817);
        int visible = Math.max(1, (panelHeight - 4) / 17);
        int max = Math.max(0, available.size() - visible);
        scroll = Math.max(0, Math.min(scroll, max));
        if (available.isEmpty()) {
            g.drawCenteredString(font, "No additional mod biomes found", width / 2, top + 20, 0xFFAFAFAF);
            return;
        }
        for (int row = 0; row < visible; row++) {
            int idx = scroll + row;
            if (idx >= available.size()) break;
            int y = top + 2 + row * 17;
            String id = available.get(idx).toString();
            boolean enabled = draft.isCustomBiomeEnabled(id, category);
            if (enabled) g.fill(left + 2, y, left + panelWidth - 2, y + 16, 0xFF355841);
            g.renderOutline(left + 7, y + 3, 10, 10, 0xFFAAB8AB);
            if (enabled) g.fill(left + 9, y + 5, left + 15, y + 11, 0xFF55FF55);
            String visibleName = font.plainSubstrByWidth(id, panelWidth - 36);
            g.drawString(font, visibleName, left + 23, y + 3,
                enabled ? 0xFFFFFFFF : 0xFFB9C5BC);
        }
        if (max > 0) {
            int track = panelHeight - 8;
            int thumb = Math.max(10, track * visible / available.size());
            int y = top + 4 + scroll * (track - thumb) / max;
            g.fill(left + panelWidth - 5, y, left + panelWidth - 2, y + thumb, 0xFFC2D5C6);
        }
    }

    @Override
    public boolean mouseClicked(double x, double y, int button) {
        if (button == 0 && x >= left && x < left + panelWidth && y >= top && y < top + panelHeight) {
            int index = scroll + ((int)y - top - 2) / 17;
            if (index >= 0 && index < available.size()) {
                if (!draft.toggleCustomBiome(available.get(index).toString(), category))
                    return true; // Cannot remove the last biome of any terrain category.
                if (owner instanceof OmniIsleEditorScreen editor) editor.refreshPreview();
            }
            return true;
        }
        return super.mouseClicked(x, y, button);
    }

    @Override
    public boolean mouseScrolled(double x, double y, double delta) {
        if (x >= left && x < left + panelWidth && y >= top && y < top + panelHeight) {
            int rows = Math.max(1, (panelHeight - 4) / 17);
            scroll = Math.max(0, Math.min(Math.max(0, available.size() - rows), scroll - (int)Math.signum(delta)));
            return true;
        }
        return super.mouseScrolled(x, y, delta);
    }

    @Override
    public void onClose() {
        if (owner instanceof OmniIsleEditorScreen editor) editor.refreshPreview();
        minecraft.setScreen(owner);
    }
}
""", encoding="utf-8")

# The main editor's biome/structure list gains a third tab opening the full
# mod selection page. Original tabs and checklists remain intact.
patch_once("client/OmniIsleEditorScreen.java",
    """        int middle = biomeListX + biomeListWidth / 2;
        context.fill(showStructures ? middle : biomeListX + 1, biomeListY + 1,
            showStructures ? biomeListX + biomeListWidth - 1 : middle, biomeListY + 19, 0xFF435A47);
        context.drawCenteredString(font, Component.translatable("omniisle.editor.biomes"),
            biomeListX + biomeListWidth / 4, biomeListY + 6, showStructures ? 0xFFAAAAAA : 0xFFFFFFFF);
        context.drawCenteredString(font, Component.translatable("omniisle.editor.structures"),
            biomeListX + biomeListWidth * 3 / 4, biomeListY + 6, showStructures ? 0xFFFFFFFF : 0xFFAAAAAA);""",
    """        int third = biomeListWidth / 3;
        context.fill(biomeListX + (showStructures ? third : 1), biomeListY + 1,
            biomeListX + (showStructures ? third * 2 : third), biomeListY + 19, 0xFF435A47);
        context.drawCenteredString(font, Component.translatable("omniisle.editor.biomes"),
            biomeListX + third / 2, biomeListY + 6, showStructures ? 0xFFAAAAAA : 0xFFFFFFFF);
        context.drawCenteredString(font, Component.translatable("omniisle.editor.structures"),
            biomeListX + third + third / 2, biomeListY + 6, showStructures ? 0xFFFFFFFF : 0xFFAAAAAA);
        context.drawCenteredString(font, "Mods", biomeListX + third * 2 + third / 2,
            biomeListY + 6, 0xFFDDDDDD);""")
patch_once("client/OmniIsleEditorScreen.java",
    """                showStructures = mouseX >= biomeListX + biomeListWidth / 2;
                biomeScroll = 0;""",
    """                if (mouseX >= biomeListX + biomeListWidth * 2 / 3) {
                    minecraft.setScreen(new ModdedBiomeScreen(this, state, parent));
                    return true;
                }
                showStructures = mouseX >= biomeListX + biomeListWidth / 3;
                biomeScroll = 0;""")
patch_once("client/OmniIsleEditorScreen.java",
    """                int color = state.selectBiome(preferred, state.worldX(x), state.worldZ(z)).color;""",
    """                int color = state.previewColor(state.selectBiome(preferred, state.worldX(x), state.worldZ(z)),
                    state.worldX(x), state.worldZ(z));""")

# Compact-layout companion page also exposes the same Mods tab.
patch_once("client/BiomeSelectionScreen.java",
    """        int middle = listX + listWidth / 2;
        context.fill(showStructures ? middle : listX + 1, listY + 1,
            showStructures ? listX + listWidth - 1 : middle, listY + 19, 0xFF435A47);
        context.drawCenteredString(font, Component.translatable("omniisle.editor.biomes"),
            listX + listWidth / 4, listY + 6, showStructures ? 0xFFAAAAAA : 0xFFFFFFFF);
        context.drawCenteredString(font, Component.translatable("omniisle.editor.structures"),
            listX + listWidth * 3 / 4, listY + 6, showStructures ? 0xFFFFFFFF : 0xFFAAAAAA);""",
    """        int third = listWidth / 3;
        context.fill(listX + (showStructures ? third : 1), listY + 1,
            listX + (showStructures ? third * 2 : third), listY + 19, 0xFF435A47);
        context.drawCenteredString(font, Component.translatable("omniisle.editor.biomes"),
            listX + third / 2, listY + 6, showStructures ? 0xFFAAAAAA : 0xFFFFFFFF);
        context.drawCenteredString(font, Component.translatable("omniisle.editor.structures"),
            listX + third + third / 2, listY + 6, showStructures ? 0xFFFFFFFF : 0xFFAAAAAA);
        context.drawCenteredString(font, "Mods", listX + third * 2 + third / 2, listY + 6, 0xFFDDDDDD);""")
patch_once("client/BiomeSelectionScreen.java",
    """                showStructures = mouseX >= listX + listWidth / 2;
                scroll = 0;""",
    """                if (mouseX >= listX + listWidth * 2 / 3) {
                    minecraft.setScreen(new ModdedBiomeScreen(this, state, owner.omniisle$parent()));
                    return true;
                }
                showStructures = mouseX >= listX + listWidth / 3;
                scroll = 0;""")
patch_once("client/OmniIsleEditorScreen.java",
    """    void refreshPreview() { invalidatePreview(); }""",
    """    void refreshPreview() { invalidatePreview(); }
    CreateWorldScreen omniisle$parent() { return parent; }""")

# Registry biome predicates ensure no structure will generate on an OmniIsle
# world if EVERY biome that structure needs was deselected. Other world presets
# and modded ocean structures remain unaffected.
patch_once("mixin/client/StructureLandGuardMixin.java",
    """        ResourceLocation id = registry.getKey(structure);
        if (id == null) return;""",
    """        ResourceLocation id = registry.getKey(structure);
        if (id == null) return;

        java.util.Set<Holder<Biome>> possible = biomeSource.possibleBiomes();
        if (structure.biomes().stream().noneMatch(possible::contains)) {
            cir.setReturnValue(StructureStart.INVALID_START);
            return;
        }""")

print("Modded biome editor, generation and conditional structures installed")
