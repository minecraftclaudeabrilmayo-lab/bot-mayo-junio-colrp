import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import guardar_cedula, obtener_cedula

GUILD_ID            = int(os.getenv("GUILD_ID", "1502814593267929229"))
CANAL_INFO_ID       = int(os.getenv("CANAL_INFO_ID", "1503377019474415777"))
CANAL_REGISTROS_ID  = int(os.getenv("CANAL_REGISTROS_ID", "1503377208226484296"))
WEB_URL             = os.getenv("WEB_URL", "http://localhost:5000")

ROL_MOD_ID          = int(os.getenv("ROL_MOD_ID", "1502815947759550624"))
ROL_ADMIN_ID        = int(os.getenv("ROL_ADMIN_ID", "1503199431913377832"))
ROL_CIUDADANOS_ID   = int(os.getenv("ROL_CIUDADANOS_ID", "1502815998707892226"))

# ─────────────────────────────────────────────
# MODALES
# ─────────────────────────────────────────────

class ModalCedula(discord.ui.Modal):
    def __init__(self, tipo: str):
        titulo = {
            "crear": "📄 Crear Cédula",
            "renovar": "🔄 Renovar Cédula",
            "ck": "💀 Realizar CK"
        }.get(tipo, "Cédula")
        super().__init__(title=titulo, timeout=300)
        self.tipo = tipo

        self.roblox_url = discord.ui.TextInput(
            label="URL de perfil de Roblox",
            placeholder="https://www.roblox.com/users/123456/profile",
            required=True, max_length=200
        )
        self.apellidos = discord.ui.TextInput(
            label="Apellidos",
            placeholder="Ej: García Martínez",
            required=True, max_length=60
        )
        self.nombres = discord.ui.TextInput(
            label="Nombres",
            placeholder="Ej: Juan Carlos",
            required=True, max_length=60
        )
        self.fecha_nac = discord.ui.TextInput(
            label="Fecha de nacimiento",
            placeholder="DD/MM/AAAA",
            required=True, max_length=20
        )
        self.lugar_nac = discord.ui.TextInput(
            label="Lugar de nacimiento  |  Sexo  |  F. expiración",
            placeholder="Bogotá | M | 01/01/2030",
            required=True, max_length=100
        )

        self.add_item(self.roblox_url)
        self.add_item(self.apellidos)
        self.add_item(self.nombres)
        self.add_item(self.fecha_nac)
        self.add_item(self.lugar_nac)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        partes = [p.strip() for p in self.lugar_nac.value.split("|")]
        if len(partes) < 3:
            await interaction.followup.send(
                "❌ El último campo debe tener formato: `Lugar | Sexo | Fecha expiración`",
                ephemeral=True
            )
            return

        lugar, sexo, fecha_exp = partes[0], partes[1], partes[2]

        datos = {
            "apellidos":        self.apellidos.value.upper(),
            "nombres":          self.nombres.value.upper(),
            "fecha_nacimiento":  self.fecha_nac.value,
            "lugar_nacimiento":  lugar.upper(),
            "sexo":             sexo.upper(),
            "fecha_expiracion":  fecha_exp,
            "roblox_url":       self.roblox_url.value.strip(),
        }

        # Llamar a la web para generar la imagen
        try:
            async with aiohttp.ClientSession() as session:
                payload = {**datos, "discord_id": str(interaction.user.id), "tipo": self.tipo}
                async with session.post(f"{WEB_URL}/generar", json=payload) as resp:
                    if resp.status != 200:
                        raise Exception(f"Web respondió {resp.status}")
                    result = await resp.json()
                    imagen_url = result["imagen_url"]
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error al generar la cédula: `{e}`\nIntentá de nuevo más tarde.",
                ephemeral=True
            )
            return

        # Determinar número de personaje (el que no tenga ocupado)
        personaje_num = 1
        cedula1 = await obtener_cedula(str(interaction.user.id), 1)
        cedula2 = await obtener_cedula(str(interaction.user.id), 2)

        if self.tipo == "crear":
            if cedula1 and cedula2:
                await interaction.followup.send(
                    "❌ Ya tenés **2 personajes activos**. Realizá un CK para liberar un slot.",
                    ephemeral=True
                )
                return
            personaje_num = 2 if cedula1 else 1
        elif self.tipo == "renovar":
            # Renovar el personaje 1 si existe, sino el 2
            if cedula1:
                personaje_num = 1
            elif cedula2:
                personaje_num = 2
            else:
                await interaction.followup.send(
                    "❌ No tenés ninguna cédula activa para renovar.",
                    ephemeral=True
                )
                return

        # Guardar en DB
        await guardar_cedula(str(interaction.user.id), personaje_num, datos, imagen_url, self.tipo)

        # Enviar al canal de registros
        canal_registros = interaction.guild.get_channel(CANAL_REGISTROS_ID)
        if canal_registros:
            embed = discord.Embed(
                title=f"{'📄 Nueva Cédula' if self.tipo == 'crear' else '🔄 Cédula Renovada'}",
                description=f"**{datos['nombres']} {datos['apellidos']}**\nPersonaje #{personaje_num}",
                color=discord.Color.from_str("#003087")
            )
            embed.set_image(url=imagen_url)
            embed.set_footer(text=f"Emitido por: {interaction.user} | ID: {interaction.user.id}")
            await canal_registros.send(embed=embed)

        await interaction.followup.send(
            f"✅ **Cédula generada correctamente** para el personaje #{personaje_num}.\n"
            f"Un moderador la enviará a tu privado pronto.",
            ephemeral=True
        )


# ─────────────────────────────────────────────
# VISTA DE BOTONES
# ─────────────────────────────────────────────

class VistaBotonCedula(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📄 Crear Cédula", style=discord.ButtonStyle.primary, custom_id="btn_crear")
    async def crear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalCedula("crear"))

    @discord.ui.button(label="🔄 Renovar Cédula", style=discord.ButtonStyle.secondary, custom_id="btn_renovar")
    async def renovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalCedula("renovar"))

    @discord.ui.button(label="💀 Realizar CK", style=discord.ButtonStyle.danger, custom_id="btn_ck")
    async def ck(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalCedula("ck"))


# ─────────────────────────────────────────────
# COG PRINCIPAL
# ─────────────────────────────────────────────

class CedulaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(VistaBotonCedula())  # Persistente

    @app_commands.command(name="setup-cedulas", description="[Admin] Publica el panel de cédulas en el canal.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_cedulas(self, interaction: discord.Interaction):
        if not any(r.id == ROL_ADMIN_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
            return

        canal = interaction.guild.get_channel(CANAL_INFO_ID)
        if not canal:
            await interaction.response.send_message("❌ Canal de info no encontrado.", ephemeral=True)
            return

        embed1 = discord.Embed(
            title="🇨🇴 Sistema de Cédulas — Colombia Roleplay",
            description=(
                "Bienvenido al sistema oficial de identificación ciudadana.\n\n"
                "Aquí podrás **crear**, **renovar** o **eliminar** la cédula de tus personajes.\n\n"
                "Cada ciudadano puede tener hasta **2 personajes activos** simultáneamente."
            ),
            color=discord.Color.from_str("#003087")
        )
        embed1.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/2/21/Flag_of_Colombia.svg")

        embed2 = discord.Embed(
            title="📋 Procedimientos",
            description=(
                "**📄 Crear Cédula**\n"
                "Registra un nuevo personaje. Necesitarás tu URL de perfil de Roblox y datos del personaje.\n\n"
                "**🔄 Renovar Cédula**\n"
                "Actualiza los datos de un personaje existente.\n\n"
                "**💀 Realizar CK**\n"
                "Elimina permanentemente un personaje. Esta acción **no tiene reversa**."
            ),
            color=discord.Color.from_str("#FCD116")
        )
        embed2.set_footer(text="Colombia Roleplay • Sistema Oficial de Cédulas")

        await canal.send(embeds=[embed1, embed2], view=VistaBotonCedula())
        await interaction.response.send_message("✅ Panel publicado correctamente.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CedulaCog(bot))
