import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import re
import uuid

from database import guardar_cedula, obtener_cedula

GUILD_ID           = int(os.getenv("GUILD_ID", "1502814593267929229"))
CANAL_INFO_ID      = int(os.getenv("CANAL_INFO_ID", "1503377019474415777"))
CANAL_REGISTROS_ID = int(os.getenv("CANAL_REGISTROS_ID", "1503377208226484296"))

ROL_MOD_ID         = int(os.getenv("ROL_MOD_ID", "1502815947759550624"))
ROL_ADMIN_ID       = int(os.getenv("ROL_ADMIN_ID", "1503199431913377832"))
ROL_CIUDADANOS_ID  = int(os.getenv("ROL_CIUDADANOS_ID", "1502815998707892226"))

ASSETS_DIR = os.path.dirname(__file__)

def cargar_fuente(size):
    try:
        return ImageFont.truetype(os.path.join(ASSETS_DIR, "font.ttf"), size)
    except:
        return ImageFont.load_default()

def extraer_user_id_roblox(url: str):
    match = re.search(r'/users/(\d+)/', url)
    return match.group(1) if match else None

def obtener_avatar_roblox(url: str):
    user_id = extraer_user_id_roblox(url)
    if not user_id:
        return None
    try:
        api_url = (
            f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
            f"?userIds={user_id}&size=420x420&format=Png&isCircular=false"
        )
        resp = requests.get(api_url, timeout=10)
        img_url = resp.json()["data"][0]["imageUrl"]
        img_resp = requests.get(img_url, timeout=10)
        return Image.open(io.BytesIO(img_resp.content)).convert("RGBA")
    except Exception as e:
        print(f"Error avatar Roblox: {e}")
        return None

def generar_dni(datos: dict) -> io.BytesIO:
    base_path = os.path.join(ASSETS_DIR, "dni_base.png")
    if not os.path.exists(base_path):
        raise FileNotFoundError("Falta dni_base.png")

    dni = Image.open(base_path).convert("RGBA")
    draw = ImageDraw.Draw(dni)

    fuente_label = cargar_fuente(18)
    fuente_dato  = cargar_fuente(22)

    color_dato  = (0, 48, 135)
    color_label = (100, 100, 100)

    avatar = obtener_avatar_roblox(datos.get("roblox_url", ""))
    if avatar:
        avatar = avatar.resize((175, 220), Image.LANCZOS)
        dni.paste(avatar, (32, 65), avatar)

    x = 245
    campos = [
        (80,  100, "APELLIDOS",           datos.get("apellidos", "")),
        (150, 170, "NOMBRES",             datos.get("nombres", "")),
        (220, 240, "FECHA DE NACIMIENTO", datos.get("fecha_nacimiento", "")),
        (290, 310, "LUGAR DE NACIMIENTO", datos.get("lugar_nacimiento", "")),
        (360, 380, "FECHA DE EXPIRACIÓN", datos.get("fecha_expiracion", "")),
    ]
    for label_y, dato_y, label_txt, dato_txt in campos:
        draw.text((x, label_y), label_txt, fill=color_label, font=fuente_label)
        draw.text((x, dato_y),  dato_txt,  fill=color_dato,  font=fuente_dato)

    draw.text((x + 370, 220), "SEXO",                fill=color_label, font=fuente_label)
    draw.text((x + 370, 240), datos.get("sexo", ""), fill=color_dato,  font=fuente_dato)

    buffer = io.BytesIO()
    dni.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

class ModalCedula(discord.ui.Modal):
    def __init__(self, tipo: str):
        titulo = {"crear": "📄 Crear Cédula", "renovar": "🔄 Renovar Cédula", "ck": "💀 Realizar CK"}.get(tipo, "Cédula")
        super().__init__(title=titulo, timeout=300)
        self.tipo = tipo

        self.roblox_url = discord.ui.TextInput(label="URL de perfil de Roblox", placeholder="https://www.roblox.com/users/123456/profile", required=True, max_length=200)
        self.apellidos  = discord.ui.TextInput(label="Apellidos", placeholder="Ej: García Martínez", required=True, max_length=60)
        self.nombres    = discord.ui.TextInput(label="Nombres", placeholder="Ej: Juan Carlos", required=True, max_length=60)
        self.fecha_nac  = discord.ui.TextInput(label="Fecha de nacimiento", placeholder="DD/MM/AAAA", required=True, max_length=20)
        self.lugar_sexo = discord.ui.TextInput(label="Lugar de nacimiento | Sexo | F. expiración", placeholder="Bogotá | M | 01/01/2030", required=True, max_length=100)

        self.add_item(self.roblox_url)
        self.add_item(self.apellidos)
        self.add_item(self.nombres)
        self.add_item(self.fecha_nac)
        self.add_item(self.lugar_sexo)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        partes = [p.strip() for p in self.lugar_sexo.value.split("|")]
        if len(partes) < 3:
            await interaction.followup.send("❌ El último campo debe tener formato: `Lugar | Sexo | Fecha expiración`", ephemeral=True)
            return

        lugar, sexo, fecha_exp = partes[0], partes[1], partes[2]

        datos = {
            "apellidos":        self.apellidos.value.upper(),
            "nombres":          self.nombres.value.upper(),
            "fecha_nacimiento": self.fecha_nac.value,
            "lugar_nacimiento": lugar.upper(),
            "sexo":             sexo.upper(),
            "fecha_expiracion": fecha_exp,
            "roblox_url":       self.roblox_url.value.strip(),
        }

        try:
            imagen_buffer = generar_dni(datos)
        except FileNotFoundError:
            await interaction.followup.send("❌ Falta la imagen base del DNI. Contactá a un administrador.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Error generando la cédula: `{e}`", ephemeral=True)
            return

        cedula1 = await obtener_cedula(str(interaction.user.id), 1)
        cedula2 = await obtener_cedula(str(interaction.user.id), 2)

        if self.tipo == "crear":
            if cedula1 and cedula2:
                await interaction.followup.send("❌ Ya tenés **2 personajes activos**. Realizá un CK para liberar un slot.", ephemeral=True)
                return
            personaje_num = 2 if cedula1 else 1
        elif self.tipo == "renovar":
            if cedula1:
                personaje_num = 1
            elif cedula2:
                personaje_num = 2
            else:
                await interaction.followup.send("❌ No tenés ninguna cédula activa para renovar.", ephemeral=True)
                return
        else:
            personaje_num = 1

        nombre_archivo = f"dni_{uuid.uuid4().hex}.png"

        canal_registros = interaction.guild.get_channel(CANAL_REGISTROS_ID)
        imagen_url = ""
        if canal_registros:
            imagen_buffer.seek(0)
            file = discord.File(imagen_buffer, filename=nombre_archivo)
            embed = discord.Embed(
                title=f"{'📄 Nueva Cédula' if self.tipo == 'crear' else '🔄 Cédula Renovada'}",
                description=f"**{datos['nombres']} {datos['apellidos']}**\nPersonaje #{personaje_num}",
                color=discord.Color.from_str("#003087")
            )
            embed.set_image(url=f"attachment://{nombre_archivo}")
            embed.set_footer(text=f"Emitido por: {interaction.user} | ID: {interaction.user.id}")
            msg = await canal_registros.send(embed=embed, file=file)
            if msg.attachments:
                imagen_url = msg.attachments[0].url

        await guardar_cedula(str(interaction.user.id), personaje_num, datos, imagen_url, self.tipo)

        await interaction.followup.send(
            f"✅ **Cédula generada correctamente** para el personaje #{personaje_num}.\nUn moderador la enviará a tu privado pronto.",
            ephemeral=True
        )

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

class CedulaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(VistaBotonCedula())

    @app_commands.command(name="setup-cedulas", description="[Admin] Publica el panel de cédulas.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setup_cedulas(self, interaction: discord.Interaction):
        if not any(r.id == ROL_ADMIN_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Solo administradores.", ephemeral=True)
            return

        canal = interaction.guild.get_channel(CANAL_INFO_ID)
        if not canal:
            await interaction.response.send_message("❌ Canal no encontrado.", ephemeral=True)
            return

        embed1 = discord.Embed(
            title="🇨🇴 Sistema de Cédulas — Colombia Roleplay",
            description="Bienvenido al sistema oficial de identificación ciudadana.\n\nAquí podrás **crear**, **renovar** o **eliminar** la cédula de tus personajes.\n\nCada ciudadano puede tener hasta **2 personajes activos** simultáneamente.",
            color=discord.Color.from_str("#003087")
        )
        embed2 = discord.Embed(
            title="📋 Procedimientos",
            description="**📄 Crear Cédula**\nRegistra un nuevo personaje con tu URL de Roblox y datos del personaje.\n\n**🔄 Renovar Cédula**\nActualiza los datos de un personaje existente.\n\n**💀 Realizar CK**\nElimina permanentemente un personaje. Esta acción **no tiene reversa**.",
            color=discord.Color.from_str("#FCD116")
        )
        embed2.set_footer(text="Colombia Roleplay • Sistema Oficial de Cédulas")

        await canal.send(embeds=[embed1, embed2], view=VistaBotonCedula())
        await interaction.response.send_message("✅ Panel publicado.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CedulaCog(bot))
