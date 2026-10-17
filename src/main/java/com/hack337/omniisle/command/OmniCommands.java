package com.hack337.omniisle.command;

import com.hack337.omniisle.worldgen.OmniBiomeSource;
import com.mojang.brigadier.Command;
import java.util.LinkedHashSet;
import java.util.StringJoiner;
import net.minecraft.commands.Commands;
import net.minecraft.core.Holder;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.biome.*;
import net.minecraftforge.event.RegisterCommandsEvent;

public final class OmniCommands {
    private OmniCommands() {}
    public static void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("omniisle").requires(src -> src.hasPermission(2))
           .then(Commands.literal("verify").executes(ctx -> {
                ServerLevel world = ctx.getSource().getLevel();
                BiomeSource source = world.getChunkSource().getGenerator().getBiomeSource();
                if (!(source instanceof OmniBiomeSource)) {
                    ctx.getSource().sendFailure(Component.literal("Not an OmniIsle world"));
                    return 0;
                }
                Climate.Sampler sampler = world.getChunkSource().randomState().sampler();
                int[][] locations = {{0,0},{256,0},{-256,0},{0,256},{0,-256},{768,0},{-768,0},{1536,1536}};
                LinkedHashSet<String> seen = new LinkedHashSet<>();
                StringJoiner samples = new StringJoiner(", ");
                for (int[] pos:locations) {
                    Holder<Biome> biome=source.getNoiseBiome(pos[0]>>2,16,pos[1]>>2,sampler);
                    String name=biome.unwrapKey().map(k->k.location().toString()).orElse("unknown");
                    seen.add(name);samples.add(pos[0]+"/"+pos[1]+"="+name);
                }
                ctx.getSource().sendSuccess(() -> Component.literal("OmniIsle active; sampled="+seen.size()), false);
                ctx.getSource().sendSuccess(() -> Component.literal(samples.toString()), false);
                return Command.SINGLE_SUCCESS;
           })));
    }
}
