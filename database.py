import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
        await init_db(_pool)
    return _pool

async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
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
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO cedulas 
                (discord_id, personaje_num, apellidos, nombres, fecha_nacimiento, lugar_nacimiento, sexo, fecha_expiracion, roblox_url, imagen_url, tipo)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
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
        )

async def obtener_cedula(discord_id: str, personaje_num: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM cedulas WHERE discord_id = $1 AND personaje_num = $2
        """, discord_id, personaje_num)
        return dict(row) if row else None

async def eliminar_cedula(discord_id: str, personaje_num: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM cedulas WHERE discord_id = $1 AND personaje_num = $2
        """, discord_id, personaje_num)
        return result != "DELETE 0"
