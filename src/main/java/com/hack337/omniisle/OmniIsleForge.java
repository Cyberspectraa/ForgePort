package com.hack337.omniisle;

import com.hack337.omniisle.worldgen.*;
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
import net.minecraftforge.registries.RegistryObject;

@Mod(OmniIsleForge.MODID)
public final class OmniIsleForge {
    public static final String MODID = "omniisle";

    private static final DeferredRegister<Codec<? extends BiomeSource>> BIOMES =
        DeferredRegister.create(Registries.BIOME_SOURCE, MODID);
    private static final DeferredRegister<Codec<? extends DensityFunction>> DENSITIES =
        DeferredRegister.create(Registries.DENSITY_FUNCTION_TYPE, MODID);
    private static final DeferredRegister<StructurePlacementType<?>> STRUCTURES =
        DeferredRegister.create(Registries.STRUCTURE_PLACEMENT, MODID);

    public static final RegistryObject<Codec<? extends BiomeSource>> ISLAND_BIOMES =
        BIOMES.register("island_biomes", () -> OmniBiomeSource.CODEC);
    public static final RegistryObject<Codec<? extends DensityFunction>> ISLAND_DENSITY =
        DENSITIES.register("island_continents", () -> IslandDensityFunction.CODEC.codec());
    public static final RegistryObject<StructurePlacementType<?>> FIXED_PLACEMENT =
        STRUCTURES.register("fixed", () -> SingleStructurePlacement.TYPE);

    public OmniIsleForge() {
        var bus = FMLJavaModLoadingContext.get().getModEventBus();
        BIOMES.register(bus);
        DENSITIES.register(bus);
        STRUCTURES.register(bus);
        MinecraftForge.EVENT_BUS.addListener(OmniCommands::register);
    }
}
