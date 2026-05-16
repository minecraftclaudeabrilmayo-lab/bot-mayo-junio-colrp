import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import obtener_cedula, eliminar_cedula

GUILD_ID          = int(os.getenv("GUILD_ID", "1502814593267929229"))
CANAL_INFO_ID     = int(os.getenv("CANAL_INFO_ID", "1503377019474415777"))
ROL_MOD_ID        = int(os.getenv("ROL_MOD_ID", "1502815947759550624"))
ROL_ADMIN_ID      = int(os.getenv("ROL_ADMIN_ID", "1503199431913377832"))

def tiene_rol(interaction: discord.Interaction, *rol_ids: int) -> bool:
    return any(r.id in rol_ids for r in interaction.user.roles)

def embed_cedula(cedula: dict, titulo: str) -> discord.Embed:
    embed = discord.Embed(
        title=titulo,
        color=discord.Color.from_str("#003087")
    )
    embed.add_field(name="Nombres", value=cedula["nombres"], inline=True)
    embed.add_field(name="Apellidos", value=cedula["apellidos"], inline=True)
    embed.add_field(name="Fecha Nac.", value=cedula["fecha_nacimiento"], inline=True)
    embed.add_field(name="Lugar Nac.", value=cedula["lugar_nacimiento"], inline=True)
    embed.add_field(name="Sexo", value=cedula["sexo"], inline=True)
    embed.add_field(name="F. Expiración", value=cedula["fecha_expiracion"], inline=True)
    if cedula.get("imagen_url"):
        embed.set_image(url=cedula["imagen_url"])
    embed.set_footer(text=f"Personaje #{cedula['personaje_num']} • Colombia Roleplay")
    return embed


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /enviar-cedula ──────────────────────────────────────────────────────
    @app_commands.command(name="enviar-cedula", description="[Mod] Envía la cédula al DM del usuario.")
    @app_commands.describe(
        usuario="Usuario de Discord",
        numero_personaje="Número de personaje (1 o 2)"
    )
    @app_commands.choices(numero_personaje=[
        app_commands.Choice(name="Personaje 1", value=1),
        app_commands.Choice(name="Personaje 2", value=2),
    ])
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def enviar_cedula(self, interaction: discord.Interaction, usuario: discord.Member, numero_personaje: int):
        if not tiene_rol(interaction, ROL_MOD_ID, ROL_ADMIN_ID):
            await interaction.response.send_message("❌ Solo moderadores pueden usar este comando.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        cedula = await obtener_cedula(str(usuario.id), numero_personaje)
        if not cedula:
            await interaction.followup.send(
                f"❌ {usuario.mention} no tiene una cédula registrada para el personaje #{numero_personaje}.",
                ephemeral=True
            )
            return

        embed = embed_cedula(cedula, f"🇨🇴 Cédula de Ciudadanía — Personaje #{numero_personaje}")
        embed.description = f"Emitida por Colombia Roleplay • Moderador: {interaction.user}"

        try:
            await usuario.send(embed=embed)
            await interaction.followup.send(
                f"✅ Cédula del personaje #{numero_personaje} enviada al DM de {usuario.mention}.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ No se pudo enviar DM a {usuario.mention}. Tiene los mensajes privados cerrados.",
                ephemeral=True
            )

    # ── /ver-dni ────────────────────────────────────────────────────────────
    @app_commands.command(name="ver-dni", description="Muestra tu cédula generada.")
    @app_commands.describe(numero_personaje="Número de personaje (1 o 2)")
    @app_commands.choices(numero_personaje=[
        app_commands.Choice(name="Personaje 1", value=1),
        app_commands.Choice(name="Personaje 2", value=2),
    ])
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ver_dni(self, interaction: discord.Interaction, numero_personaje: int):
        await interaction.response.defer(ephemeral=True)

        cedula = await obtener_cedula(str(interaction.user.id), numero_personaje)
        if not cedula:
            canal_info = interaction.guild.get_channel(CANAL_INFO_ID)
            mention = canal_info.mention if canal_info else f"<#{CANAL_INFO_ID}>"
            await interaction.followup.send(
                f"❌ No tenés una cédula para el personaje #{numero_personaje}.\n"
                f"🔹 Podés crearla en {mention} usando el botón **📄 Crear Cédula**.",
                ephemeral=True
            )
            return

        embed = embed_cedula(cedula, f"🇨🇴 Tu Cédula — Personaje #{numero_personaje}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /dni-administrativo ─────────────────────────────────────────────────
    @app_commands.command(name="dni-administrativo", description="[Mod] Ver la cédula de cualquier usuario.")
    @app_commands.describe(
        usuario="Usuario de Discord",
        numero_personaje="Número de personaje (1 o 2)"
    )
    @app_commands.choices(numero_personaje=[
        app_commands.Choice(name="Personaje 1", value=1),
        app_commands.Choice(name="Personaje 2", value=2),
    ])
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def dni_administrativo(self, interaction: discord.Interaction, usuario: discord.Member, numero_personaje: int):
        if not tiene_rol(interaction, ROL_MOD_ID, ROL_ADMIN_ID):
            await interaction.response.send_message("❌ Solo moderadores pueden usar este comando.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        cedula = await obtener_cedula(str(usuario.id), numero_personaje)
        if not cedula:
            await interaction.followup.send(
                f"❌ {usuario.mention} no tiene cédula registrada para el personaje #{numero_personaje}.",
                ephemeral=True
            )
            return

        embed = embed_cedula(cedula, f"🔍 [Admin] Cédula de {usuario.display_name} — Personaje #{numero_personaje}")
        embed.set_author(name=f"{usuario} ({usuario.id})", icon_url=usuario.display_avatar.url)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /realizar-ck ────────────────────────────────────────────────────────
    @app_commands.command(name="realizar-ck", description="[Mod] Elimina permanentemente la cédula de un personaje.")
    @app_commands.describe(
        usuario="Usuario de Discord",
        numero_personaje="Número de personaje (1 o 2)"
    )
    @app_commands.choices(numero_personaje=[
        app_commands.Choice(name="Personaje 1", value=1),
        app_commands.Choice(name="Personaje 2", value=2),
    ])
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def realizar_ck(self, interaction: discord.Interaction, usuario: discord.Member, numero_personaje: int):
        if not tiene_rol(interaction, ROL_MOD_ID, ROL_ADMIN_ID):
            await interaction.response.send_message("❌ Solo moderadores pueden usar este comando.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        cedula = await obtener_cedula(str(usuario.id), numero_personaje)
        if not cedula:
            await interaction.followup.send(
                f"❌ {usuario.mention} no tiene cédula para el personaje #{numero_personaje}.",
                ephemeral=True
            )
            return

        nombre_personaje = f"{cedula['nombres']} {cedula['apellidos']}"
        eliminado = await eliminar_cedula(str(usuario.id), numero_personaje)

        if eliminado:
            # Notificar al usuario
            try:
                embed_notif = discord.Embed(
                    title="💀 CK Ejecutado",
                    description=(
                        f"Tu personaje **{nombre_personaje}** (#{numero_personaje}) "
                        f"ha sido eliminado definitivamente.\n\n"
                        f"Este slot está ahora disponible para un nuevo personaje."
                    ),
                    color=discord.Color.red()
                )
                embed_notif.set_footer(text="Colombia Roleplay • Sistema de Cédulas")
                await usuario.send(embed=embed_notif)
            except discord.Forbidden:
                pass  # Usuario con DM cerrado, continuar igual

            await interaction.followup.send(
                f"✅ CK ejecutado. El personaje **{nombre_personaje}** (#{numero_personaje}) "
                f"de {usuario.mention} ha sido eliminado.",
                ephemeral=True
            )
        else:
            await interaction.followup.send("❌ No se pudo eliminar la cédula. Intentá de nuevo.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
