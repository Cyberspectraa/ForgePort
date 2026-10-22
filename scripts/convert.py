#!/usr/bin/env python3
"""Deterministic upstream 1.21.1 NeoForge -> native 1.20.1 MinecraftForge compatibility patch.
Input: the original upstream Java files. Output: buildable Forge 47.x sources.
The original fabric/1.20.1 resources are copied by the CI workflow.
"""
from pathlib import Path
import re

ROOT=Path("src/main")
JAVA=ROOT/"java/com/hack337/omniisle"
RES=ROOT/"resources"
# Remove abandoned prototype entry point to prevent duplicate mods.
(JAVA/"OmniIsleForge.java").unlink(missing_ok=True)

def rewrite(rel, f):
    p=JAVA/rel
    old=p.read_text(encoding="utf-8")
    new=f(old)
    p.write_text(new,encoding="utf-8")
    return new

def replace(rel, changes):
    def f(s):
        for a,b in changes:
            if a not in s: print(f"NOTICE: {rel}: '{a[:80]}' not found")
            s=s.replace(a,b)
        return s
    return rewrite(rel,f)

# Forge class loaded on client and dedicated server.
(JAVA/"OmniIsleMod.java").write_text("""package com.hack337.omniisle;
import com.hack337.omniisle.worldgen.IslandDensityFunction;
import com.hack337.omniisle.worldgen.OmniBiomeSource;
import com.hack337.omniisle.worldgen.SingleStructurePlacement;
import com.hack337.omniisle.command.OmniCommands;
import com.mojang.serialization.Codec;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.structure.placement.StructurePlacementType;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;

@Mod("omniisle")
public final class OmniIsleMod {
    private static final DeferredRegister<Codec<? extends DensityFunction>> DENSITY_FUNCTIONS =
        DeferredRegister.create(Registries.DENSITY_FUNCTION_TYPE, "omniisle");
    private static final DeferredRegister<Codec<? extends BiomeSource>> BIOME_SOURCES =
        DeferredRegister.create(Registries.BIOME_SOURCE, "omniisle");
    private static final DeferredRegister<StructurePlacementType<?>> PLACEMENT_TYPES =
        DeferredRegister.create(Registries.STRUCTURE_PLACEMENT, "omniisle");

    static {
        DENSITY_FUNCTIONS.register("island_continents", () -> IslandDensityFunction.CODEC.codec());
        BIOME_SOURCES.register("island_biomes", () -> OmniBiomeSource.CODEC);
        PLACEMENT_TYPES.register("fixed", () -> SingleStructurePlacement.TYPE);
    }
    public OmniIsleMod() {
        var bus=FMLJavaModLoadingContext.get().getModEventBus();
        DENSITY_FUNCTIONS.register(bus);
        BIOME_SOURCES.register(bus);
        PLACEMENT_TYPES.register(bus);
        MinecraftForge.EVENT_BUS.addListener(OmniCommands::registerCommands);
    }
}
""",encoding="utf-8")

# Use Forge's public screen-init and render events for the editor entry point.
# This replaces version-fragile injections into the private WorldTab class.
(JAVA/"mixin/client/WorldTypeEditorMixin.java").unlink(missing_ok=True)
client_hooks=JAVA/"client/ForgeEditorButton.java"
client_hooks.write_text("""package com.hack337.omniisle.client;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.worldselection.CreateWorldScreen;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.network.chat.Component;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ScreenEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.Map;
import java.util.WeakHashMap;

@Mod.EventBusSubscriber(modid="omniisle", value=Dist.CLIENT, bus=Mod.EventBusSubscriber.Bus.FORGE)
public final class ForgeEditorButton {
    private static final Map<CreateWorldScreen, Button> BUTTONS = new WeakHashMap<>();
    private static final Map<CreateWorldScreen, Boolean> RESELECT_PRESET = new WeakHashMap<>();
    private ForgeEditorButton() {}

    /** Called before applying a regenerated world-creation datapack. */
    public static void expectPresetRefresh(CreateWorldScreen screen) {
        RESELECT_PRESET.put(screen, true);
    }

    public static void cancelPresetRefresh(CreateWorldScreen screen) {
        RESELECT_PRESET.remove(screen);
    }

    @SubscribeEvent
    public static void addButton(ScreenEvent.Init.Post event) {
        if (!(event.getScreen() instanceof CreateWorldScreen screen)) return;
        Button button = Button.builder(Component.translatable("omniisle.editor.open"),
                b -> Minecraft.getInstance().setScreen(new OmniIsleEditorScreen(screen)))
            .bounds(Math.max(8, screen.width - 186), Math.max(35, screen.height - 63), 174, 20)
            .build();
        button.visible = false;
        button.active = false;
        event.addListener(button);
        BUTTONS.put(screen, button);
    }

    @SubscribeEvent
    public static void updateButton(ScreenEvent.Render.Post event) {
        if (!(event.getScreen() instanceof CreateWorldScreen screen)) return;
        Button button = BUTTONS.get(screen);
        if (button == null) return;
        WorldCreationUiState state = screen.getUiState();
        // In 1.20.1 the datapack reload can preserve a stale selectedDimensions
        // generator even though the new preset JSON and enabled pack were loaded.
        // Re-select the freshly loaded registry entry exactly once after save.
        if (Boolean.TRUE.equals(RESELECT_PRESET.get(screen))) {
            boolean generatedPackEnabled = state.getSettings().dataConfiguration()
                .dataPacks().getEnabled().stream()
                .anyMatch(id -> id.endsWith(WorldPackBuilder.FILE_NAME));
            if (generatedPackEnabled) {
                var reloadedPreset = java.util.stream.Stream.concat(
                        state.getNormalPresetList().stream(), state.getAltPresetList().stream())
                    .filter(entry -> entry.preset() != null && entry.preset().unwrapKey()
                        .map(key -> "omniisle".equals(key.location().getNamespace())
                            && "omniisle".equals(key.location().getPath()))
                        .orElse(false))
                    .findFirst();
                if (reloadedPreset.isPresent()) {
                    RESELECT_PRESET.remove(screen);
                    state.setWorldType(reloadedPreset.get());
                }
            }
        }
        boolean selected = state.getWorldType().preset() != null
            && state.getWorldType().preset().unwrapKey()
                .map(key -> "omniisle".equals(key.location().getNamespace())
                    && "omniisle".equals(key.location().getPath()))
                .orElse(false);
        button.active = selected;
        button.visible = selected;
    }
}
""",encoding="utf-8")

replace("OmniIsleIds.java",[
    ("ResourceLocation.fromNamespaceAndPath(MOD_ID, path)","new ResourceLocation(MOD_ID, path)")
])
replace("worldgen/IslandDensityFunction.java",[
    ("KeyDispatchDataCodec.of(CODEC)","new KeyDispatchDataCodec<>(CODEC.codec())"),
    ("Registry.register(BuiltInRegistries.DENSITY_FUNCTION_TYPE, OmniIsleIds.id(\"island_continents\"), CODEC);","// registered on Forge mod event bus"),
])
replace("worldgen/OmniBiomeSource.java",[
    ("public static final MapCodec<OmniBiomeSource> CODEC = RecordCodecBuilder.mapCodec(",
     "public static final Codec<OmniBiomeSource> CODEC = RecordCodecBuilder.create("),
    ("landBiomes.size() < 18", "landBiomes.size() < 17"),
    ("protected MapCodec<? extends BiomeSource> codec()","protected Codec<? extends BiomeSource> codec()"),
    ("key.identifier().getPath()","key.location().getPath()"),
    ("""return Stream.of(landBiomes, enabledLandBiomes, shoreBiomes, enabledShoreBiomes,
            oceanBiomes, enabledOceanBiomes, riverBiomes, enabledRiverBiomes,
            caveBiomes, enabledCaveBiomes).flatMap(List::stream).distinct();""",
     """// Only the active user-selected biomes are actually generatable.
        // Do not advertise disabled palette entries to Minecraft or modded integrations.
        return Stream.of(enabledLandBiomes, enabledShoreBiomes, enabledOceanBiomes,
            enabledRiverBiomes, enabledCaveBiomes).flatMap(List::stream).distinct();"""),
    ("Registry.register(BuiltInRegistries.BIOME_SOURCE, OmniIsleIds.id(\"island_biomes\"), CODEC);","// registered on Forge mod event bus")
])
replace("worldgen/SingleStructurePlacement.java",[
    ("public static final MapCodec<SingleStructurePlacement> CODEC = RecordCodecBuilder.mapCodec",
     "public static final Codec<SingleStructurePlacement> CODEC = RecordCodecBuilder.create"),
    ("Registry.register(BuiltInRegistries.STRUCTURE_PLACEMENT, OmniIsleIds.id(\"fixed\"), TYPE);",
     "// registered on Forge mod event bus")
])
(JAVA/"command/OmniCommands.java").write_text("""package com.hack337.omniisle.command;
import com.hack337.omniisle.worldgen.OmniBiomeSource;
import com.mojang.brigadier.Command;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.server.level.ServerLevel;
import net.minecraftforge.event.RegisterCommandsEvent;

public final class OmniCommands {
    private OmniCommands() {}
    public static void registerCommands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("omniisle")
            .requires(src -> src.hasPermission(2))
            .then(Commands.literal("verify").executes(context -> {
                ServerLevel world=context.getSource().getLevel();
                BiomeSource source=world.getChunkSource().getGenerator().getBiomeSource();
                context.getSource().sendSuccess(
                    () -> Component.literal("OmniIsle biome source: " + source.getClass().getSimpleName()
                      + "; native=" + (source instanceof OmniBiomeSource)), false);
                return Command.SINGLE_SUCCESS;
            })));
    }
}
""", encoding="utf-8")
# In Forge 1.20.1 biome spawns are supplied by data-driven forge biome modifiers.
(JAVA/"worldgen/RiverLife.java").unlink(missing_ok=True)
forge_mod=RES/"data/omniisle/forge/biome_modifier"
forge_mod.mkdir(parents=True,exist_ok=True)
(forge_mod/"river_fish.json").write_text("""{"type":"forge:add_spawns","biomes":"minecraft:river","spawners":[{"type":"minecraft:salmon","weight":24,"minCount":2,"maxCount":5},{"type":"minecraft:cod","weight":10,"minCount":2,"maxCount":4}]}
""")
(forge_mod/"frozen_river_fish.json").write_text("""{"type":"forge:add_spawns","biomes":"minecraft:frozen_river","spawners":[{"type":"minecraft:salmon","weight":18,"minCount":1,"maxCount":4}]}
""")

# Original datapack built by client editor must use 1.20.1 format.
platform=JAVA/"platform/TargetPlatform.java"
platform.parent.mkdir(parents=True,exist_ok=True)
platform.write_text("""package com.hack337.omniisle.platform;
public final class TargetPlatform {
    public static final int PACK_FORMAT = 15;
    public static final int PACK_FORMAT_MINOR = -1;
    public static final boolean HAS_TRIAL_CHAMBERS = false;
    public static final boolean HAS_PALE_GARDEN = false;
    private TargetPlatform() {}
}
""")
replace("client/OmniIsleEditorScreen.java",[
    ("public final class OmniIsleEditorScreen extends Screen {", "public final class OmniIsleEditorScreen extends Screen {\n    private int omniMouseX, omniMouseY;"),
    ("super.render(context, mouseX, mouseY, delta);", "omniMouseX = mouseX; omniMouseY = mouseY;\n        renderBackground(context);\n        super.render(context, mouseX, mouseY, delta);"),
    ("drawChoiceList(context, mouseX, mouseY)", "drawChoiceList(context, omniMouseX, omniMouseY)"),
    ("ResourceLocation.fromNamespaceAndPath(", "new ResourceLocation("),
    ("double horizontalAmount, double verticalAmount)", "double verticalAmount)"),
    ("super.mouseScrolled(mouseX, mouseY, horizontalAmount, verticalAmount)",
     "super.mouseScrolled(mouseX, mouseY, verticalAmount)"),
    ("public void renderBackground(GuiGraphics context, int mouseX, int mouseY, float delta)",
     "public void renderBackground(GuiGraphics context)"),
    ("super.renderBackground(context, mouseX, mouseY, delta)",
     "super.renderBackground(context)"),
    ("""((CreateWorldBridge)parent).omniisle$applyPack(
                manager, true, configuration -> minecraft.setScreen(parent));""",
     """ForgeEditorButton.expectPresetRefresh(parent);
            ((CreateWorldBridge)parent).omniisle$applyPack(
                manager, true, configuration -> {
                    ForgeEditorButton.cancelPresetRefresh(parent);
                    minecraft.setScreen(parent);
                });"""),
])
# GUI dimensions and drawing methods are mostly unchanged from 1.21.1, except background API.
replace("client/BiomeSelectionScreen.java",[
    ("final class BiomeSelectionScreen extends Screen {", "final class BiomeSelectionScreen extends Screen {\n    private int omniMouseX, omniMouseY;\n    @Override public void render(GuiGraphics g, int mx, int my, float p) {\n        omniMouseX=mx; omniMouseY=my;\n        renderBackground(g);\n        super.render(g,mx,my,p);\n    }"),
    ("super.render(context, mouseX, mouseY, delta);", "omniMouseX = mouseX; omniMouseY = mouseY;\n        super.render(context, mouseX, mouseY, delta);"),
    ("renderList(context, mouseX, mouseY)", "renderList(context, omniMouseX, omniMouseY)"),
    ("double horizontalAmount, double verticalAmount)", "double verticalAmount)"),
    ("super.mouseScrolled(mouseX, mouseY, horizontalAmount, verticalAmount)",
     "super.mouseScrolled(mouseX, mouseY, verticalAmount)"),
    ("public void renderBackground(GuiGraphics context, int mouseX, int mouseY, float delta)",
     "public void renderBackground(GuiGraphics context)"),
    ("super.renderBackground(context, mouseX, mouseY, delta)",
     "super.renderBackground(context)"),
])
# World creation bridge methods use this signature in 1.20.1.
# Resource mixin config comes from exact 1.20.1 upstream branch.
(RES/"pack.mcmeta").write_text('{"pack":{"pack_format":15,"description":"OmniIsle native Forge port resources"}}\n')
(RES/"META-INF").mkdir(parents=True,exist_ok=True)
(RES/"META-INF/mods.toml").write_text("""modLoader="javafml"
loaderVersion="[47,)"
license="GPL-3.0-only"
[[mods]]
modId="omniisle"
version="0.5.0-forge"
displayName="OmniIsle Forge 1.20.1 (unofficial port)"
authors="Hack337 (original), Cyberspectraa (Forge port)"
description='''OmniIsle is an island world preset with biomes, structures and custom editing.'''
[[dependencies.omniisle]]
modId="forge"
mandatory=true
versionRange="[47,)"
ordering="NONE"
side="BOTH"
[[dependencies.omniisle]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
ordering="NONE"
side="BOTH"
""")
mixins=RES/"omniisle.client.mixins.json"
if mixins.exists():
    import json
    cfg=json.loads(mixins.read_text().replace("JAVA_21", "JAVA_17"))
    cfg["refmap"]="omniisle.refmap.json"
    cfg["minVersion"]="0.8.5"

    cfg["client"]=[c for c in cfg.get("client",[]) if c != "WorldTypeEditorMixin"]
    cfg["mixins"]=[*cfg.get("mixins", []), "StructureLandGuardMixin"]
    mixins.write_text(json.dumps(cfg, indent=2)+"\n")

# Modded structures are not automatically constrained by OmniIsle's custom island
# footprint. Guard opt-in land structures at start-generation time, BEFORE pieces
# carve terrain, while leaving marine structures and other world types untouched.
guard=JAVA/"mixin/client/StructureLandGuardMixin.java"
guard.write_text("""package com.hack337.omniisle.mixin.client;

import com.hack337.omniisle.worldgen.OmniBiomeSource;
import java.util.Optional;
import java.util.function.Predicate;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Only structures in #omniisle:land_only are guarded. This is opt-in so aquatic
 * modded structures, vanilla ocean monuments, etc. still generate normally.
 * The outer ring keeps large structures away from coastlines, not just their
 * start chunk. Reads this world's actual continentalness rather than using
 * a global mask: custom editor datapacks and seeds are supported.
 */
@Mixin(Structure.class)
public abstract class StructureLandGuardMixin {
    private static final TagKey<Structure> OMNI_LAND_ONLY = TagKey.create(
        Registries.STRUCTURE, new ResourceLocation("omniisle", "land_only"));
    private static final int FOOTPRINT_MARGIN = 96;
    private static final double MIN_LAND_CONTINENTALNESS = 0.02;

    @Inject(method = "generate", at = @At("HEAD"), cancellable = true)
    private void omniisle$guardLandStructure(
            RegistryAccess registryAccess, ChunkGenerator generator,
            BiomeSource biomeSource, RandomState randomState,
            StructureTemplateManager structureTemplates, long worldSeed,
            ChunkPos chunkPos, int references, LevelHeightAccessor heightAccessor,
            Predicate<Holder<Biome>> biomePredicate,
            CallbackInfoReturnable<StructureStart> cir) {

        if (!(biomeSource instanceof OmniBiomeSource)) return;
        Registry<Structure> registry = registryAccess.registryOrThrow(Registries.STRUCTURE);
        Structure structure = (Structure) (Object) this;
        ResourceLocation id = registry.getKey(structure);
        if (id == null) return;

        Optional<Holder.Reference<Structure>> holder =
            registry.getHolder(ResourceKey.create(Registries.STRUCTURE, id));
        if (holder.isEmpty() || !holder.get().is(OMNI_LAND_ONLY)) return;

        int x = chunkPos.getMiddleBlockX();
        int z = chunkPos.getMiddleBlockZ();
        var continents = randomState.router().continents();
        int margin = FOOTPRINT_MARGIN;
        int[][] offsets = {
            {0, 0}, {margin, 0}, {-margin, 0}, {0, margin}, {0, -margin},
            {margin, margin}, {margin, -margin}, {-margin, margin}, {-margin, -margin}
        };
        for (int[] offset : offsets) {
            double value = continents.compute(
                new DensityFunction.SinglePointContext(x + offset[0], 64, z + offset[1]));
            if (value < MIN_LAND_CONTINENTALNESS) {
                cir.setReturnValue(StructureStart.INVALID_START);
                return;
            }
        }
    }
}
""", encoding="utf-8")

# Any datapack may extend this registry tag with other land-only structures.
# Optional entries allow OmniIsle to load without Ice And Fire installed.
land_tag=RES/"data/omniisle/tags/worldgen/structure/land_only.json"
land_tag.parent.mkdir(parents=True, exist_ok=True)
import json
land_structures=[
    "fire_dragon_cave", "ice_dragon_cave", "lightning_dragon_cave",
    "fire_dragon_roost", "ice_dragon_roost", "lightning_dragon_roost",
    "cyclops_cave", "gorgon_temple", "graveyard", "hydra_cave",
    "mausoleum", "pixie_village"
]
land_tag.write_text(json.dumps({
    "replace": False,
    "values": [{"id": "iceandfire:"+name, "required": False} for name in land_structures]
}, indent=2)+"\n", encoding="utf-8")


print("Native Forge transformation applied")

# Additional registry-driven modded biomes and biome-gated structure generation.
biome_patch_file=Path("scripts/modded_biomes.py")
exec(compile(biome_patch_file.read_text(encoding="utf-8"), str(biome_patch_file), "exec"))

# Registry-driven structures and improved mod biome generation; no percentage system.
generation_patch_file=Path("scripts/biome_generation.py")
exec(compile(generation_patch_file.read_text(encoding="utf-8"), str(generation_patch_file), "exec"))

# Explicit full-Overworld mod replacements follow the original climate map.
automatic_patch_file=Path("scripts/automatic_biome_replacements.py")
exec(compile(automatic_patch_file.read_text(encoding="utf-8"), str(automatic_patch_file), "exec"))

# Follow native large climate regions and honour explicit external Overworld
# biome replacements, instead of layering small separate Voronoi patches.
coherent_patch_file=Path("scripts/coherent_modded_biomes.py")
exec(compile(coherent_patch_file.read_text(encoding="utf-8"), str(coherent_patch_file), "exec"))

# Beach protection and coherent north-cold to south-desert climate.
coast_patch_file=Path("scripts/coastal_latitude.py")
exec(compile(coast_patch_file.read_text(encoding="utf-8"), str(coast_patch_file), "exec"))

# Keep Aquamirae frozen-ocean Ice Maze zones off the northern shoreline.
aquamirae_patch_file=Path("scripts/aquamirae_northern_ocean.py")
exec(compile(aquamirae_patch_file.read_text(encoding="utf-8"), str(aquamirae_patch_file), "exec"))

# Conflict-safe feature sequencing for mixed vanilla/modded OmniIsle biome palettes.
feature_cycle_patch_file=Path("scripts/feature_cycle_compat.py")
exec(compile(feature_cycle_patch_file.read_text(encoding="utf-8"), str(feature_cycle_patch_file), "exec"))


