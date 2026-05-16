import psycopg2
import psycopg2.extras
import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@contextmanager
def cursor():
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cedulas (
                id SERIAL PRIMARY KEY,
                discord_id TEXT NOT NULL,
                personaje_num INTEGER NOT NULL CHECK (personaje_num IN (1, 2)),
                apellidos TEXT NOT NULL,
                nombres TEXT NOT NULL,
                fecha_nacimiento TEXT NOT NULL,
                lugar_nacimiento TEXT NOT NULL,
                sexo TEXT NOT NULL,
                fecha_expiracion TEXT NOT NULL,
                roblox_url TEXT NOT NULL,
                imagen_url TEXT,
                tipo TEXT NOT NULL DEFAULT 'cedula',
                creado_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(discord_id, personaje_num)
            );
        """)
    print("✅ Base de datos inicializada")

async def guardar_cedula(discord_id: str, personaje_num: int, datos: dict, imagen_url: str, tipo: str = "cedula"):
    with cursor() as cur:
        cur.execute("""
            INSERT INTO cedulas 
                (discord_id, personaje_num, apellidos, nombres, fecha_nacimiento, lugar_nacimiento, sexo, fecha_expiracion, roblox_url, imagen_url, tipo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (discord_id, personaje_num)
            DO UPDATE SET
                apellidos = EXCLUDED.apellidos,
                nombres = EXCLUDED.nombres,
                fecha_nacimiento = EXCLUDED.fecha_nacimiento,
                lugar_nacimiento = EXCLUDED.lugar_nacimiento,
                sexo = EXCLUDED.sexo,
                fecha_expiracion = EXCLUDED.fecha_expiracion,
                roblox_url = EXCLUDED.roblox_url,
                imagen_url = EXCLUDED.imagen_url,
                tipo = EXCLUDED.tipo,
                creado_at = NOW()
        """,
        (
            discord_id,
            personaje_num,
            datos["apellidos"],
            datos["nombres"],
            datos["fecha_nacimiento"],
            datos["lugar_nacimiento"],
            datos["sexo"],
            datos["fecha_expiracion"],
            datos["roblox_url"],
            imagen_url,
            tipo
        ))

async def obtener_cedula(discord_id: str, personaje_num: int):
    with cursor() as cur:
        cur.execute("""
            SELECT * FROM cedulas WHERE discord_id = %s AND personaje_num = %s
        """, (discord_id, personaje_num))
        row = cur.fetchone()
        return dict(row) if row else None

async def eliminar_cedula(discord_id: str, personaje_num: int):
    with cursor() as cur:
        cur.execute("""
            DELETE FROM cedulas WHERE discord_id = %s AND personaje_num = %s
        """, (discord_id, personaje_num))
        return cur.rowcount > 0
