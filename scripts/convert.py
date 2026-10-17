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
    private ForgeEditorButton() {}

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
    ("super.render(context, mouseX, mouseY, delta);", "omniMouseX = mouseX; omniMouseY = mouseY;\n        super.render(context, mouseX, mouseY, delta);"),
    ("drawChoiceList(context, mouseX, mouseY)", "drawChoiceList(context, omniMouseX, omniMouseY)"),
    ("ResourceLocation.fromNamespaceAndPath(", "new ResourceLocation("),
    ("double horizontalAmount, double verticalAmount)", "double verticalAmount)"),
    ("super.mouseScrolled(mouseX, mouseY, horizontalAmount, verticalAmount)",
     "super.mouseScrolled(mouseX, mouseY, verticalAmount)"),
    ("public void renderBackground(GuiGraphics context, int mouseX, int mouseY, float delta)",
     "public void renderBackground(GuiGraphics context)"),
    ("super.renderBackground(context, mouseX, mouseY, delta)",
     "super.renderBackground(context)"),
])
# GUI dimensions and drawing methods are mostly unchanged from 1.21.1, except background API.
replace("client/BiomeSelectionScreen.java",[
    ("final class BiomeSelectionScreen extends Screen {", "final class BiomeSelectionScreen extends Screen {\n    private int omniMouseX, omniMouseY;\n    @Override public void render(GuiGraphics g, int mx, int my, float p) {\n        omniMouseX=mx; omniMouseY=my; super.render(g,mx,my,p);\n    }"),
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
replace("mixin/client/WorldTypeEditorMixin.java",[
    ("ResourceLocation.fromNamespaceAndPath(", "new ResourceLocation("),
    ("private void omniisle$initializeButton(CreateWorldScreen screen, CallbackInfo ci) {",
     "private void omniisle$initializeButton(CallbackInfo ci) {"),
    ("omniisle$updateButton(screen.getUiState());", "omniisle$updateButton(this$0.getUiState());"),
    ("@Inject(method = \"lambda$new$3\", at = @At(\"TAIL\"))",
     "@Inject(method = \"tick\", at = @At(\"TAIL\"))"),
    ("private void omniisle$enableEditor(WorldCreationUiState creator, CallbackInfo ci) {",
     "private void omniisle$enableEditor(CallbackInfo ci) {"),
    ("omniisle$updateButton(creator);", "omniisle$updateButton(this$0.getUiState());")
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
    mixins.write_text(json.dumps(cfg, indent=2)+"\n")
print("Native Forge transformation applied")
