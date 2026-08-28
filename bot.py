import os
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)
NORMAL_CHANNEL_ID = 1542808823776026656
START_DICK_SIZE = 0
DAILY_REWARD = 50_000
ROLE_CREATE_COST = 200_000
ROLE_ADMIN_ID = 1542839885055004672
OWNER_ID = 1455564327351226380

# Discord CDN emoji links used by the server's embeds.
EMOJI_DICK = "https://discord.com/assets/d59af318cacdcf3b.svg"
EMOJI_GROWTH = "https://discord.com/assets/a59b48874be63ed4.svg"
EMOJI_GIFT = "https://discord.com/assets/949f113339307625.svg"
EMOJI_MONEY = "https://discord.com/assets/60e4658040396168.svg"

MIN_COINFLIP_BET = 100
MIN_COOKIE_BET = 1_000
MAX_BET = 2_000_000_000

# ---------------- CASES ----------------
CASE_DATA = {
    "Звичайний": {
        "price": 5_000, "emoji": "🟢",
        "cars": [
            ("Daewoo Lanos", 2_500, False), ("Chevrolet Aveo (T250)", 3_000, False),
            ("Opel Astra G", 3_500, False), ("Skoda Fabia I", 3_800, False),
            ("Renault Megane II", 4_200, False), ("Volkswagen Golf IV", 4_500, False),
            ("Peugeot 307", 4_700, False), ("Ford Focus I", 5_000, False),
            ("Nissan Almera N16", 5_200, False), ("Honda Civic VI", 5_500, False),
            ("Mitsubishi Lancer IX", 5_800, False), ("Mazda 323 (BJ)", 6_000, False),
            ("Hyundai Elantra XD", 6_300, False), ("Toyota Corolla (E120)", 6_800, False),
            ("BMW 3 Series (E36)", 7_500, True), ("Audi A4 (B6)", 7_800, True),
            ("Mercedes-Benz W124", 8_500, True),
        ],
    },
    "Рідкий": {
        "price": 10_000, "emoji": "🔵",
        "cars": [
            ("Renault Fluence", 6_800, False), ("Ford Mondeo Mk4", 7_500, False),
            ("Skoda Octavia A5 FL", 8_000, False), ("Kia Cerato II", 8_300, False),
            ("Volkswagen Jetta VI", 8_700, False), ("Honda Civic VIII (5D / Sedan)", 9_000, False),
            ("Hyundai Sonata YF", 9_500, False), ("Toyota Corolla (E150)", 10_000, False),
            ("Mitsubishi Lancer X", 10_500, False), ("Volkswagen Passat B7", 11_500, False),
            ("Subaru Legacy B14", 12_000, False), ("Mazda 6 (GH)", 12_500, False),
            ("Nissan Teana (J32)", 13_000, False), ("BMW 3 Series (E90)", 14_000, True),
            ("Audi A4 (B8)", 14_500, True), ("Lexus IS 250 (XE10 / XE20)", 15_500, True),
            ("Infiniti G37", 16_500, True),
        ],
    },
    "Епічний": {
        "price": 20_000, "emoji": "🟣",
        "cars": [
            ("Ford Fusion Mk2 (USA)", 12_000, False), ("Volkswagen CC", 13_500, False),
            ("Hyundai Genesis DH", 15_000, False), ("BMW 5 Series (F10)", 16_000, False),
            ("Kia Optima / K5 (JF)", 17_000, False), ("Lexus IS 250 (XE20)", 18_000, False),
            ("Volvo S60 II", 19_000, False), ("Audi A6 (C7)", 20_000, False),
            ("Acura TLX (UB1)", 21_500, False), ("Mercedes-Benz E-Class (W212)", 23_000, False),
            ("BMW 4 Series (F32)", 24_500, False), ("Mazda CX-5 (KF)", 26_000, False),
            ("Subaru WRX STI (VA)", 27_500, False), ("Ford Mustang (S550, V6 / EcoBoost)", 29_000, True),
            ("Alfa Romeo Giulia (952)", 31_000, True), ("Porsche Cayenne (92A)", 33_000, True),
            ("Chevrolet Camaro VI", 35_000, True),
        ],
    },
    "Міфічний": {
        "price": 50_000, "emoji": "🟠",
        "cars": [
            ("Porsche Cayenne II (FL)", 34_000, False), ("BMW M4 (F82)", 38_000, False),
            ("Lexus GS F", 40_000, False), ("Audi RS5 (B8 / B9)", 42_000, False),
            ("Jaguar F-Type (S/V6)", 44_000, False), ("Tesla Model S Plaid / Performance", 47_000, False),
            ("Alfa Romeo Giulia Quadrifoglio", 48_500, False), ("Mercedes-AMG C 63 (W205)", 50_000, False),
            ("BMW M5 (F10)", 53_000, False), ("Audi RS6 (C7)", 55_000, False),
            ("Chevrolet Corvette Stingray (C7)", 58_000, False), ("Ford Mustang Shelby GT350", 62_000, False),
            ("Porsche 911 Carrera (997)", 65_000, False), ("BMW M5 (F90)", 70_000, True),
            ("Nissan GT-R (R35)", 75_000, True), ("Mercedes-AMG E 63 S (W213)", 80_000, True),
            ("Dodge Viper SRT-10", 88_000, True),
        ],
    },
    "Легендарний": {
        "price": 100_000, "emoji": "🟡",
        "cars": [
            ("BMW M8 Competition (F92)", 72_000, False), ("Audi R8 V10 Plus", 80_000, False),
            ("Nissan GT-R Nismo", 85_000, False), ("Mercedes-AMG GT R", 90_000, False),
            ("Porsche Panamera Turbo S (971)", 95_000, False), ("Aston Martin Vantage", 100_000, False),
            ("Bentley Continental GT II", 110_000, False), ("Lamborghini Huracán", 120_000, False),
            ("Porsche 911 Turbo S (991.2)", 130_000, False), ("Ferrari 458 Italia", 140_000, False),
            ("Ford GT (2005)", 150_000, False), ("McLaren 720S", 165_000, True),
            ("Lamborghini Aventador LP700-4", 175_000, True), ("Porsche 911 GT3 (991.2)", 185_000, True),
            ("Ferrari 488 Pista", 210_000, True), ("Mercedes-Benz SLR McLaren", 240_000, True),
            ("Porsche Carrera GT", 300_000, True),
        ],
    },
}

CASE_WEIGHTS = [17 - i for i in range(17)]  # chance decreases with vehicle value
CASE_TOTAL_WEIGHT = sum(CASE_WEIGHTS)

# ---------------- REAL ESTATE ----------------
HOUSES = [
    ('Кімната в гуртожитку', 50000),
    ('Смарт-квартира', 90000),
    ('1-кімнатна квартира', 150000),
    ('2-кімнатна квартира', 230000),
    ('3-кімнатна квартира', 320000),
    ('Квартира в новобудові', 450000),
    ('Пентхаус у центрі', 650000),
    ('Апартаменти бізнес-класу', 850000),
    ('Дворівневі апартаменти', 1100000),
    ('Таунхаус', 1400000),
    ('Невеликий заміський будинок', 1800000),
    ('Сучасний приватний будинок', 2300000),
    ('Будинок із гаражем', 2900000),
    ('Сімейний котедж', 3600000),
    ('Котедж біля озера', 4500000),
    ('Заміський маєток', 5500000),
    ('Великий маєток', 6800000),
    ('Панорамний будинок', 8200000),
    ('Преміум-вілла', 10000000),
    ('Вілла з басейном', 12500000),
    ('Вілла на пагорбі', 15000000),
    ('Розкішна вілла', 18000000),
    ('Елітний маєток', 22000000),
    ('Президентська резиденція', 28000000),
    ('Острівна супер-вілла', 40000000)
]
HOUSES_BY_NAME = dict(HOUSES)
MASTURBATION_COOLDOWN = 2 * 60 * 60
MASTURBATION_DURATION = 30

def case_chances(rarity: str):
    return [
        (car[0], car[1], car[2], weight / CASE_TOTAL_WEIGHT * 100)
        for car, weight in zip(CASE_DATA[rarity]["cars"], CASE_WEIGHTS)
    ]

def roll_case(rarity: str):
    chances = case_chances(rarity)
    return random.choices(chances, weights=[x[3] for x in chances], k=1)[0]

def add_inventory_item(user_id: int, item_type: str, item_key: str, quantity: int = 1):
    ensure_user(user_id)
    conn = db()
    conn.execute("""INSERT INTO inventory_items(user_id,item_type,item_key,quantity)
                    VALUES(?,?,?,?)
                    ON CONFLICT(user_id,item_type,item_key)
                    DO UPDATE SET quantity=quantity+excluded.quantity""",
                 (user_id, item_type, item_key, quantity))
    conn.commit(); conn.close()

def remove_inventory_item(user_id: int, item_type: str, item_key: str, quantity: int = 1) -> bool:
    conn = db()
    try:
        cur = conn.execute("""UPDATE inventory_items SET quantity=quantity-?
                              WHERE user_id=? AND item_type=? AND item_key=? AND quantity>=?""",
                           (quantity,user_id,item_type,item_key,quantity))
        if cur.rowcount != 1:
            conn.rollback(); return False
        conn.execute("DELETE FROM inventory_items WHERE user_id=? AND item_type=? AND item_key=? AND quantity<=0",
                     (user_id,item_type,item_key))
        conn.commit(); return True
    finally:
        conn.close()

def get_inventory_items(user_id: int, item_type: Optional[str] = None):
    conn = db()
    if item_type:
        rows = conn.execute("""SELECT * FROM inventory_items WHERE user_id=? AND item_type=? AND quantity>0
                               ORDER BY item_type,item_key""",(user_id,item_type)).fetchall()
    else:
        rows = conn.execute("""SELECT * FROM inventory_items WHERE user_id=? AND quantity>0
                               ORDER BY item_type,item_key""",(user_id,)).fetchall()
    conn.close(); return rows

def add_case_inventory(user_id: int, rarity: str, quantity: int):
    add_inventory_item(user_id, "case", rarity, quantity)

def remove_case_inventory(user_id: int, rarity: str, quantity: int = 1) -> bool:
    return remove_inventory_item(user_id, "case", rarity, quantity)

def get_case_inventory(user_id: int):
    return get_inventory_items(user_id, "case")

COOKIE_WAIT_SECONDS = 10 * 60
COOKIE_COUNTDOWN_SECONDS = 10
COOKIE_PLAY_SECONDS = 60

ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing in .env / Railway Variables")

# ============================================================
# DATABASE / RAILWAY PERSISTENCE
# ============================================================
# IMPORTANT:
# On Railway, create a Volume mounted at /data and set:
#     DB_PATH=/data/bot.db
# The bot refuses to silently fall back to the ephemeral container
# filesystem when running on Railway.
IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
DEFAULT_DB_PATH = "/data/bot.db" if IS_RAILWAY else os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.db")
DB_PATH = os.path.abspath(os.path.expanduser(os.getenv("DB_PATH", DEFAULT_DB_PATH).strip()))
BACKUP_DIR = os.path.abspath(os.path.expanduser(os.getenv("DB_BACKUP_DIR", os.path.join(os.path.dirname(DB_PATH), "backups")).strip()))
BACKUP_INTERVAL_SECONDS = max(60, int(os.getenv("DB_BACKUP_INTERVAL_SECONDS", "300")))
MAX_DB_BACKUPS = max(3, int(os.getenv("MAX_DB_BACKUPS", "30")))

if IS_RAILWAY and not DB_PATH.startswith("/data/"):
    raise RuntimeError(
        "SAFETY STOP: Railway detected, but DB_PATH is not inside /data. "
        "Attach a Railway Volume mounted at /data and set DB_PATH=/data/bot.db. "
        "The bot will NOT start with an unsafe ephemeral database."
    )

DB_LOCK = asyncio.Lock()
_backup_task: Optional[asyncio.Task] = None
_db_initialized = False


def _ensure_storage_dirs():
    db_dir = os.path.dirname(DB_PATH) or "."
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not os.access(db_dir, os.W_OK):
        raise RuntimeError(f"Database directory is not writable: {db_dir}")
    if not os.access(BACKUP_DIR, os.W_OK):
        raise RuntimeError(f"Backup directory is not writable: {BACKUP_DIR}")


def db():
    _ensure_storage_dirs()
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA wal_autocheckpoint=1000")
    # WAL is ideal for a single Railway bot process and safe across restarts.
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _table_columns(conn, table: str):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate_schema(conn):
    # Safe, additive migrations for databases created by older versions.
    migrations = {
        "users": {
            "username": "TEXT NOT NULL DEFAULT ''",
            "admin": "INTEGER NOT NULL DEFAULT 0",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "active_car": "TEXT",
            "primary_house": "TEXT",
        },
        "promos": {"created_at": "TEXT NOT NULL DEFAULT ''"},
        "promo_uses": {"used_at": "TEXT NOT NULL DEFAULT ''"},
    }
    for table, columns in migrations.items():
        existing = _table_columns(conn, table)
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _integrity_check(path: str) -> bool:
    if not os.path.exists(path) or os.path.getsize(path) < 4096:
        return False
    try:
        conn = sqlite3.connect(path, timeout=10)
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        return result == "ok"
    except Exception:
        return False


def _checkpoint_wal():
    try:
        conn = db()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except Exception as exc:
        print(f"[DB] WAL checkpoint warning: {exc!r}")


def _backup_once(reason: str = "scheduled") -> Optional[str]:
    _ensure_storage_dirs()
    if not os.path.exists(DB_PATH):
        return None

    # Make the SQLite backup from a consistent database snapshot.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    final_path = os.path.join(BACKUP_DIR, f"bot_{timestamp}_{reason}.db")
    temp_path = final_path + ".tmp"

    source = None
    target = None
    try:
        source = sqlite3.connect(DB_PATH, timeout=30)
        target = sqlite3.connect(temp_path)
        with target:
            source.backup(target, pages=256, sleep=0.05)
        target.close(); target = None
        source.close(); source = None

        if not _integrity_check(temp_path):
            raise RuntimeError("Backup integrity_check failed")
        os.replace(temp_path, final_path)
        _prune_backups()
        return final_path
    except Exception as exc:
        print(f"[DB] Backup failed ({reason}): {exc!r}")
        try:
            if target: target.close()
        except Exception: pass
        try:
            if source: source.close()
        except Exception: pass
        try:
            if os.path.exists(temp_path): os.remove(temp_path)
        except Exception: pass
        return None


def _prune_backups():
    files = []
    for name in os.listdir(BACKUP_DIR):
        if name.startswith("bot_") and name.endswith(".db"):
            path = os.path.join(BACKUP_DIR, name)
            if os.path.isfile(path):
                files.append((os.path.getmtime(path), path))
    files.sort(reverse=True)
    for _, path in files[MAX_DB_BACKUPS:]:
        try:
            os.remove(path)
        except OSError:
            pass


def _restore_latest_backup() -> bool:
    _ensure_storage_dirs()
    candidates = []
    for name in os.listdir(BACKUP_DIR):
        if name.startswith("bot_") and name.endswith(".db"):
            path = os.path.join(BACKUP_DIR, name)
            if os.path.isfile(path) and _integrity_check(path):
                candidates.append((os.path.getmtime(path), path))
    if not candidates:
        return False
    candidates.sort(reverse=True)
    latest = candidates[0][1]
    temp = DB_PATH + ".restore.tmp"
    try:
        src = sqlite3.connect(latest)
        dst = sqlite3.connect(temp)
        with dst:
            src.backup(dst, pages=256)
        src.close(); dst.close()
        if not _integrity_check(temp):
            raise RuntimeError("Restored DB failed integrity_check")
        os.replace(temp, DB_PATH)
        print(f"[DB] Restored database from backup: {latest}")
        return True
    except Exception as exc:
        print(f"[DB] Restore failed: {exc!r}")
        try:
            if os.path.exists(temp): os.remove(temp)
        except OSError:
            pass
        return False


def validate_database_startup():
    """Hard safety checks before the bot starts serving economy commands."""
    _ensure_storage_dirs()

    # If the main file disappeared but a verified backup exists, restore it
    # instead of silently starting with a brand-new empty economy.
    if not os.path.exists(DB_PATH):
        if _restore_latest_backup():
            print("[DB] Main database was missing; restored verified backup.")
        return

    if not _integrity_check(DB_PATH):
        print("[DB] WARNING: main database failed integrity_check. Trying latest valid backup...")
        if not _restore_latest_backup():
            raise RuntimeError(
                "Database is corrupt and no valid backup is available. "
                "Bot stopped to avoid making the situation worse."
            )


def database_health() -> dict:
    try:
        conn = db()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        promos = conn.execute("SELECT COUNT(*) FROM promos").fetchone()[0]
        conn.close()
        return {"ok": integrity == "ok", "integrity": integrity, "users": users, "promos": promos}
    except Exception as exc:
        return {"ok": False, "integrity": repr(exc), "users": -1, "promos": -1}


async def backup_loop():
    await asyncio.sleep(30)
    while not bot.is_closed():
        try:
            async with DB_LOCK:
                path = await asyncio.to_thread(_backup_once, "auto")
                if path:
                    print(f"[DB] Automatic backup: {path}")
        except Exception as exc:
            print(f"[DB] Backup loop error: {exc!r}")
        await asyncio.sleep(BACKUP_INTERVAL_SECONDS)


def init_db():
    global _db_initialized
    if _db_initialized:
        return
    validate_database_startup()
    # Preserve the pre-migration state before any schema changes.
    if os.path.exists(DB_PATH):
        _backup_once("pre_migration")
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL DEFAULT '',
        dick_size INTEGER NOT NULL DEFAULT 0,
        balance INTEGER NOT NULL DEFAULT 0,
        admin INTEGER NOT NULL DEFAULT 0,
        daily_at TEXT,
        dick_at TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS promos (
        code TEXT PRIMARY KEY,
        money INTEGER NOT NULL DEFAULT 0,
        dick INTEGER NOT NULL DEFAULT 0,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS promo_uses (
        code TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(code, user_id)
    );

    CREATE TABLE IF NOT EXISTS roles (
        role_id INTEGER PRIMARY KEY,
        guild_id INTEGER NOT NULL,
        owner_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        color INTEGER NOT NULL,
        price INTEGER NOT NULL DEFAULT 0,
        for_sale INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS role_inventory (
        user_id INTEGER NOT NULL,
        role_id INTEGER NOT NULL,
        added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, role_id)
    );

    CREATE TABLE IF NOT EXISTS case_inventory (
        user_id INTEGER NOT NULL,
        rarity TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(user_id, rarity)
    );

    CREATE TABLE IF NOT EXISTS inventory_items (
        user_id INTEGER NOT NULL,
        item_type TEXT NOT NULL,
        item_key TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, item_type, item_key)
    );

    CREATE TABLE IF NOT EXISTS market_listings (
        listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER NOT NULL,
        item_type TEXT NOT NULL,
        item_key TEXT NOT NULL,
        price INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        sold_at TEXT
    );

    CREATE TABLE IF NOT EXISTS masturbation_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        finishes_at TEXT NOT NULL,
        reward INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'running',
        finished_at TEXT
    );

    CREATE TABLE IF NOT EXISTS cookie_games (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER NOT NULL UNIQUE,
        proposer_id INTEGER NOT NULL,
        opponent_id INTEGER NOT NULL,
        bet INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'waiting',
        proposer_score INTEGER NOT NULL DEFAULT 0,
        opponent_score INTEGER NOT NULL DEFAULT 0,
        started_at TEXT,
        ended_at TEXT
    );

    CREATE TABLE IF NOT EXISTS number_games (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER NOT NULL UNIQUE,
        proposer_id INTEGER NOT NULL,
        opponent_id INTEGER NOT NULL,
        bet INTEGER NOT NULL,
        proposer_number INTEGER,
        opponent_number INTEGER,
        current_guesser_id INTEGER,
        status TEXT NOT NULL DEFAULT 'choosing',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ended_at TEXT
    );
    """)
    _migrate_schema(conn)
    # Move legacy case inventory into the unified /inventory storage once.
    conn.execute("""INSERT INTO inventory_items(user_id, item_type, item_key, quantity)\n                       SELECT user_id, 'case', rarity, quantity FROM case_inventory WHERE quantity > 0\n                       ON CONFLICT(user_id, item_type, item_key) DO UPDATE SET quantity=MAX(inventory_items.quantity, excluded.quantity)""")
    conn.commit()
    conn.close()
    _db_initialized = True


def ensure_user(user_id: int, username: str = ""):
    conn = db()
    conn.execute(
        "INSERT OR IGNORE INTO users(user_id, username, dick_size, balance) VALUES (?, ?, ?, 0)",
        (user_id, username, START_DICK_SIZE),
    )
    if username:
        conn.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    conn.commit()
    conn.close()


def get_user(user_id: int, username: str = ""):
    ensure_user(user_id, username)
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row


def money_add(user_id: int, amount: int):
    """Atomic balance change. Negative changes are rejected if balance is insufficient."""
    ensure_user(user_id)
    conn = db()
    try:
        if amount < 0:
            cur = conn.execute(
                "UPDATE users SET balance=balance+? WHERE user_id=? AND balance>=?",
                (amount, user_id, -amount),
            )
        else:
            cur = conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        ok = cur.rowcount == 1
        conn.commit()
        return ok
    finally:
        conn.close()


def money_set(user_id: int, amount: int):
    ensure_user(user_id)
    conn = db()
    conn.execute("UPDATE users SET balance=? WHERE user_id=?", (max(0, amount), user_id))
    conn.commit()
    conn.close()


def dick_set(user_id: int, amount: int):
    ensure_user(user_id)
    conn = db()
    conn.execute("UPDATE users SET dick_size=? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def set_cooldown(user_id: int, column: str):
    if column not in ("daily_at", "dick_at"):
        raise ValueError("bad column")
    ensure_user(user_id)
    now = datetime.now(timezone.utc).isoformat()
    conn = db()
    conn.execute(f"UPDATE users SET {column}=? WHERE user_id=?", (now, user_id))
    conn.commit()
    conn.close()


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def cooldown_left(value, seconds=86400):
    last = parse_time(value)
    if not last:
        return timedelta(0)
    left = (last + timedelta(seconds=seconds)) - datetime.now(timezone.utc)
    return max(left, timedelta(0))


def fmt_duration(td: timedelta):
    total = max(0, int(td.total_seconds()))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} д.")
    if hours:
        parts.append(f"{hours} год.")
    if minutes:
        parts.append(f"{minutes} хв.")
    if not parts:
        parts.append(f"{seconds} сек.")
    return " ".join(parts)


def money(n: int):
    return f"{n:,}"


def is_owner(user_id: int):
    return user_id == OWNER_ID

def is_admin(user_id: int):
    if user_id == OWNER_ID or user_id in ADMIN_IDS:
        return True
    return bool(get_user(user_id)["admin"])

def can_manage_admins(user_id: int):
    return is_owner(user_id)


def embed(title, description="", color=discord.Color.blurple()):
    return discord.Embed(title=title, description=description, color=color)


def get_setting(key: str):
    conn = db()
    row = conn.execute("SELECT value FROM bot_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_setting(key: str, value: str):
    conn = db()
    conn.execute("INSERT INTO bot_settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()


def delete_setting(key: str):
    conn = db()
    conn.execute("DELETE FROM bot_settings WHERE key=?", (key,))
    conn.commit()
    conn.close()


def consume_setting(key: str):
    """Atomically read-and-delete a one-shot setting."""
    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT value FROM bot_settings WHERE key=?", (key,)).fetchone()
        if row:
            conn.execute("DELETE FROM bot_settings WHERE key=?", (key,))
        conn.commit()
        return row["value"] if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def normal_channel_only(interaction: discord.Interaction) -> bool:
    # Owner and admins may use every command in every channel.
    return is_admin(interaction.user.id) or interaction.channel_id == NORMAL_CHANNEL_ID


async def reject_wrong_channel(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"❌ Цю команду можна використовувати тільки в <#{NORMAL_CHANNEL_ID}>.",
        ephemeral=True,
    )


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- DICK ----------------

@bot.tree.command(name="dick", description="Щодня змінити свій розмір")
async def dick(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)

    u = get_user(interaction.user.id, interaction.user.name)
    left = cooldown_left(u["dick_at"])
    if left.total_seconds() > 0:
        await interaction.response.send_message(
            f"⏳ Ти вже використовував команду сьогодні. До наступної спроби: **{fmt_duration(left)}**.",
            ephemeral=True,
        )
        return

    # First ever use is guaranteed to be positive.
    if u["dick_at"] is None:
        change = random.randint(1, 5)
    else:
        change = random.randint(-5, 5)

    new_size = max(0, u["dick_size"] + change)
    conn = db()
    conn.execute(
        "UPDATE users SET dick_size=?, dick_at=?, username=? WHERE user_id=?",
        (new_size, datetime.now(timezone.utc).isoformat(), interaction.user.name, interaction.user.id),
    )
    conn.commit()
    conn.close()

    sign = f"+{change}" if change > 0 else str(change)
    action = "виріс" if change > 0 else ("зменшився" if change < 0 else "не змінився")
    await interaction.response.send_message(embed=embed(
        "🍆 Розмір пісюна",
        f"[**🍆**]({EMOJI_DICK}) **Розмір пісюна**\n\n"
        f"[📈]({EMOJI_GROWTH}) Твій пісюн **{action}** на **{sign} см**!\n"
        f"Тепер його розмір: **{new_size} см** [🍆]({EMOJI_DICK}).",
        discord.Color.green() if change >= 0 else discord.Color.red(),
    ))


# ---------------- PROFILE / MONEY ----------------

@bot.tree.command(name="profile", description="Показати профіль користувача")
@app_commands.describe(user="Користувач, профіль якого показати")
async def profile(interaction: discord.Interaction, user: discord.Member | None = None):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    target = user or interaction.user
    u = get_user(target.id, target.name)
    e = embed(f"👤 Профіль {target.display_name}")
    e.set_thumbnail(url=target.display_avatar.url)
    e.add_field(name="🍆 Розмір", value=f"**{u['dick_size']} см**", inline=True)
    e.add_field(name="💰 Баланс", value=f"**{money(u['balance'])}**", inline=True)
    e.add_field(name="🚗 Автомобіль", value=f"**{u['active_car'] or 'немає'}**", inline=False)
    e.add_field(name="🏠 Дім", value=f"**{u['primary_house'] or 'немає'}**", inline=False)
    await interaction.response.send_message(embed=e)


@bot.tree.command(name="money", description="Показати свій баланс")
async def money_cmd(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    u = get_user(interaction.user.id, interaction.user.name)
    await interaction.response.send_message(embed=embed(
        "💰 Баланс", f"{interaction.user.mention}, на твоєму балансі **{money(u['balance'])}** 💰."
    ))


@bot.tree.command(name="pay", description="Відправити гроші іншому користувачу")
@app_commands.describe(member="Кому відправити", amount="Сума")
async def pay(interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, MAX_BET]):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    if member.bot or member.id == interaction.user.id:
        await interaction.response.send_message("❌ Не можна переказати гроші собі або боту.", ephemeral=True)
        return
    sender = get_user(interaction.user.id, interaction.user.name)
    if sender["balance"] < amount:
        await interaction.response.send_message(
            f"❌ Недостатньо грошей. Баланс: **{money(sender['balance'])}** 💰.", ephemeral=True
        )
        return
    conn = db()
    conn.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (amount, interaction.user.id, amount))
    changed = conn.execute("SELECT changes() AS c").fetchone()["c"]
    if changed:
        conn.execute("INSERT OR IGNORE INTO users(user_id, username, dick_size, balance) VALUES (?, ?, ?, 0)",
                     (member.id, member.name, START_DICK_SIZE))
        conn.execute("UPDATE users SET username=?, balance=balance+? WHERE user_id=?", (member.name, amount, member.id))
    conn.commit()
    conn.close()
    if not changed:
        await interaction.response.send_message("❌ Не вдалося виконати переказ. Спробуй ще раз.", ephemeral=True)
        return
    await interaction.response.send_message(embed=embed(
        "💸 Переказ виконано",
        f"{interaction.user.mention} відправив {member.mention} **{money(amount)}** 💰."
    , discord.Color.green()))


# ---------------- DAILY ----------------

@bot.tree.command(name="daily", description="Отримати щоденний бонус")
async def daily(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    u = get_user(interaction.user.id, interaction.user.name)
    left = cooldown_left(u["daily_at"])
    if left.total_seconds() > 0:
        await interaction.response.send_message(
            f"⏳ Наступний бонус буде доступний через **{fmt_duration(left)}**.", ephemeral=True
        )
        return
    money_add(interaction.user.id, DAILY_REWARD)
    set_cooldown(interaction.user.id, "daily_at")
    await interaction.response.send_message(embed=embed(
         "🎁 Щоденний бонус",
        f"[🎁]({EMOJI_GIFT}) Ти отримав `{money(DAILY_REWARD)}` [💰]({EMOJI_MONEY})!",
        discord.Color.gold()
    ))


# ---------------- TOP / HELP ----------------

@bot.tree.command(name="top", description="Показати топ- користувачів за балансом")
async def top(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    conn = db()
    rows = conn.execute("SELECT * FROM users ORDER BY balance DESC, user_id ASC LIMIT 3").fetchall()
    conn.close()
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, row in enumerate(rows):
        member = interaction.guild.get_member(row["user_id"]) if interaction.guild else None
        name = member.display_name if member else row["username"] or f"ID {row['user_id']}"
        lines.append(f"{medals[i]} **{discord.utils.escape_markdown(name)}** — `{money(row['balance'])}` [💰](https://discord.com/assets/60e4658040396168.svg)")
    if not lines:
        lines = ["Поки що немає користувачів зі збереженим балансом."]
    await interaction.response.send_message(embed=embed("🏆 Топ-3 за балансом", "\n".join(lines), discord.Color.gold()))


@bot.tree.command(name="help", description="Список команд і пояснення")
async def help_cmd(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    e = embed("📚 Допомога", "Основні команди бота та ігри.")
    e.add_field(name="Профіль", value="`/dick` — щоденна зміна розміру.\n`/profile [user]` — профіль.\n`/money` — баланс.", inline=False)
    e.add_field(name="Економіка", value="`/daily` — бонус.\n`/pay member amount` — переказ.\n`/top` — топ-3.", inline=False)
    e.add_field(name="🎒 Інвентар та майно", value="`/inventory` — перегляд і використання предметів.\n`/case` — магазин кейсів.\n`/houses` — купівля нерухомості.\n`/market` — ринок гравців.\n`/market_sell` — виставити майно на продаж.", inline=False)
    e.add_field(name="🎮 Ігри", value="`/coinflip bet` — монетка.\n`/roulette` — рулетка.\n`/cookie user bet` — печенька.\n`/number user bet` — вгадай число 1–30.", inline=False)
    e.add_field(name="✨ Інше", value="`/masturbation` — бонус раз на 2 години.\n`/promo` — активувати промокод.\n`/role_shop` — магазин ролей.\n`/role_create` — створити роль.", inline=False)
    await interaction.response.send_message(embed=e)


# ---------------- PROMO ----------------

class PromoModal(discord.ui.Modal, title="Активація промокоду"):
    code = discord.ui.TextInput(label="Введіть промокод", placeholder="Наприклад: SVIAT67", required=True, max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        code = str(self.code.value).strip().upper()
        conn = db()
        promo = conn.execute("SELECT * FROM promos WHERE code=?", (code,)).fetchone()
        used = conn.execute("SELECT 1 FROM promo_uses WHERE code=? AND user_id=?", (code, interaction.user.id)).fetchone()
        if not promo:
            conn.close(); return await interaction.response.send_message("❌ Такого промокоду не існує.", ephemeral=True)
        if used:
            conn.close(); return await interaction.response.send_message("❌ Ти вже активував цей промокод.", ephemeral=True)
        conn.execute("INSERT INTO promo_uses(code, user_id) VALUES (?, ?)", (code, interaction.user.id))
        conn.execute("UPDATE users SET balance=balance+?, dick_size=dick_size+? WHERE user_id=?", (promo["money"], promo["dick"], interaction.user.id))
        conn.commit(); conn.close()
        await interaction.response.send_message(
            f"✅ Промокод **{code}** активовано!\n💰 +**{money(promo['money'])}**\n🍆 {promo['dick']:+d} см", ephemeral=True
        )


@bot.tree.command(name="promo", description="Активувати промокод")
async def promo(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    await interaction.response.send_modal(PromoModal())


# ---------------- COINFLIP ----------------

class CoinChoiceView(discord.ui.View):
    def __init__(self, owner_id: int, bet: int):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.bet = bet
        self.choice = None
        self.processing = False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Це не твоя ставка.", ephemeral=True)
            return False
        if self.processing:
            await interaction.response.send_message("Ставка вже обробляється.", ephemeral=True)
            return False
        return True

    def disable_buttons(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="Орел", emoji="🪙", style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.choice = "Орел"
        await self.finish(interaction)

    @discord.ui.button(label="Решка", emoji="🪙", style=discord.ButtonStyle.secondary)
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.choice = "Решка"
        await self.finish(interaction)

    async def finish(self, interaction: discord.Interaction):
        self.processing = True
        self.disable_buttons()
        # This selection message is private: only the player can see it.
        await interaction.response.edit_message(
            embed=embed("🪙 Підкинув монетку...", "⏳ Результат буде через 2 секунди..."),
            view=self,
        )
        try:
            await asyncio.sleep(2)
            # Exactly 50/50 when there is no one-shot admin override.
            # The override is atomically consumed, so only the FIRST next spin
            # by ANY user can receive it.
            forced = consume_setting("coinflip_next")
            if forced in ("Орел", "Решка"):
                result = forced
            else:
                result = random.choice(("Орел", "Решка"))

            won = result == self.choice
            if won:
                winnings = self.bet * 2
                money_add(self.owner_id, winnings)
                text = (
                    f"[🪙]({EMOJI_MONEY}) Випало: **{result}**! 🎉\n"
                    f"Ти вгадав! Отримуєш **{money(winnings)}** [💰]({EMOJI_MONEY})."
                )
                title = "🪙 Coinflip"
                color = discord.Color.green()
            else:
                text = (
                    f"🪙 Випало: **{result}**! ❌\n"
                    f"Ти програв ставку **{money(self.bet)}** [💰]({EMOJI_MONEY})."
                )
                title = "🪙 Coinflip"
                color = discord.Color.red()

            # The result is public so everyone in the channel can see it.
            await interaction.channel.send(
                embed=embed(title, text, color)
            )
        except Exception as exc:
            # Do not leave the player stuck on the waiting message if something fails.
            print(f"Coinflip error: {exc!r}")
            money_add(self.owner_id, self.bet)
            await interaction.followup.send(
                "Сталася помилка під час підкидання монетки. Ставку повернено.",
                ephemeral=True,
            )
        finally:
            self.stop()


@bot.tree.command(name="coinflip", description="Ставка на орла або решку")
@app_commands.describe(bet="Сума ставки")
async def coinflip(interaction: discord.Interaction, bet: app_commands.Range[int, MIN_COINFLIP_BET, MAX_BET]):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    u = get_user(interaction.user.id, interaction.user.name)
    if u["balance"] < bet:
        return await interaction.response.send_message(f"❌ Недостатньо грошей. Баланс: **{money(u['balance'])}**.", ephemeral=True)
    money_add(interaction.user.id, -bet)
    await interaction.response.send_message(
        embed=embed("🪙 Coinflip", f"💰 Ставка: **{money(bet)}**\n\n🦅 **Орел** або 🪙 **Решка**?"),
        view=CoinChoiceView(interaction.user.id, bet),
        ephemeral=True,
    )


# ---------------- ROULETTE ----------------

@bot.tree.command(name="roulette", description="Ставка та спроба вгадати число")
async def roulette(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    await interaction.response.send_message(
        embed=embed(
            "🎰 Рулетка",
            "Спочатку обери рівень, потім бот попросить **суму ставки**, і лише після цього — твоє число.\n\n"
            "🟢 **Легкий:** 1–3 — X3\n"
            "🔵 **Середній:** 1–5 — X5\n"
            "🔴 **Важкий:** 1–10 — X10\n"
            "🟣 **Неможливий:** 1–50 — X1000\n\n"
            "💰 Мінімальна ставка: **100**."
        ),
        view=RouletteDifficultyView()
    )


class RouletteBetModal(discord.ui.Modal, title="💰 Сума ставки"):
    bet = discord.ui.TextInput(
        label="Сума ставки",
        placeholder="Наприклад: 5000",
        required=True,
        max_length=15
    )

    def __init__(self, low: int, high: int, multiplier: int, label: str):
        super().__init__()
        self.low = low
        self.high = high
        self.multiplier = multiplier
        self.level_label = label

    async def on_submit(self, interaction: discord.Interaction):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)

        try:
            amount = int(str(self.bet.value).strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ Сума ставки має бути цілим числом.", ephemeral=True
            )

        if amount < MIN_COINFLIP_BET:
            return await interaction.response.send_message(
                f"❌ Мінімальна ставка — **{money(MIN_COINFLIP_BET)}** 💰.",
                ephemeral=True
            )
        if amount > MAX_BET:
            return await interaction.response.send_message("❌ Ставка занадто велика.", ephemeral=True)

        u = get_user(interaction.user.id, interaction.user.name)
        if u["balance"] < amount:
            return await interaction.response.send_message(
                f"❌ Недостатньо грошей. Твій баланс: **{money(u['balance'])}** 💰.",
                ephemeral=True
            )

        # Reserve the stake atomically before asking for the number.
        if not money_add(interaction.user.id, -amount):
            return await interaction.response.send_message(
                "❌ Не вдалося зарезервувати ставку. Спробуй ще раз.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            RouletteGuessModal(
                interaction.user.id,
                amount,
                self.low,
                self.high,
                self.multiplier,
                self.level_label
            )
        )


class RouletteGuessModal(discord.ui.Modal, title="🎯 Твоє число"):
    guess = discord.ui.TextInput(
        label="Обери число",
        placeholder="Введи число з діапазону",
        required=True,
        max_length=3
    )

    def __init__(self, owner_id: int, bet: int, low: int, high: int, multiplier: int, label: str):
        super().__init__()
        self.owner_id = owner_id
        self.bet_amount = bet
        self.low = low
        self.high = high
        self.multiplier = multiplier
        self.level_label = label

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            # Normally impossible because the modal is tied to the interaction,
            # but keep the check as a safety guard.
            money_add(self.owner_id, self.bet_amount)
            return await interaction.response.send_message("❌ Це не твоя ставка.", ephemeral=True)

        try:
            number = int(str(self.guess.value).strip())
        except ValueError:
            money_add(self.owner_id, self.bet_amount)
            return await interaction.response.send_message(
                "❌ Потрібно ввести ціле число. Ставку повернено.", ephemeral=True
            )

        if not self.low <= number <= self.high:
            money_add(self.owner_id, self.bet_amount)
            return await interaction.response.send_message(
                f"❌ Число має бути від **{self.low}** до **{self.high}**. Ставку повернено.",
                ephemeral=True
            )

        await interaction.response.send_message(
            embed=embed(
                "🎰 Рулетка",
                f"💰 Ставка: **{money(self.bet_amount)}**\n"
                f"🎯 Твоє число: **{number}**\n\n"
                "⏳ Бот думає над результатом..."
            ),
            ephemeral=True
        )

        await asyncio.sleep(2)

        forced = consume_setting("roulette_next")
        forced_number = None
        if forced is not None:
            try:
                candidate = int(forced)
                if self.low <= candidate <= self.high:
                    forced_number = candidate
            except ValueError:
                pass

        result = forced_number if forced_number is not None else random.randint(self.low, self.high)

        if result == number:
            winnings = self.bet_amount * self.multiplier
            money_add(self.owner_id, winnings)
            desc = (
                f"🎯 Випало число: **{result}**!\n\n"
                f"🎉 **Ти вгадав!**\n"
                f"💰 Ставка: **{money(self.bet_amount)}**\n"
                f"💵 Виплата: **{money(winnings)}**\n"
                f"📈 Коефіцієнт: **X{self.multiplier}**"
            )
            color = discord.Color.green()
        else:
            desc = (
                f"🎯 Випало число: **{result}**!\n\n"
                f"❌ **Ти не вгадав.**\n"
                f"💸 Втрачено: **{money(self.bet_amount)}**"
            )
            color = discord.Color.red()

        await interaction.edit_original_response(
            embed=embed("🎰 Результат рулетки", desc, color)
        )


class RouletteDifficultyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def choose(self, interaction: discord.Interaction, low: int, high: int, multiplier: int, label: str):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)

        u = get_user(interaction.user.id, interaction.user.name)
        if u["balance"] < MIN_COINFLIP_BET:
            return await interaction.response.send_message(
                f"❌ Для гри потрібно хоча б **{money(MIN_COINFLIP_BET)}** 💰.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            RouletteBetModal(low, high, multiplier, label)
        )

    @discord.ui.button(label="Легкий", emoji="🟢", style=discord.ButtonStyle.success)
    async def easy(self, interaction, button):
        await self.choose(interaction, 1, 3, 3, "Легкий")

    @discord.ui.button(label="Середній", emoji="🔵", style=discord.ButtonStyle.primary)
    async def medium(self, interaction, button):
        await self.choose(interaction, 1, 5, 5, "Середній")

    @discord.ui.button(label="Важкий", emoji="🔴", style=discord.ButtonStyle.danger)
    async def hard(self, interaction, button):
        await self.choose(interaction, 1, 10, 10, "Важкий")

    @discord.ui.button(label="Неможливий", emoji="🟣", style=discord.ButtonStyle.secondary)
    async def impossible(self, interaction, button):
        await self.choose(interaction, 1, 50, 1000, "Неможливий")


# ---------------- COOKIE GAME ----------------

cookie_games: dict[int, dict] = {}


def cookie_channel_id(game: dict):
    return game.get("channel_id")


async def create_cookie_channel(guild: discord.Guild, proposer: discord.Member, opponent: discord.Member, bet: int):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        proposer: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        opponent: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }
    category = None
    channel = await guild.create_text_channel("гра-в-печеньку", overwrites=overwrites, category=category, reason="Гра в печеньку")
    conn = db()
    cur = conn.execute(
        "INSERT INTO cookie_games(channel_id, proposer_id, opponent_id, bet, status) VALUES (?, ?, ?, ?, 'waiting')",
        (channel.id, proposer.id, opponent.id, bet),
    )
    game_id = cur.lastrowid
    conn.commit(); conn.close()
    game = {"id": game_id, "channel_id": channel.id, "proposer_id": proposer.id, "opponent_id": opponent.id, "bet": bet,
            "status": "waiting", "ready": set(), "scores": {proposer.id: 0, opponent.id: 0}, "task": None}
    cookie_games[channel.id] = game
    return channel, game


async def cookie_countdown(channel: discord.TextChannel, game: dict, seconds: int = 10):
    for n in range(seconds, 0, -1):
        await channel.send(f"⏳ **{n}** сек.")
        await asyncio.sleep(1)


async def start_cookie_game(game: dict):
    if game["status"] != "waiting":
        return
    game["status"] = "countdown"
    conn = db(); conn.execute("UPDATE cookie_games SET status='countdown' WHERE channel_id=?", (game["channel_id"],)); conn.commit(); conn.close()
    channel = bot.get_channel(game["channel_id"])
    if not channel:
        return
    await channel.send(embed=embed("🍪 Старт через 10 секунд", f"{channel.guild.get_member(game['proposer_id']).mention} та {channel.guild.get_member(game['opponent_id']).mention}, приготуйтеся!"))
    await cookie_countdown(channel, game, COOKIE_COUNTDOWN_SECONDS)
    if game["status"] != "countdown":
        return
    game["status"] = "playing"
    game["started_at"] = datetime.now(timezone.utc)
    conn = db(); conn.execute("UPDATE cookie_games SET status='playing', started_at=? WHERE channel_id=?", (game["started_at"].isoformat(), game["channel_id"])); conn.commit(); conn.close()
    await channel.send(embed=embed("🍪 Почали!", "Відправляй якнайбільше символів у повідомленнях за 1 хвилину.\nКожен символ = **1 очко**!", discord.Color.green()))
    for remaining in [50, 40, 30, 20, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]:
        await asyncio.sleep(10 if remaining >= 10 else 1)
        if game["status"] != "playing":
            return
        await channel.send(f"⏱️ **{remaining} сек.**")
    await asyncio.sleep(1)
    await finish_cookie_game(game)


async def finish_cookie_game(game: dict):
    if game["status"] != "playing":
        return
    game["status"] = "counting"
    channel = bot.get_channel(game["channel_id"])
    conn = db(); conn.execute("UPDATE cookie_games SET status='counting' WHERE channel_id=?", (game["channel_id"],)); conn.commit(); conn.close()
    if not channel:
        return
    await channel.send(embed=embed("🍪 Підрахунок очок", "Зараз підраховуємо результат...", discord.Color.gold()))
    await asyncio.sleep(5)
    a, b = game["proposer_id"], game["opponent_id"]
    sa, sb = game["scores"][a], game["scores"][b]
    bet = game["bet"]
    if sa > sb:
        winner, loser, sw, sl = a, b, sa, sb
        money_add(winner, bet * 2)
        result = f"🏆 Переможець: <@{winner}>\n\n🎯 Очки: **{sw}**\n👤 Суперник: **{sl}**\n📊 Йому не вистачило **{sw - sl}** очок, щоб зрівняти рахунок.\n\n💰 Переможцю виплачено **{money(bet * 2)}**."
    elif sb > sa:
        winner, loser, sw, sl = b, a, sb, sa
        money_add(winner, bet * 2)
        result = f"🏆 Переможець: <@{winner}>\n\n🎯 Очки: **{sw}**\n👤 Суперник: **{sl}**\n📊 Йому не вистачило **{sw - sl}** очок, щоб зрівняти рахунок.\n\n💰 Переможцю виплачено **{money(bet * 2)}**."
    else:
        money_add(a, bet); money_add(b, bet)
        result = f"🤝 **Нічия!**\n\n<@{a}> — **{sa}** очок\n<@{b}> — **{sb}** очок\n\n💰 Ставки повернуто обом гравцям."
    conn = db(); conn.execute("UPDATE cookie_games SET status='finished', proposer_score=?, opponent_score=?, ended_at=? WHERE channel_id=?", (sa, sb, datetime.now(timezone.utc).isoformat(), game["channel_id"])); conn.commit(); conn.close()
    await channel.send(embed=embed("🍪 Результат гри", result, discord.Color.green() if sa != sb else discord.Color.blurple()))
    await asyncio.sleep(15)
    try:
        await channel.delete(reason="Гра в печеньку завершена")
    except discord.HTTPException:
        pass
    cookie_games.pop(game["channel_id"], None)


class CookieProposalView(discord.ui.View):
    def __init__(self, proposer_id: int, opponent_id: int, bet: int):
        super().__init__(timeout=600)
        self.proposer_id = proposer_id; self.opponent_id = opponent_id; self.bet = bet; self.done = False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ Ця пропозиція призначена іншому користувачу.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Грати", emoji="🍪", style=discord.ButtonStyle.success)
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.done:
            return
        self.done = True
        opponent = get_user(self.opponent_id, interaction.user.name)
        if opponent["balance"] < self.bet:
            self.done = False
            return await interaction.response.send_message("❌ У тебе недостатньо грошей для цієї ставки.", ephemeral=True)
        money_add(self.opponent_id, -self.bet)
        proposer = interaction.guild.get_member(self.proposer_id)
        try:
            channel, game = await create_cookie_channel(interaction.guild, proposer, interaction.user, self.bet)
        except Exception:
            money_add(self.opponent_id, self.bet)
            self.done = False
            return await interaction.response.send_message("❌ Не вдалося створити приватний канал гри. Перевір права бота.", ephemeral=True)
        self.disable_all_items()
        await interaction.response.edit_message(embed=embed("🍪 Пропозицію прийнято", f"Гра створена: {channel.mention}"), view=self)
        if proposer:
            try:
                await interaction.channel.send(embed=embed("🍪 Гру прийнято", f"<@{self.proposer_id}> прийняв пропозицію. Приватний канал: {channel.mention}"))
            except discord.HTTPException:
                pass
        game["task"] = asyncio.create_task(scheduled_cookie_start(game))

    @discord.ui.button(label="Відмовитись", emoji="❌", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.done: return
        self.done = True
        self.disable_all_items()
        await interaction.response.edit_message(embed=embed("🍪 Пропозицію відхилено", f"<@{self.opponent_id}> відмовився від гри."), view=self)
        await interaction.channel.send(embed=embed("🍪 Відмова", f"<@{self.opponent_id}> відмовився грати з <@{self.proposer_id}>."))

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True


async def scheduled_cookie_start(game: dict):
    await asyncio.sleep(COOKIE_WAIT_SECONDS)
    if game["status"] == "waiting":
        await start_cookie_game(game)


@bot.tree.command(name="cookie", description="Запропонувати користувачу гру в печеньку")
@app_commands.describe(user="Користувач, якому пропонуєш гру", bet="Ставка, мінімум 1000")
async def cookie(interaction: discord.Interaction, user: discord.Member, bet: app_commands.Range[int, MIN_COOKIE_BET, MAX_BET]):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    if user.bot or user.id == interaction.user.id:
        return await interaction.response.send_message("❌ Не можна грати самому з собою або з ботом.", ephemeral=True)
    proposer = get_user(interaction.user.id, interaction.user.name)
    if proposer["balance"] < bet:
        return await interaction.response.send_message(f"❌ У тебе недостатньо грошей. Баланс: **{money(proposer['balance'])}** 💰.", ephemeral=True)
    # Reserve proposer's stake immediately. It is refunded on decline/timeout/failure.
    money_add(interaction.user.id, -bet)
    await interaction.response.send_message(embed=embed(
        "🍪 Пропозиція гри", f"Пропозиція гри в печеньку користувачу {user.mention} відправлена.\n\n💰 **Ставка: {money(bet)}**"
    ))
    proposal_msg = await interaction.channel.send(
        embed=embed("🍪 Пропозиція гри в печеньку", f"<@{interaction.user.id}> пропонує <@{user.id}> зіграти в печеньку.\n\n💰 **Ставка: {money(bet)}**"),
        view=CookieProposalView(interaction.user.id, user.id, bet)
    )
    # Refund if the proposal times out without acceptance.
    async def refund_later():
        await asyncio.sleep(600)
        view = proposal_msg.components
        # The View's done state is not accessible from message components, so this is
        # handled by a closure attribute below when we keep the object alive.
    # Keep reference and explicit timeout task.
    proposal_view = proposal_msg.components  # no-op; view is already attached
    async def proposal_timeout():
        await asyncio.sleep(600)
        # If no game contains this proposal's exact proposer/opponent/bet, refund.
        conn = db()
        exists = conn.execute("SELECT 1 FROM cookie_games WHERE proposer_id=? AND opponent_id=? AND bet=? AND status IN ('waiting','countdown','playing','counting')", (interaction.user.id, user.id, bet)).fetchone()
        conn.close()
        if not exists:
            money_add(interaction.user.id, bet)
            try:
                await interaction.channel.send(embed=embed("🍪 Час пропозиції вийшов", f"<@{user.id}> не прийняв пропозицію. Ставку **{money(bet)}** повернуто <@{interaction.user.id}>."))
            except discord.HTTPException:
                pass
    asyncio.create_task(proposal_timeout())


@bot.command(name="pecenka")
async def pecenka(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    game = cookie_games.get(message.channel.id)
    if not game or game["status"] != "waiting":
        return
    if message.author.id not in (game["proposer_id"], game["opponent_id"]):
        return
    game["ready"].add(message.author.id)
    if len(game["ready"]) == 2:
        if game.get("task") and not game["task"].done():
            game["task"].cancel()
        game["task"] = asyncio.create_task(start_cookie_game(game))
    else:
        await message.channel.send(f"🍪 <@{message.author.id}> готовий. Чекаємо другого гравця — напиши `!pecenka`.")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    game = cookie_games.get(message.channel.id)
    if game and game["status"] == "playing" and message.author.id in game["scores"]:
        game["scores"][message.author.id] += len(message.content)
        conn = db()
        conn.execute("UPDATE cookie_games SET proposer_score=?, opponent_score=? WHERE channel_id=?", (game["scores"][game['proposer_id']], game["scores"][game['opponent_id']], game["channel_id"]))
        conn.commit(); conn.close()
    await bot.process_commands(message)


# ---------------- ROLES ----------------

def role_color_to_int(value: str):
    value = value.strip().replace("#", "")
    if len(value) != 6:
        raise ValueError
    return int(value, 16)

async def role_shop_rows(guild):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM roles WHERE guild_id=? AND for_sale=1 ORDER BY price ASC",
        (guild.id,)
    ).fetchall()
    conn.close()
    return [r for r in rows if guild.get_role(r["role_id"])][:25]

async def role_shop_text(guild):
    rows = await role_shop_rows(guild)
    if not rows:
        return "Зараз у продажу немає ролей."
    return "\n".join(
        f"**{r['name']}** — **{money(r['price'])}** — продавець: <@{r['owner_id']}>"
        for r in rows
    )

class RoleBuySelect(discord.ui.Select):
    def __init__(self, rows):
        options = [
            discord.SelectOption(
                label=str(r["name"])[:100],
                description=f"Ціна: {money(r['price'])}"[:100],
                value=str(r["role_id"])
            ) for r in rows
        ]
        super().__init__(placeholder="Обери роль, яку хочеш купити", options=options)

    async def callback(self, interaction: discord.Interaction):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        await buy_role(interaction, int(self.values[0]))

class RoleShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Купити", style=discord.ButtonStyle.success, row=0)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        rows = await role_shop_rows(interaction.guild)
        if not rows:
            return await interaction.response.send_message("Зараз у продажу немає ролей.", ephemeral=True)
        await interaction.response.send_message(
            embed=embed("Купівля ролі", "Обери роль, яку хочеш купити."),
            view=RoleBuyView(rows),
            ephemeral=True
        )

    @discord.ui.button(label="Продати", style=discord.ButtonStyle.danger, row=0)
    async def sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        rows = await get_inventory_rows(interaction.guild, interaction.user.id)
        owned = await get_owned_not_inventory_rows(interaction.guild, interaction.user.id)
        all_rows = rows + owned
        # Remove duplicates while preserving order.
        seen = set()
        all_rows = [r for r in all_rows if not (r["role_id"] in seen or seen.add(r["role_id"]))]
        if not all_rows:
            return await interaction.response.send_message("У тебе немає ролей, які можна виставити на продаж.", ephemeral=True)
        await interaction.response.send_message(
            embed=embed("Продаж ролі", "Обери свою роль, яку хочеш виставити на продаж."),
            view=RoleSellView(all_rows[:25]),
            ephemeral=True
        )

    @discord.ui.button(label="Створити", style=discord.ButtonStyle.primary, row=0)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        await interaction.response.send_modal(RoleNameModal())


class RoleBuyView(discord.ui.View):
    def __init__(self, rows):
        super().__init__(timeout=180)
        if rows:
            self.add_item(RoleBuySelect(rows))

async def buy_role(interaction: discord.Interaction, role_id: int):
    if not interaction.guild:
        return await interaction.response.send_message("Тільки на сервері.", ephemeral=True)
    conn = db()
    row = conn.execute(
        "SELECT * FROM roles WHERE role_id=? AND guild_id=? AND for_sale=1",
        (role_id, interaction.guild.id)
    ).fetchone()
    conn.close()
    if not row:
        return await interaction.response.send_message("Ця роль більше не продається.", ephemeral=True)
    if row["owner_id"] == interaction.user.id:
        return await interaction.response.send_message("Не можна купити власну роль.", ephemeral=True)

    buyer = get_user(interaction.user.id, interaction.user.name)
    price, seller_id = row["price"], row["owner_id"]
    if buyer["balance"] < price:
        return await interaction.response.send_message("Недостатньо грошей.", ephemeral=True)

    role = interaction.guild.get_role(role_id)
    if not role:
        return await interaction.response.send_message("Роль більше не існує на сервері.", ephemeral=True)

    conn = db()
    conn.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?",
                 (price, interaction.user.id, price))
    changed = conn.execute("SELECT changes() AS c").fetchone()["c"]
    if not changed:
        conn.close()
        return await interaction.response.send_message("Недостатньо грошей.", ephemeral=True)

    conn.execute("INSERT OR IGNORE INTO users(user_id, username, dick_size, balance) VALUES (?, ?, ?, 0)",
                 (seller_id, str(seller_id), START_DICK_SIZE))
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (price, seller_id))
    conn.execute("UPDATE roles SET owner_id=?, for_sale=0 WHERE role_id=?", (interaction.user.id, role_id))
    conn.execute("INSERT OR IGNORE INTO role_inventory(user_id, role_id) VALUES (?, ?)", (interaction.user.id, role_id))
    conn.commit()
    conn.close()

    seller = interaction.guild.get_member(seller_id)
    if seller:
        try:
            await seller.remove_roles(role)
        except discord.HTTPException:
            pass

    await interaction.response.send_message(
        embed=embed(
            "Роль придбано",
            f"Ти придбав роль {role.mention} за **{money(price)}**.\n\nБажаєш зараз отримати її на сервері чи залишити в інвентарі?"
        ),
        view=PurchasedRoleView(role_id),
        ephemeral=True
    )

class PurchasedRoleView(discord.ui.View):
    def __init__(self, role_id):
        super().__init__(timeout=180)
        self.role_id = role_id

    @discord.ui.button(label="Інвентар", style=discord.ButtonStyle.secondary)
    async def inventory(self, interaction, button):
        await show_inventory(interaction)

    @discord.ui.button(label="Отримати роль", style=discord.ButtonStyle.success)
    async def get_role(self, interaction, button):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            return await interaction.response.send_message("Роль більше не існує.", ephemeral=True)
        try:
            await interaction.user.add_roles(role)
        except discord.HTTPException:
            return await interaction.response.send_message("Discord не дозволив видати роль.", ephemeral=True)
        conn = db()
        conn.execute("DELETE FROM role_inventory WHERE user_id=? AND role_id=?", (interaction.user.id, self.role_id))
        conn.commit(); conn.close()
        await interaction.response.send_message(f"Роль {role.mention} видано тобі.", ephemeral=True)

    @discord.ui.button(label="Продати", style=discord.ButtonStyle.danger)
    async def sell(self, interaction, button):
        await interaction.response.send_modal(RoleSellModal(self.role_id))

class RoleSellModal(discord.ui.Modal, title="Продати роль"):
    price = discord.ui.TextInput(label="Ціна", placeholder="100000", required=True)

    def __init__(self, role_id=None):
        super().__init__()
        self.role_id = role_id

    async def on_submit(self, interaction):
        try:
            price = int(str(self.price.value).strip())
            if price < 1 or price > MAX_BET:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("Невірна ціна.", ephemeral=True)

        conn = db()
        row = conn.execute("SELECT * FROM roles WHERE role_id=? AND owner_id=?",
                           (self.role_id, interaction.user.id)).fetchone()
        if not row:
            conn.close()
            return await interaction.response.send_message("Ця роль не належить тобі.", ephemeral=True)
        conn.execute("UPDATE roles SET price=?, for_sale=1 WHERE role_id=?", (price, self.role_id))
        conn.execute("DELETE FROM role_inventory WHERE user_id=? AND role_id=?", (interaction.user.id, self.role_id))
        conn.commit(); conn.close()
        await interaction.response.send_message(f"Роль виставлено на продаж за **{money(price)}**.", ephemeral=True)

class RoleSellSelect(discord.ui.Select):
    def __init__(self, rows):
        options = [
            discord.SelectOption(label=str(r["name"])[:100], value=str(r["role_id"]))
            for r in rows[:25]
        ]
        super().__init__(placeholder="Обери роль для продажу", options=options)

    async def callback(self, interaction):
        await interaction.response.send_modal(RoleSellModal(int(self.values[0])))

class RoleSellView(discord.ui.View):
    def __init__(self, rows):
        super().__init__(timeout=180)
        if rows:
            self.add_item(RoleSellSelect(rows))

class RoleNameModal(discord.ui.Modal, title="Створення ролі"):
    name = discord.ui.TextInput(label="Назва ролі", placeholder="VIP", min_length=1, max_length=100)

    async def on_submit(self, interaction):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        name = str(self.name.value).strip()
        if not name:
            return await interaction.response.send_message("Вкажи назву ролі.", ephemeral=True)
        await interaction.response.send_message(
            embed=embed("Колір ролі", "Бажаєш присвоїти ролі колір?\nЯкщо так — створення коштуватиме **200,000**."),
            view=RoleColorChoiceView(name),
            ephemeral=True
        )

class RoleColorChoiceView(discord.ui.View):
    def __init__(self, name):
        super().__init__(timeout=180)
        self.name = name

    @discord.ui.button(label="Так", style=discord.ButtonStyle.success)
    async def yes(self, interaction, button):
        await interaction.response.edit_message(
            embed=embed("Вибір кольору", "Відміть існуючу роль з кольором, який хочеш використати."),
            view=RoleColorSelectView(self.name)
        )

    @discord.ui.button(label="Ні", style=discord.ButtonStyle.secondary)
    async def no(self, interaction, button):
        await interaction.response.edit_message(
            embed=embed("Створення скасовано", "Роль не було створено."),
            view=None
        )

class RoleColorSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Обери роль з потрібним кольором", min_values=1, max_values=1)

    async def callback(self, interaction):
        role = self.values[0]
        if role.is_default() or role.managed:
            return await interaction.response.send_message("Обери звичайну роль з кольором, не системну та не інтегровану.", ephemeral=True)
        await create_custom_role(interaction, self.view.role_name, role.colour.value)

class RoleColorSelectView(discord.ui.View):
    def __init__(self, role_name):
        super().__init__(timeout=180)
        self.role_name = role_name
        self.add_item(RoleColorSelect())

async def create_custom_role(interaction, name, color_int):
    cost = ROLE_CREATE_COST
    u = get_user(interaction.user.id, interaction.user.name)
    if u["balance"] < cost:
        return await interaction.response.send_message(
            f"Недостатньо грошей. Потрібно **{money(cost)}**.", ephemeral=True
        )
    try:
        role = await interaction.guild.create_role(
            name=name,
            colour=discord.Colour(color_int),
            reason=f"Custom role created by {interaction.user}"
        )
    except discord.HTTPException:
        return await interaction.response.send_message("Не вдалося створити або видати роль.", ephemeral=True)

    money_add(interaction.user.id, -cost)
    conn = db()
    conn.execute(
        "INSERT INTO roles(role_id, guild_id, owner_id, name, color, price, for_sale) VALUES (?, ?, ?, ?, ?, 0, 0)",
        (role.id, interaction.guild.id, interaction.user.id, name, color_int)
    )
    conn.execute("INSERT OR IGNORE INTO role_inventory(user_id, role_id) VALUES (?, ?)", (interaction.user.id, role.id))
    conn.commit(); conn.close()
    await interaction.response.edit_message(
        embed=embed("Роль створено", f"Роль {role.mention} створено та додано до твого інвентарю.\nВартість: **{money(cost)}**."),
        view=None
    )

async def get_inventory_rows(guild: discord.Guild, user_id: int):
    conn = db()
    rows = conn.execute("""
        SELECT r.* FROM roles r
        JOIN role_inventory i ON i.role_id=r.role_id
        WHERE i.user_id=? AND r.guild_id=?
        ORDER BY i.added_at DESC
    """, (user_id, guild.id)).fetchall()
    conn.close()
    return [r for r in rows if guild.get_role(r["role_id"])]


async def get_owned_not_inventory_rows(guild: discord.Guild, user_id: int):
    conn = db()
    rows = conn.execute("""
        SELECT r.* FROM roles r
        WHERE r.guild_id=? AND r.owner_id=?
          AND NOT EXISTS (
              SELECT 1 FROM role_inventory i
              WHERE i.role_id=r.role_id AND i.user_id=?
          )
        ORDER BY r.name
    """, (guild.id, user_id, user_id)).fetchall()
    conn.close()
    return [r for r in rows if guild.get_role(r["role_id"])]


async def show_inventory(interaction):
    rows = await get_inventory_rows(interaction.guild, interaction.user.id)
    if not rows:
        description = "Інвентар порожній."
    else:
        description = "\n".join(
            f"**{r['name']}** — **{money(r['price']) if r['price'] else 'не продається'}**"
            for r in rows[:25]
        )
    await interaction.response.send_message(
        embed=embed("Інвентар ролей", description),
        view=InventoryView([r["role_id"] for r in rows[:25]]),
        ephemeral=True
    )


class InventorySelect(discord.ui.Select):
    def __init__(self, role_ids, action):
        self.action = action
        super().__init__(
            placeholder="Обери роль",
            options=[discord.SelectOption(label=str(rid), value=str(rid)) for rid in role_ids[:25]]
        )

    async def callback(self, interaction):
        rid = int(self.values[0])
        if self.action == "get":
            role = interaction.guild.get_role(rid)
            if not role:
                return await interaction.response.send_message("Роль більше не існує.", ephemeral=True)
            try:
                await interaction.user.add_roles(role, reason="Отримання ролі з інвентарю")
            except discord.HTTPException:
                return await interaction.response.send_message("Не вдалося видати роль.", ephemeral=True)
            conn = db()
            conn.execute("DELETE FROM role_inventory WHERE user_id=? AND role_id=?", (interaction.user.id, rid))
            conn.commit(); conn.close()
            return await interaction.response.send_message(f"Роль {role.mention} видано.", ephemeral=True)
        if self.action == "sell":
            return await interaction.response.send_modal(RoleSellModal(rid))
        if self.action == "remove":
            conn = db()
            conn.execute("DELETE FROM role_inventory WHERE user_id=? AND role_id=?", (interaction.user.id, rid))
            conn.commit(); conn.close()
            return await interaction.response.send_message("Роль прибрано з інвентарю. Її можна буде знову додати через кнопку додавання.", ephemeral=True)


class InventoryAddSelect(discord.ui.Select):
    def __init__(self, rows):
        super().__init__(
            placeholder="Обери власну роль для інвентарю",
            options=[
                discord.SelectOption(label=str(r["name"])[:100], description="Додати до інвентарю", value=str(r["role_id"]))
                for r in rows[:25]
            ]
        )

    async def callback(self, interaction):
        rid = int(self.values[0])
        conn = db()
        row = conn.execute("SELECT * FROM roles WHERE role_id=? AND guild_id=? AND owner_id=?", (rid, interaction.guild.id, interaction.user.id)).fetchone()
        if not row:
            conn.close()
            return await interaction.response.send_message("Ця роль більше не належить тобі.", ephemeral=True)
        conn.execute("INSERT OR IGNORE INTO role_inventory(user_id, role_id) VALUES (?, ?)", (interaction.user.id, rid))
        conn.commit(); conn.close()
        role = interaction.guild.get_role(rid)
        await interaction.response.send_message(f"Роль {role.mention if role else row['name']} додано до інвентарю.", ephemeral=True)


class InventoryAddView(discord.ui.View):
    def __init__(self, rows):
        super().__init__(timeout=180)
        self.add_item(InventoryAddSelect(rows))


class InventoryView(discord.ui.View):
    def __init__(self, role_ids):
        super().__init__(timeout=180)
        if role_ids:
            self.add_item(InventorySelect(role_ids, "get"))
            self.add_item(InventorySelect(role_ids, "sell"))

    @discord.ui.button(label="Додати роль", style=discord.ButtonStyle.primary, row=2)
    async def add_role(self, interaction, button):
        rows = await get_owned_not_inventory_rows(interaction.guild, interaction.user.id)
        if not rows:
            return await interaction.response.send_message("Немає власних ролей, які можна додати до інвентарю.", ephemeral=True)
        await interaction.response.send_message(
            embed=embed("Додати роль в інвентар", "Обери свою роль, яку хочеш зберігати в інвентарі."),
            view=InventoryAddView(rows),
            ephemeral=True
        )


@bot.tree.command(name="role_shop", description="Переглянути магазин ролей")
async def role_shop(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if not interaction.guild: return await interaction.response.send_message("Тільки на сервері.", ephemeral=True)
    await interaction.response.send_message(embed=embed("Магазин ролей", await role_shop_text(interaction.guild)), view=RoleShopView())

@bot.tree.command(name="role_create", description="Створити власну роль")
async def role_create(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if not interaction.guild: return await interaction.response.send_message("Тільки на сервері.", ephemeral=True)
    await interaction.response.send_modal(RoleNameModal())

@bot.tree.command(name="role_sell", description="Виставити свою роль на продаж")
@app_commands.describe(role="Роль", price="Ціна")
async def role_sell(interaction: discord.Interaction, role: discord.Role, price: app_commands.Range[int, 1, MAX_BET]):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    conn = db(); row = conn.execute("SELECT * FROM roles WHERE role_id=? AND guild_id=? AND owner_id=?", (role.id, interaction.guild.id, interaction.user.id)).fetchone()
    if not row:
        conn.close(); return await interaction.response.send_message("Це не твоя роль, створена через бота.", ephemeral=True)
    conn.execute("UPDATE roles SET price=?, for_sale=1 WHERE role_id=?", (price, role.id)); conn.execute("DELETE FROM role_inventory WHERE user_id=? AND role_id=?", (interaction.user.id, role.id)); conn.commit(); conn.close()
    await interaction.response.send_message(f"Роль {role.mention} виставлена на продаж за **{money(price)}**.", ephemeral=True)

@bot.tree.command(name="role_buy", description="Купити роль")
@app_commands.describe(role="Роль")
async def role_buy(interaction: discord.Interaction, role: discord.Role):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    await buy_role(interaction, role.id)


# ---------------- CASES ----------------

@bot.tree.command(name="case", description="Відкрити магазин кейсів")
async def case(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    await interaction.response.send_message(
        embed=embed(
            "🎁 Магазин кейсів",
            "Обери кейс, який хочеш придбати. Після покупки його можна відкрити одразу або зберегти в /inventory.",
            discord.Color.gold()
        ),
        view=CaseMainView()
    )

class CaseMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    async def choose(self, interaction: discord.Interaction, rarity: str):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        data = CASE_DATA[rarity]
        u = get_user(interaction.user.id, interaction.user.name)
        if u["balance"] < data["price"]:
            return await interaction.response.send_message(
                f"❌ Недостатньо грошей. Потрібно **{money(data['price'])}** 💰.\n"
                f"Твій баланс: **{money(u['balance'])}** 💰.",
                ephemeral=True
            )
        await interaction.response.send_message(
            embed=embed(
                f"{data['emoji']} {rarity} кейс",
                f"Ціна одного кейса: **{money(data['price'])}** 💰\n\n"
                "Обери, скільки кейсів хочеш придбати:",
                discord.Color.gold()
            ),
            view=CaseQuantityView(rarity),
            ephemeral=True
        )

    @discord.ui.button(label="Звичайний | 5 тис.", emoji="🟢", style=discord.ButtonStyle.success, row=0)
    async def common(self, interaction, button): await self.choose(interaction, "Звичайний")

    @discord.ui.button(label="Рідкий | 10 тис.", emoji="🔵", style=discord.ButtonStyle.primary, row=0)
    async def rare(self, interaction, button): await self.choose(interaction, "Рідкий")

    @discord.ui.button(label="Епічний | 20 тис.", emoji="🟣", style=discord.ButtonStyle.primary, row=0)
    async def epic(self, interaction, button): await self.choose(interaction, "Епічний")

    @discord.ui.button(label="Міфічний | 50 тис.", emoji="🟠", style=discord.ButtonStyle.danger, row=0)
    async def mythic(self, interaction, button): await self.choose(interaction, "Міфічний")

    @discord.ui.button(label="Легендарний | 100 тис.", emoji="🟡", style=discord.ButtonStyle.secondary, row=0)
    async def legendary(self, interaction, button): await self.choose(interaction, "Легендарний")

    @discord.ui.button(label="Шанси", emoji="🎲", style=discord.ButtonStyle.secondary, row=1)
    async def chances(self, interaction, button):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        await send_case_chances(interaction)


class CaseQuantityView(discord.ui.View):
    def __init__(self, rarity: str):
        super().__init__(timeout=180)
        self.rarity = rarity
        for n in range(1, 11):
            button = discord.ui.Button(
                label=str(n),
                emoji=("🔟" if n == 10 else f"{n}\ufe0f\u20e3"),
                style=discord.ButtonStyle.primary,
                row=(n - 1) // 5
            )
            button.callback = self.make_callback(n)
            self.add_item(button)

    def make_callback(self, quantity: int):
        async def callback(interaction: discord.Interaction):
            data = CASE_DATA[self.rarity]
            total = data["price"] * quantity
            u = get_user(interaction.user.id, interaction.user.name)
            if u["balance"] < total:
                return await interaction.response.send_message(
                    f"❌ Недостатньо грошей для **{quantity}** шт.\n"
                    f"Потрібно: **{money(total)}** 💰\n"
                    f"Твій баланс: **{money(u['balance'])}** 💰.",
                    ephemeral=True
                )
            if not money_add(interaction.user.id, -total):
                return await interaction.response.send_message(
                    "❌ Не вдалося списати гроші. Спробуй ще раз.", ephemeral=True
                )

            await interaction.response.send_message(
                embed=embed(
                    "✅ Кейс успішно придбано",
                    f"{data['emoji']} Ви успішно придбали кейс рідкості **{self.rarity}**.\n\n"
                    f"📦 Кількість: **{quantity} шт.**\n"
                    f"💰 Витрачено: **{money(total)}**\n\n"
                    "Можеш **відкрити їх зараз** або **закинути в інвентар**, щоб відкрити пізніше.",
                    discord.Color.green()
                ),
                view=CasePurchaseView(self.rarity, quantity, interaction.user.id)
            )
        return callback


class CasePurchaseView(discord.ui.View):
    def __init__(self, rarity: str, quantity: int, owner_id: int):
        super().__init__(timeout=300)
        self.rarity = rarity
        self.quantity = quantity
        self.owner_id = owner_id
        self.used = False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Ці кнопки призначені користувачу, який придбав кейси.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Відкрити зараз", emoji="🎁", style=discord.ButtonStyle.success)
    async def open_now(self, interaction: discord.Interaction, button):
        if self.used:
            return await interaction.response.send_message("❌ Ця покупка вже оброблена.", ephemeral=True)
        self.used = True
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)
        await open_cases_and_send(interaction, self.rarity, self.quantity)

    @discord.ui.button(label="В інвентар", emoji="🎒", style=discord.ButtonStyle.primary)
    async def to_inventory(self, interaction: discord.Interaction, button):
        if self.used:
            return await interaction.response.send_message("❌ Ця покупка вже оброблена.", ephemeral=True)
        self.used = True
        for item in self.children:
            item.disabled = True
        add_case_inventory(interaction.user.id, self.rarity, self.quantity)
        await interaction.response.edit_message(
            embed=embed(
                "🎒 Кейси додано в інвентар",
                f"{CASE_DATA[self.rarity]['emoji']} **{self.rarity}** — **{self.quantity} шт.**\n\n"
                "Тепер їх можна відкрити пізніше через інвентар.",
                discord.Color.blurple()
            ),
            view=self
        )


async def send_case_chances(interaction: discord.Interaction):
    # One embed per rarity keeps the complete 17-item list within Discord limits.
    first = True
    for rarity, data in CASE_DATA.items():
        lines = []
        for i, (name, value, jackpot, chance) in enumerate(case_chances(rarity), 1):
            marker = " 🎰 **ДЖЕКПОТ**" if jackpot else ""
            lines.append(f"`{i:02}` • **{name}** — {money(value)} 💰 — **{chance:.2f}%**{marker}")
        e = embed(
            f"{data['emoji']} Шанси — {rarity}",
            "\n".join(lines),
            discord.Color.gold()
        )
        if first:
            await interaction.response.send_message(embed=e, ephemeral=True)
            first = False
        else:
            await interaction.followup.send(embed=e, ephemeral=True)


class CarResultView(discord.ui.View):
    def __init__(self, owner_id: int, car_name: str, car_value: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.car_name = car_name
        self.car_value = car_value
        self.done = False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Ці кнопки доступні лише тому, хто відкрив кейс.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Забрати", emoji="🚗", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button):
        if self.done:
            return await interaction.response.send_message("❌ Цю машину вже оброблено.", ephemeral=True)
        self.done = True
        add_inventory_item(interaction.user.id, "car", self.car_name, 1)
        conn=db()
        row=conn.execute("SELECT active_car FROM users WHERE user_id=?",(interaction.user.id,)).fetchone()
        if not row["active_car"]:
            conn.execute("UPDATE users SET active_car=? WHERE user_id=?",(self.car_name,interaction.user.id))
        conn.commit(); conn.close()
        for item in self.children: item.disabled=True
        await interaction.response.edit_message(
            embed=embed("🚗 Машину забрано", f"**{self.car_name}** додано до твого інвентарю.\n\nПеревір `/inventory` або профіль.", discord.Color.green()),
            view=self
        )

    @discord.ui.button(label="Продати", emoji="💰", style=discord.ButtonStyle.danger)
    async def sell(self, interaction: discord.Interaction, button):
        if self.done:
            return await interaction.response.send_message("❌ Цю машину вже оброблено.", ephemeral=True)
        self.done = True
        money_add(interaction.user.id, self.car_value)
        for item in self.children: item.disabled=True
        await interaction.response.edit_message(
            embed=embed("💰 Машину продано", f"**{self.car_name}** продано державі за **{money(self.car_value)}** 💰.", discord.Color.gold()),
            view=self
        )

async def open_cases_and_send(interaction: discord.Interaction, rarity: str, quantity: int):
    data = CASE_DATA[rarity]
    results = [roll_case(rarity) for _ in range(quantity)]
    for name, value, jackpot, chance in results:
        title = "🎰 ДЖЕКПОТ!" if jackpot else "🎁 Кейс відкрито"
        text = f"{data['emoji']} Рідкість кейса: **{rarity}**\n\n🚗 Ви отримали: **{name}**\n💰 Вартість машини: **{money(value)}**"
        if jackpot:
            text += "\n\n🎰 **ЦЕ ДЖЕКПОТ! Вітаємо!**"
        await interaction.followup.send(
            embed=embed(title, text, discord.Color.gold() if jackpot else discord.Color.blurple()),
            view=CarResultView(interaction.user.id, name, value),
            ephemeral=True
        )


class InventoryUseView(discord.ui.View):
    """Interactive inventory: select an item and use it.

    Cases are consumed and opened immediately. Cars/houses are equipped as the
    active profile property. All mutations are persisted in SQLite.
    """
    def __init__(self, user_id: int, rows):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.rows = rows
        options = []
        for idx, r in enumerate(rows[:25]):
            item_type = r["item_type"]
            if item_type == "case":
                emoji = CASE_DATA.get(r["item_key"], {}).get("emoji", "🎁")
                label = f"{emoji} Кейс: {r['item_key']}"
                description = f"Кількість: {r['quantity']} • відкривається"
            elif item_type == "car":
                label = f"🚗 {r['item_key']}"
                description = f"Кількість: {r['quantity']} • зробити активним"
            elif item_type == "house":
                label = f"🏠 {r['item_key']}"
                description = f"Кількість: {r['quantity']} • зробити основним"
            else:
                label = f"📦 {r['item_key']}"
                description = f"Кількість: {r['quantity']}"
            options.append(discord.SelectOption(
                label=label[:100], description=description[:100], value=str(idx)
            ))

        if options:
            select = discord.ui.Select(
                placeholder="Обери предмет, який хочеш використати",
                options=options,
                custom_id=f"inventory_use_{user_id}"
            )
            select.callback = self.use_selected
            self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Це меню інвентарю належить іншому користувачу.", ephemeral=True
            )
            return False
        return True

    async def use_selected(self, interaction: discord.Interaction):
        select = self.children[0]
        index = int(select.values[0])
        if index >= len(self.rows):
            return await interaction.response.send_message(
                "❌ Цей предмет більше недоступний. Відкрий `/inventory` ще раз.", ephemeral=True
            )

        row = self.rows[index]
        item_type = row["item_type"]
        item_key = row["item_key"]

        # Re-check the database at click time to prevent stale menus and
        # double-spending an item after another interaction.
        fresh = find_inventory_item(self.user_id, item_type, item_key)
        if not fresh:
            return await interaction.response.send_message(
                "❌ Цього предмета вже немає в інвентарі. Онови `/inventory`.", ephemeral=True
            )

        if item_type == "case":
            if item_key not in CASE_DATA:
                return await interaction.response.send_message(
                    "❌ Невідомий тип кейса. Звернися до адміністратора.", ephemeral=True
                )
            if not remove_inventory_item(self.user_id, "case", item_key, 1):
                return await interaction.response.send_message(
                    "❌ Не вдалося використати кейс. Спробуй ще раз.", ephemeral=True
                )

            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(
                embed=embed(
                    "🎁 Відкриваємо кейс",
                    f"{CASE_DATA[item_key]['emoji']} **{item_key}** використано з інвентарю.\n\n"
                    "Зараз визначимо твою машину...",
                    discord.Color.gold()
                ),
                view=self
            )
            name, value, jackpot, chance = roll_case(item_key)
            title = "🎰 ДЖЕКПОТ!" if jackpot else "🎁 Кейс відкрито"
            text = (
                f"{CASE_DATA[item_key]['emoji']} Рідкість кейса: **{item_key}**\n\n"
                f"🚗 Ви отримали: **{name}**\n"
                f"💰 Вартість машини: **{money(value)}**"
            )
            if jackpot:
                text += "\n\n🎰 **ЦЕ ДЖЕКПОТ! Вітаємо!**"
            await interaction.followup.send(
                embed=embed(title, text, discord.Color.gold() if jackpot else discord.Color.blurple()),
                view=CarResultView(self.user_id, name, value),
                ephemeral=True
            )
            return

        if item_type == "car":
            conn = db()
            conn.execute("UPDATE users SET active_car=? WHERE user_id=?", (item_key, self.user_id))
            conn.commit(); conn.close()
            await interaction.response.send_message(
                embed=embed(
                    "🚗 Автомобіль використано",
                    f"Тепер твій активний автомобіль: **{item_key}**.\n\n"
                    "Це також відображатиметься у `/profile`.",
                    discord.Color.green()
                ), ephemeral=True
            )
            return

        if item_type == "house":
            conn = db()
            conn.execute("UPDATE users SET primary_house=? WHERE user_id=?", (item_key, self.user_id))
            conn.commit(); conn.close()
            await interaction.response.send_message(
                embed=embed(
                    "🏠 Нерухомість використано",
                    f"Тепер твій основний дім: **{item_key}**.\n\n"
                    "Це також відображатиметься у `/profile`.",
                    discord.Color.green()
                ), ephemeral=True
            )
            return

        await interaction.response.send_message(
            "ℹ️ Для цього предмета поки немає дії використання.", ephemeral=True
        )


@bot.tree.command(name="inventory", description="Переглянути та використовувати предмети інвентарю")
async def inventory(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    rows = get_inventory_items(interaction.user.id)
    role_rows = await get_inventory_rows(interaction.guild, interaction.user.id) if interaction.guild else []
    parts = []
    for r in rows:
        if r["item_type"] == "case":
            label = f"{CASE_DATA.get(r['item_key'], {'emoji':'🎁'})['emoji']} Кейси: **{r['item_key']}** — {r['quantity']} шт. • 🎁 можна відкрити"
        elif r["item_type"] == "car":
            label = f"🚗 **{r['item_key']}** — {r['quantity']} шт. • ⚙️ можна використати"
        elif r["item_type"] == "house":
            label = f"🏠 **{r['item_key']}** — {r['quantity']} шт. • ⚙️ можна використати"
        else:
            label = f"📦 **{r['item_key']}** — {r['quantity']} шт."
        parts.append(label)
    if role_rows:
        parts.append("🏷️ Ролі: " + ", ".join(f"**{r['name']}**" for r in role_rows))
    description = "\n".join(parts) if parts else "Твій інвентар порожній."
    description += "\n\n👇 **Обери предмет нижче, щоб використати його.**" if rows else ""
    await interaction.response.send_message(
        embed=embed("🎒 Інвентар", description, discord.Color.blurple()),
        view=InventoryUseView(interaction.user.id, rows) if rows else None,
        ephemeral=True
    )

# ---------------- HOUSES ----------------
class HouseShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        options = [discord.SelectOption(label=name[:100], description=f"{money(price)} 💰", value=name)
                   for name, price in HOUSES[:25]]
        select = discord.ui.Select(placeholder="Обери нерухомість для купівлі", options=options)
        select.callback = self.buy_house
        self.add_item(select)

    async def buy_house(self, interaction: discord.Interaction):
        name = self.children[0].values[0]
        price = HOUSES_BY_NAME[name]
        u = get_user(interaction.user.id, interaction.user.name)
        if u["balance"] < price:
            return await interaction.response.send_message(f"❌ Недостатньо грошей. Потрібно **{money(price)}** 💰.", ephemeral=True)
        if not money_add(interaction.user.id, -price):
            return await interaction.response.send_message("❌ Не вдалося списати гроші.", ephemeral=True)
        add_inventory_item(interaction.user.id, "house", name, 1)
        conn=db()
        row=conn.execute("SELECT primary_house FROM users WHERE user_id=?",(interaction.user.id,)).fetchone()
        if not row["primary_house"]:
            conn.execute("UPDATE users SET primary_house=? WHERE user_id=?",(name,interaction.user.id))
        conn.commit(); conn.close()
        await interaction.response.send_message(embed=embed("🏠 Нерухомість придбано", f"Ти придбав **{name}** за **{money(price)}** 💰.\n\nОб'єкт збережено в `/inventory`.", discord.Color.green()), ephemeral=True)

@bot.tree.command(name="houses", description="Купити квартиру, будинок або віллу у держави")
async def houses(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    lines = [f"**{i}. {name}** — {money(price)} 💰" for i,(name,price) in enumerate(HOUSES,1)]
    await interaction.response.send_message(embed=embed("🏠 Державна нерухомість", "\n".join(lines), discord.Color.green()), view=HouseShopView())

# ---------------- MARKET ----------------
def find_inventory_item(user_id: int, item_type: str, item_key: str):
    conn=db()
    row=conn.execute("SELECT * FROM inventory_items WHERE user_id=? AND item_type=? AND item_key=? AND quantity>0",
                     (user_id,item_type,item_key)).fetchone()
    conn.close(); return row

class MarketView(discord.ui.View):
    def __init__(self, listings):
        super().__init__(timeout=300)
        options=[]
        for r in listings[:25]:
            seller=f"<@{r['seller_id']}>"
            options.append(discord.SelectOption(
                label=f"{r['item_key']}"[:100],
                description=f"{money(r['price'])} 💰 • {r['item_type']} • {seller}"[:100],
                value=str(r["listing_id"])
            ))
        if options:
            select=discord.ui.Select(placeholder="Обери оголошення для купівлі", options=options)
            select.callback=self.buy_listing
            self.add_item(select)

    async def buy_listing(self, interaction: discord.Interaction):
        listing_id=int(self.children[0].values[0])
        conn=db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            listing=conn.execute("SELECT * FROM market_listings WHERE listing_id=? AND status='active'",(listing_id,)).fetchone()
            if not listing:
                conn.rollback()
                return await interaction.response.send_message("❌ Це оголошення вже недоступне.", ephemeral=True)
            if listing["seller_id"] == interaction.user.id:
                conn.rollback()
                return await interaction.response.send_message("❌ Не можна купити власне оголошення.", ephemeral=True)
            buyer=conn.execute("SELECT balance FROM users WHERE user_id=?",(interaction.user.id,)).fetchone()
            if not buyer or buyer["balance"] < listing["price"]:
                conn.rollback()
                return await interaction.response.send_message("❌ Недостатньо грошей.", ephemeral=True)
            conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?",(listing["price"],interaction.user.id))
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(listing["price"],listing["seller_id"]))
            conn.execute("""INSERT INTO inventory_items(user_id,item_type,item_key,quantity) VALUES(?,?,?,1)
                            ON CONFLICT(user_id,item_type,item_key) DO UPDATE SET quantity=quantity+1""",
                         (interaction.user.id,listing["item_type"],listing["item_key"]))
            conn.execute("UPDATE market_listings SET status='sold', sold_at=? WHERE listing_id=?",
                         (datetime.now(timezone.utc).isoformat(),listing_id))
            if listing["item_type"]=="car":
                row=conn.execute("SELECT active_car FROM users WHERE user_id=?",(interaction.user.id,)).fetchone()
                if not row["active_car"]:
                    conn.execute("UPDATE users SET active_car=? WHERE user_id=?",(listing["item_key"],interaction.user.id))
            elif listing["item_type"]=="house":
                row=conn.execute("SELECT primary_house FROM users WHERE user_id=?",(interaction.user.id,)).fetchone()
                if not row["primary_house"]:
                    conn.execute("UPDATE users SET primary_house=? WHERE user_id=?",(listing["item_key"],interaction.user.id))
            conn.commit()
        except Exception:
            conn.rollback(); raise
        finally: conn.close()
        await interaction.response.send_message(embed=embed("🛒 Покупку завершено",
            f"Ти придбав **{listing['item_key']}** у <@{listing['seller_id']}> за **{money(listing['price'])}** 💰.",
            discord.Color.green()), ephemeral=True)

@bot.tree.command(name="market", description="Ринок гравців: купівля та перегляд оголошень")
async def market(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    conn=db()
    listings=conn.execute("""SELECT * FROM market_listings WHERE status='active' ORDER BY created_at DESC LIMIT 25""").fetchall()
    conn.close()
    if not listings:
        text="Зараз на ринку немає активних оголошень.\n\nВиставити майно можна командою `/market_sell`."
    else:
        text="\n".join(f"**#{r['listing_id']}** • {r['item_key']} • {money(r['price'])} 💰 • продавець <@{r['seller_id']}>" for r in listings)
    await interaction.response.send_message(embed=embed("🏪 Ринок гравців",text,discord.Color.gold()), view=MarketView(listings) if listings else None)

@bot.tree.command(name="market_sell", description="Виставити свою машину або нерухомість на ринок")
@app_commands.describe(item_type="Тип майна", item_name="Точна назва з інвентарю", price="Ціна продажу")
@app_commands.choices(item_type=[
    app_commands.Choice(name="Автомобіль", value="car"),
    app_commands.Choice(name="Нерухомість", value="house"),
])
async def market_sell(interaction: discord.Interaction, item_type: app_commands.Choice[str], item_name: str,
                      price: app_commands.Range[int,1,MAX_BET]):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    item_type_value=item_type.value
    if item_type_value=="house" and item_name not in HOUSES_BY_NAME:
        return await interaction.response.send_message("❌ Такого об'єкта нерухомості не існує.", ephemeral=True)
    row=find_inventory_item(interaction.user.id,item_type_value,item_name)
    if not row:
        return await interaction.response.send_message("❌ Цього майна немає у твоєму `/inventory`.", ephemeral=True)
    if not remove_inventory_item(interaction.user.id,item_type_value,item_name,1):
        return await interaction.response.send_message("❌ Не вдалося зарезервувати майно.", ephemeral=True)
    conn=db()
    conn.execute("INSERT INTO market_listings(seller_id,item_type,item_key,price) VALUES(?,?,?,?)",
                 (interaction.user.id,item_type_value,item_name,price))
    # If the listed asset was the profile's active one, clear the profile field.
    if item_type_value=="car":
        conn.execute("UPDATE users SET active_car=NULL WHERE user_id=? AND active_car=?",(interaction.user.id,item_name))
    else:
        conn.execute("UPDATE users SET primary_house=NULL WHERE user_id=? AND primary_house=?",(interaction.user.id,item_name))
    conn.commit(); conn.close()
    await interaction.response.send_message(embed=embed("🏷️ Оголошення створено",
        f"**{item_name}** виставлено на ринок за **{money(price)}** 💰.\n\nПокупці побачать його через `/market`.",discord.Color.blurple()),ephemeral=True)
# ---------------- NUMBER DUEL ----------------
NUMBER_MIN = 1
NUMBER_MAX = 30
NUMBER_DELETE_AFTER = 60
number_games: dict[int, dict] = {}

async def create_number_channel(guild: discord.Guild, proposer: discord.Member, opponent: discord.Member, bet: int):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        proposer: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        opponent: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }
    category = discord.utils.get(guild.categories, name="Ігри")
    channel = await guild.create_text_channel("вгадай-число-суперника", overwrites=overwrites, category=category, reason="Гра вгадай число")
    conn = db()
    cur = conn.execute("INSERT INTO number_games(channel_id,proposer_id,opponent_id,bet) VALUES(?,?,?,?)", (channel.id, proposer.id, opponent.id, bet))
    game_id = cur.lastrowid
    conn.commit(); conn.close()
    game = {"game_id": game_id, "channel_id": channel.id, "proposer_id": proposer.id, "opponent_id": opponent.id, "bet": bet,
            "proposer_number": None, "opponent_number": None, "current_guesser_id": None, "status": "choosing"}
    number_games[channel.id] = game
    return channel, game

class NumberChallengeView(discord.ui.View):
    def __init__(self, proposer_id: int, opponent_id: int, bet: int):
        super().__init__(timeout=120)
        self.proposer_id, self.opponent_id, self.bet = proposer_id, opponent_id, bet

    async def interaction_check(self, interaction):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ Ця пропозиція призначена іншому гравцю.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Прийняти", style=discord.ButtonStyle.success)
    async def accept(self, interaction, button):
        opponent = get_user(interaction.user.id, interaction.user.name)
        proposer = get_user(self.proposer_id)
        if opponent["balance"] < self.bet:
            return await interaction.response.send_message(f"❌ У тебе недостатньо грошей для ставки **{money(self.bet)}**.", ephemeral=True)
        if proposer["balance"] < self.bet:
            return await interaction.response.send_message("❌ У суперника вже недостатньо грошей. Пропозицію скасовано.", ephemeral=True)
        # Re-check both balances atomically, then reserve both stakes.
        conn = db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            p = conn.execute("SELECT balance FROM users WHERE user_id=?", (self.proposer_id,)).fetchone()
            o = conn.execute("SELECT balance FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()
            if not p or not o or p["balance"] < self.bet or o["balance"] < self.bet:
                conn.rollback()
                return await interaction.response.send_message("❌ Не вистачає коштів для ставки.", ephemeral=True)
            conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (self.bet, self.proposer_id))
            conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (self.bet, interaction.user.id))
            conn.commit()
        finally:
            conn.close()
        proposer_member = interaction.guild.get_member(self.proposer_id)
        if not proposer_member:
            money_add(self.proposer_id, self.bet)
            money_add(interaction.user.id, self.bet)
            return await interaction.response.send_message("❌ Не вдалося знайти суперника на сервері.", ephemeral=True)
        try:
            channel, game = await create_number_channel(interaction.guild, proposer_member, interaction.user, self.bet)
        except Exception:
            money_add(self.proposer_id, self.bet); money_add(interaction.user.id, self.bet)
            raise
        await interaction.response.edit_message(embed=embed("🎯 Гру прийнято", f"Канал гри: {channel.mention}\nСтавка: **{money(self.bet)}** 💰", discord.Color.green()), view=None)
        await channel.send(embed=embed("🎯 Вгадай число суперника", f"{proposer_member.mention} та {interaction.user.mention}, оберіть **таємне число від 1 до 30**.\n\nЧисло бачите тільки ви — бот покаже підтвердження приватно.", discord.Color.blurple()), view=NumberSecretView(channel.id, self.proposer_id, self.opponent_id))

    @discord.ui.button(label="Відхилити", style=discord.ButtonStyle.danger)
    async def decline(self, interaction, button):
        await interaction.response.edit_message(embed=embed("❌ Пропозицію відхилено", "Гру не створено."), view=None)

class NumberSecretView(discord.ui.View):
    def __init__(self, channel_id: int, proposer_id: int, opponent_id: int):
        super().__init__(timeout=900)
        self.channel_id, self.proposer_id, self.opponent_id, self.page = channel_id, proposer_id, opponent_id, 0
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        start = self.page * 10 + 1
        for n in range(start, start + 10):
            button = discord.ui.Button(label=str(n), style=discord.ButtonStyle.primary, row=0 if n <= start + 4 else 1)
            button.callback = self.make_number_callback(n)
            self.add_item(button)
        if self.page > 0:
            button = discord.ui.Button(label="◀️", style=discord.ButtonStyle.secondary, row=2)
            button.callback = self.prev
            self.add_item(button)
        if self.page < 2:
            button = discord.ui.Button(label="▶️", style=discord.ButtonStyle.secondary, row=2)
            button.callback = self.next
            self.add_item(button)

    async def interaction_check(self, interaction):
        if interaction.user.id not in (self.proposer_id, self.opponent_id):
            await interaction.response.send_message("❌ Ти не береш участі в цій грі.", ephemeral=True)
            return False
        return True

    async def prev(self, interaction):
        self.page = max(0, self.page - 1); self.rebuild()
        await interaction.response.edit_message(view=self)

    async def next(self, interaction):
        self.page = min(2, self.page + 1); self.rebuild()
        await interaction.response.edit_message(view=self)

    def make_number_callback(self, number: int):
        async def callback(interaction):
            conn = db()
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute("SELECT * FROM number_games WHERE channel_id=? AND status='choosing'", (self.channel_id,)).fetchone()
                if not row:
                    conn.rollback(); return await interaction.response.send_message("❌ Вибір уже завершено.", ephemeral=True)
                column = "proposer_number" if interaction.user.id == self.proposer_id else "opponent_number"
                if row[column] is not None:
                    conn.rollback(); return await interaction.response.send_message("❌ Ти вже обрав число.", ephemeral=True)
                conn.execute(f"UPDATE number_games SET {column}=? WHERE channel_id=?", (number, self.channel_id))
                conn.commit()
                updated = conn.execute("SELECT * FROM number_games WHERE channel_id=?", (self.channel_id,)).fetchone()
            finally:
                conn.close()
            await interaction.response.send_message(embed=embed("🔒 Число збережено", f"Твоє таємне число: **{number}**.\n\n⏳ Чекаємо на число суперника..."), ephemeral=True)
            if updated["proposer_number"] is not None and updated["opponent_number"] is not None:
                await start_number_round(interaction.channel, self.channel_id)
            else:
                other = self.opponent_id if interaction.user.id == self.proposer_id else self.proposer_id
                await interaction.channel.send(f"<@{other}>", embed=embed("🔔 Суперник уже обрав число", "Тепер обери своє таємне число від 1 до 30."), delete_after=15)
        return callback

async def start_number_round(channel, channel_id):
    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM number_games WHERE channel_id=?", (channel_id,)).fetchone()
        if not row or row["status"] != "choosing":
            conn.rollback(); return
        guesser = random.choice([row["proposer_id"], row["opponent_id"]])
        conn.execute("UPDATE number_games SET current_guesser_id=?, status='playing' WHERE channel_id=?", (guesser, channel_id))
        conn.commit()
    finally:
        conn.close()
    await channel.send(embed=embed("🎯 Гра починається!", f"Бот випадково обрав, хто починає: <@{guesser}>.\n\nТвоя черга — введи число від **1 до 30**.", discord.Color.gold()), view=NumberGuessView(channel_id))

class NumberGuessView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=900); self.channel_id = channel_id

    @discord.ui.button(label="🎯 Вгадати число", style=discord.ButtonStyle.success)
    async def guess(self, interaction, button):
        conn = db(); row = conn.execute("SELECT current_guesser_id,status FROM number_games WHERE channel_id=?", (self.channel_id,)).fetchone(); conn.close()
        if not row or row["status"] != "playing":
            return await interaction.response.send_message("❌ Гра вже завершена.", ephemeral=True)
        if row["current_guesser_id"] != interaction.user.id:
            return await interaction.response.send_message("⏳ Зараз твоя черга ще не настала.", ephemeral=True)
        await interaction.response.send_modal(NumberGuessModal(self.channel_id))

class NumberGuessModal(discord.ui.Modal, title="🎯 Твоє припущення"):
    number = discord.ui.TextInput(label="Число від 1 до 30", placeholder="Наприклад: 20", max_length=2, required=True)
    def __init__(self, channel_id):
        super().__init__(); self.channel_id = channel_id
    async def on_submit(self, interaction):
        try: guess = int(str(self.number.value).strip())
        except ValueError: return await interaction.response.send_message("❌ Введи ціле число від 1 до 30.", ephemeral=True)
        if not 1 <= guess <= 30: return await interaction.response.send_message("❌ Число має бути від 1 до 30.", ephemeral=True)
        result = await process_number_guess(self.channel_id, interaction.user.id, guess, interaction.channel)
        await interaction.response.send_message(result, ephemeral=True)

async def process_number_guess(channel_id, user_id, guess, channel):
    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM number_games WHERE channel_id=?", (channel_id,)).fetchone()
        if not row or row["status"] != "playing":
            conn.rollback(); return "❌ Гра вже завершена."
        if row["current_guesser_id"] != user_id:
            conn.rollback(); return "⏳ Зараз число вгадує суперник. Почекай своєї черги."
        target = row["opponent_number"] if user_id == row["proposer_id"] else row["proposer_number"]
        if guess == target:
            winnings = row["bet"] * 2
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (winnings, user_id))
            conn.execute("UPDATE number_games SET status='finished', ended_at=? WHERE channel_id=?", (datetime.now(timezone.utc).isoformat(), channel_id))
            conn.commit(); won = True
        else:
            next_id = row["opponent_id"] if user_id == row["proposer_id"] else row["proposer_id"]
            conn.execute("UPDATE number_games SET current_guesser_id=? WHERE channel_id=?", (next_id, channel_id))
            conn.commit(); won = False
    finally:
        conn.close()
    if won:
        await channel.send(embed=embed("🏆 Перемога!", f"🎯 <@{user_id}> вгадав число суперника!\n\n🔢 Загадане число: **{target}**\n💰 Переможець отримує **{money(winnings)}** 💰 (**X2** від ставки **{money(row['bet'])}**).", discord.Color.green()))
        asyncio.create_task(delete_number_channel_later(channel, channel_id))
        return f"🎉 Ти вгадав! Ти отримуєш **{money(winnings)}** 💰."
    direction = "⬆️" if target > guess else "⬇️"
    next_id = row["opponent_id"] if user_id == row["proposer_id"] else row["proposer_id"]
    await channel.send(embed=embed("🎯 Підказка", f"<@{user_id}> назвав **{guess}**. {direction} **Число {'більше' if target > guess else 'менше'} за {guess}**.\n\nТепер черга <@{next_id}>.", discord.Color.blurple()), view=NumberGuessView(channel_id))
    return f"{direction} Число {'більше' if target > guess else 'менше'} за **{guess}**. Тепер чекаємо на суперника."

async def delete_number_channel_later(channel, channel_id):
    await asyncio.sleep(NUMBER_DELETE_AFTER)
    try: await channel.delete(reason="Гра вгадай число завершена")
    except discord.HTTPException: pass
    number_games.pop(channel_id, None)

@bot.tree.command(name="number", description="Запропонувати гравцю гру вгадай число 1–30")
@app_commands.describe(user="Суперник", bet="Ставка")
async def number(interaction: discord.Interaction, user: discord.Member, bet: app_commands.Range[int, MIN_COINFLIP_BET, MAX_BET]):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if not interaction.guild: return await interaction.response.send_message("Тільки на сервері.", ephemeral=True)
    if user.bot or user.id == interaction.user.id: return await interaction.response.send_message("❌ Обери іншого гравця.", ephemeral=True)
    u = get_user(interaction.user.id, interaction.user.name)
    if u["balance"] < bet: return await interaction.response.send_message(f"❌ Недостатньо грошей. Потрібно **{money(bet)}** 💰.", ephemeral=True)
    conn = db(); exists = conn.execute("SELECT 1 FROM number_games WHERE status IN ('choosing','playing') AND (proposer_id=? OR opponent_id=?)", (interaction.user.id, interaction.user.id)).fetchone(); conn.close()
    if exists: return await interaction.response.send_message("❌ Ти вже береш участь у грі. Заверши її перед новою ставкою.", ephemeral=True)
    await interaction.response.send_message(embed=embed("🎯 Пропозиція гри", f"{interaction.user.mention} пропонує {user.mention} зіграти у **вгадай число 1–30**.\n\n💰 Ставка: **{money(bet)}** з кожного.\n🏆 Переможець отримує **{money(bet*2)}** (X2).", discord.Color.gold()), view=NumberChallengeView(interaction.user.id, user.id, bet))

@bot.tree.command(name="guess", description="Ввести число під час гри вгадай число")
@app_commands.describe(number="Число від 1 до 30")
async def guess_command(interaction: discord.Interaction, number: app_commands.Range[int, 1, 30]):
    conn = db(); row = conn.execute("SELECT * FROM number_games WHERE channel_id=? AND status='playing'", (interaction.channel_id,)).fetchone(); conn.close()
    if not row: return await interaction.response.send_message("❌ Тут немає активної гри вгадай число.", ephemeral=True)
    result = await process_number_guess(interaction.channel_id, interaction.user.id, number, interaction.channel)
    await interaction.response.send_message(result, ephemeral=True)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return
    conn = db(); row = conn.execute("SELECT * FROM number_games WHERE channel_id=? AND status='playing'", (message.channel.id,)).fetchone(); conn.close()
    if row and message.content.strip().isdigit():
        try: await message.delete()
        except discord.HTTPException: pass
        if row["current_guesser_id"] != message.author.id:
            text = f"<@{message.author.id}> ⏳ Зараз число вгадує суперник. Зачекай своєї черги."
        else:
            text = f"<@{message.author.id}> 🎯 Використай кнопку **«Вгадати число»** або команду `/guess`."
        try: await message.channel.send(text, delete_after=5)
        except discord.HTTPException: pass
        return
    await bot.process_commands(message)

# ---------------- MASTURBATION ----------------
async def finish_masturbation_session(session_id: int):
    await asyncio.sleep(MASTURBATION_DURATION)
    conn=db()
    try:
        row=conn.execute("SELECT * FROM masturbation_sessions WHERE session_id=? AND status='running'",(session_id,)).fetchone()
        if not row: return
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(row["reward"],row["user_id"]))
        conn.execute("UPDATE masturbation_sessions SET status='finished', finished_at=? WHERE session_id=?",
                     (datetime.now(timezone.utc).isoformat(),session_id))
        conn.commit()
        user=bot.get_user(row["user_id"])
        if user:
            try:
                await user.send(embed=embed("💰 Бонус отримано!",f"Ти закінчив. Твій бонус: **{money(row['reward'])}** 💰.",discord.Color.green()))
            except discord.HTTPException:
                pass
    finally: conn.close()

async def resume_masturbation_sessions():
    conn=db()
    rows=conn.execute("SELECT session_id, finishes_at FROM masturbation_sessions WHERE status='running'").fetchall()
    conn.close()
    now=datetime.now(timezone.utc)
    for row in rows:
        delay=max(0,(parse_time(row["finishes_at"])-now).total_seconds())
        async def worker(sid=row["session_id"], d=delay):
            await asyncio.sleep(d); await finish_masturbation_session(sid)
        asyncio.create_task(worker())

@bot.tree.command(name="masturbation", description="Отримати бонус за завершення активності")
async def masturbation(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    conn=db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        running=conn.execute("SELECT 1 FROM masturbation_sessions WHERE user_id=? AND status='running'",(interaction.user.id,)).fetchone()
        if running:
            conn.rollback()
            return await interaction.response.send_message("⏳ Ти вже виконуєш цю активність.",ephemeral=True)
        last=conn.execute("""SELECT finished_at, started_at FROM masturbation_sessions
                             WHERE user_id=? AND status='finished' ORDER BY session_id DESC LIMIT 1""",(interaction.user.id,)).fetchone()
        if last:
            left=cooldown_left(last["finished_at"],MASTURBATION_COOLDOWN)
            if left.total_seconds()>0:
                conn.rollback()
                return await interaction.response.send_message(f"⏳ Наступний раз можна через **{fmt_duration(left)}**.",ephemeral=True)
        now=datetime.now(timezone.utc)
        finishes=now+timedelta(seconds=MASTURBATION_DURATION)
        reward=random.randint(5_000,15_000)
        cur=conn.execute("""INSERT INTO masturbation_sessions(user_id,started_at,finishes_at,reward,status)
                            VALUES(?,?,?,?, 'running')""",(interaction.user.id,now.isoformat(),finishes.isoformat(),reward))
        session_id=cur.lastrowid
        conn.commit()
    finally: conn.close()
    asyncio.create_task(finish_masturbation_session(session_id))
    await interaction.response.send_message(embed=embed("⏳ Активність розпочато",
        "Ти почав. Коли завершиш, отримаєш випадковий бонус **від 5 000 до 15 000 💰**.\n\n⏱️ Тривалість: **30 секунд**.\n🔁 Повторити можна **раз на 2 години**.",discord.Color.blurple()),ephemeral=False)


# ---------------- ADMIN ----------------

def admin_denied(interaction):
    return interaction.response.send_message("Немає доступу.", ephemeral=True)

async def set_admin_status(actor: discord.Member, target: discord.Member, enabled: bool):
    if not is_owner(actor.id):
        return False, "Лише власник може призначати або знімати адміністраторів."
    if target.id == OWNER_ID:
        return False, "Власника не можна змінити."
    conn = db()
    conn.execute(
        "INSERT OR IGNORE INTO users(user_id, username, dick_size, balance) VALUES (?, ?, ?, 0)",
        (target.id, target.name, START_DICK_SIZE)
    )
    conn.execute("UPDATE users SET username=?, admin=? WHERE user_id=?", (target.name, int(enabled), target.id))
    conn.commit(); conn.close()
    return True, ""

async def give_admin(interaction, user: discord.Member):
    ok, reason = await set_admin_status(interaction.user, user, True)
    if not ok:
        return await interaction.response.send_message(reason, ephemeral=True)

    role = interaction.guild.get_role(ROLE_ADMIN_ID) if interaction.guild else None
    if role:
        try:
            await user.add_roles(role, reason="Призначення адміністратором ботом")
        except discord.HTTPException:
            pass

    server_name = interaction.guild.name if interaction.guild else "Discord сервері"
    dm = discord.Embed(
        title="Призначення адміністратора",
        description=f"Вас було призначено на посаду адміністратора в діскорд сервері **{server_name}**.",
        color=discord.Color.green()
    )
    try:
        await user.send(embed=dm)
    except discord.HTTPException:
        pass

    await interaction.response.send_message(f"Адміністратора призначено: {user.mention}.", ephemeral=True)

async def take_admin(interaction, user: discord.Member):
    ok, reason = await set_admin_status(interaction.user, user, False)
    if not ok:
        return await interaction.response.send_message(reason, ephemeral=True)

    role = interaction.guild.get_role(ROLE_ADMIN_ID) if interaction.guild else None
    if role:
        try:
            await user.remove_roles(role, reason="Зняття адміністратора ботом")
        except discord.HTTPException:
            pass
    await interaction.response.send_message(f"Адміністратора знято: {user.mention}.", ephemeral=True)

class GiveMoneyModal(discord.ui.Modal, title="Видати гроші"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    amount = discord.ui.TextInput(label="Кількість грошей", placeholder="50000")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        try: uid, amount = int(self.user_id.value.strip()), int(self.amount.value.strip()); assert amount > 0
        except (ValueError, AssertionError): return await interaction.response.send_message("Невірні дані.", ephemeral=True)
        money_add(uid, amount); await interaction.response.send_message(f"{uid} отримав {money(amount)}.", ephemeral=True)

class SetMoneyModal(discord.ui.Modal, title="Встановити гроші"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    amount = discord.ui.TextInput(label="Новий баланс", placeholder="50000")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        try: uid, amount = int(self.user_id.value.strip()), int(self.amount.value.strip()); assert amount >= 0
        except (ValueError, AssertionError): return await interaction.response.send_message("Невірні дані.", ephemeral=True)
        old = get_user(uid)["balance"]; money_set(uid, amount)
        await interaction.response.send_message(f"Баланс {uid}: {money(old)} → {money(amount)}.", ephemeral=True)

class SetDickModal(discord.ui.Modal, title="Встановити розмір"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    size = discord.ui.TextInput(label="Новий розмір", placeholder="10")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        try: uid, size = int(self.user_id.value.strip()), int(self.size.value.strip())
        except ValueError: return await interaction.response.send_message("Невірні дані.", ephemeral=True)
        old = get_user(uid)["dick_size"]; dick_set(uid, size)
        await interaction.response.send_message(f"Розмір {uid}: {old} см → {size} см.", ephemeral=True)

class RigRouletteModal(discord.ui.Modal, title="Накрутка рулетки"):
    number = discord.ui.TextInput(label="Наступне число (1-50)", placeholder="17")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        try: n = int(self.number.value.strip()); assert 1 <= n <= 50
        except (ValueError, AssertionError): return await interaction.response.send_message("Невірне число.", ephemeral=True)
        set_setting("roulette_next", str(n)); await interaction.response.send_message(f"Наступного разу рулетка спробує показати {n}.", ephemeral=True)

class RigCoinModal(discord.ui.Modal, title="Накрутка монетки"):
    result = discord.ui.TextInput(label="Наступний результат", placeholder="Орел або Решка")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        value = self.result.value.strip().lower()
        mapping = {"орел": "Орел", "решка": "Решка", "heads": "Орел", "tails": "Решка"}
        if value not in mapping: return await interaction.response.send_message("Напиши Орел або Решка.", ephemeral=True)
        set_setting("coinflip_next", mapping[value]); await interaction.response.send_message(
            f"🎲 Накрутку встановлено: **{mapping[value]}**. Її отримає **перший наступний прокрут будь-якого користувача**, після чого вона автоматично зникне.",
            ephemeral=True
        )

class AdminUserModal(discord.ui.Modal, title="Призначити адміністратора"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    async def on_submit(self, interaction):
        if not is_owner(interaction.user.id): return await admin_denied(interaction)
        try: uid=int(self.user_id.value.strip())
        except ValueError: return await interaction.response.send_message("Невірний ID.", ephemeral=True)
        member=interaction.guild.get_member(uid)
        if not member:
            return await interaction.response.send_message("Користувача не знайдено на сервері.", ephemeral=True)
        await give_admin(interaction, member)

class TakeAdminModal(discord.ui.Modal, title="Зняти адміністратора"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    async def on_submit(self, interaction):
        if not is_owner(interaction.user.id): return await admin_denied(interaction)
        try: uid=int(self.user_id.value.strip())
        except ValueError: return await interaction.response.send_message("Невірний ID.", ephemeral=True)
        member=interaction.guild.get_member(uid)
        if not member:
            return await interaction.response.send_message("Користувача не знайдено на сервері.", ephemeral=True)
        await take_admin(interaction, member)

class MsgSendModal(discord.ui.Modal, title="Надіслати повідомлення користувачу в лс"):
    user = discord.ui.TextInput(label="Нік користувача або Discord ID", placeholder="username або 123456789012345678")
    text = discord.ui.TextInput(label="Текст повідомлення", style=discord.TextStyle.paragraph, max_length=4000)
    attachment_url = discord.ui.TextInput(label="Посилання на фото/відео (необов'язково)", required=False, placeholder="https://...")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        member = await resolve_member(interaction.guild, str(self.user.value).strip())
        if not member:
            return await interaction.response.send_message("Користувача не знайдено. Вкажи нік або Discord ID.", ephemeral=True)
        e = discord.Embed(title="Повідомлення", description=str(self.text.value), color=discord.Color.blurple())
        if self.attachment_url.value.strip():
            e.set_image(url=self.attachment_url.value.strip())
        try:
            await member.send(embed=e)
        except discord.HTTPException:
            return await interaction.response.send_message("Не вдалося надіслати повідомлення в особисті повідомлення.", ephemeral=True)
        await interaction.response.send_message(f"Повідомлення надіслано {member.mention}.", ephemeral=True)

async def resolve_member(guild, value):
    value=value.strip()
    if value.isdigit():
        return guild.get_member(int(value))
    value=value.lstrip("@")
    lower=value.lower()
    for m in guild.members:
        if m.name.lower()==lower or m.display_name.lower()==lower or str(m).lower()==lower:
            return m
    return None

def _chunk_text(text: str, limit: int = 3500):
    if not text:
        return ["—"]
    return [text[i:i + limit] for i in range(0, len(text), limit)]


def build_database_report():
    """Build a human-readable read-only snapshot of all persistent bot data."""
    conn = db()
    try:
        users = conn.execute(
            "SELECT user_id, username, dick_size, balance, admin, daily_at, dick_at, created_at "
            "FROM users ORDER BY balance DESC, user_id ASC"
        ).fetchall()
        promos = conn.execute(
            "SELECT code, money, dick, created_by, created_at FROM promos ORDER BY code ASC"
        ).fetchall()
        uses = conn.execute(
            "SELECT code, user_id, used_at FROM promo_uses ORDER BY code ASC, user_id ASC"
        ).fetchall()
        roles = conn.execute(
            "SELECT role_id, guild_id, owner_id, name, color, price, for_sale FROM roles ORDER BY role_id ASC"
        ).fetchall()
        settings = conn.execute(
            "SELECT key, value FROM bot_settings ORDER BY key ASC"
        ).fetchall()
        cookie = conn.execute(
            "SELECT game_id, channel_id, proposer_id, opponent_id, bet, status, "
            "proposer_score, opponent_score, started_at, ended_at "
            "FROM cookie_games ORDER BY game_id DESC LIMIT 100"
        ).fetchall()
        inventory_rows = conn.execute(
            "SELECT user_id, item_type, item_key, quantity FROM inventory_items WHERE quantity > 0 ORDER BY user_id, item_type, item_key"
        ).fetchall()
        market_rows = conn.execute(
            "SELECT listing_id, seller_id, item_type, item_key, price, status FROM market_listings ORDER BY listing_id DESC LIMIT 100"
        ).fetchall()
    finally:
        conn.close()

    parts = []

    users_text = []
    for i, u in enumerate(users, 1):
        users_text.append(
            f"{i}. <@{u['user_id']}> | ID `{u['user_id']}` | "
            f"💰 `{money(u['balance'])}` | 🍆 `{u['dick_size']} см` | "
            f"admin=`{u['admin']}` | username=`{u['username'] or '—'}`"
        )
    parts.append(("👥 Користувачі", "\n".join(users_text) or "Немає записів."))

    promo_text = [
        f"🎟️ `{p['code']}` → 💰 `{money(p['money'])}`, 🍆 `{p['dick']:+d} см`, "
        f"created_by=`{p['created_by']}`"
        for p in promos
    ]
    parts.append(("🎟️ Промокоди", "\n".join(promo_text) or "Немає промокодів."))

    uses_text = [
        f"`{x['code']}` → <@{x['user_id']}> (`{x['user_id']}`) | {x['used_at']}"
        for x in uses
    ]
    parts.append(("✅ Активації промокодів", "\n".join(uses_text) or "Немає активацій."))

    role_text = [
        f"`{r['role_id']}` | **{discord.utils.escape_markdown(r['name'])}** | "
        f"owner=`{r['owner_id']}` | price=`{money(r['price'])}` | sale=`{r['for_sale']}` | "
        f"color=`#{r['color']:06X}` | guild=`{r['guild_id']}`"
        for r in roles
    ]
    parts.append(("🏷️ Ролі", "\n".join(role_text) or "Немає записів."))

    settings_text = [
        f"`{x['key']}` = `{x['value']}`"
        for x in settings
    ]
    parts.append(("⚙️ Одноразові налаштування / накрутки", "\n".join(settings_text) or "Немає активних значень."))

    cookie_text = [
        f"`#{x['game_id']}` | <@{x['proposer_id']}> vs <@{x['opponent_id']}> | "
        f"💰 `{money(x['bet'])}` | `{x['status']}` | "
        f"🍪 {x['proposer_score']}:{x['opponent_score']}"
        for x in cookie
    ]
    parts.append(("🍪 Історія ігор", "\n".join(cookie_text) or "Немає записів."))

    inventory_text = [
        f"<@{x['user_id']}> | `{x['item_type']}` | {x['item_key']} | `{x['quantity']} шт.`"
        for x in inventory_rows
    ]
    parts.append(("🎒 Загальний інвентар", "\n".join(inventory_text) or "Немає предметів в інвентарях."))

    market_text = [
        f"#{x['listing_id']} | seller=`{x['seller_id']}` | {x['item_type']} | {x['item_key']} | {money(x['price'])} | `{x['status']}`"
        for x in market_rows
    ]
    parts.append(("🏪 Ринок", "\n".join(market_text) or "Немає оголошень."))

    return parts


async def send_database_report(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        return await admin_denied(interaction)

    try:
        health = await asyncio.to_thread(database_health)
        parts = await asyncio.to_thread(build_database_report)
    except Exception as exc:
        return await interaction.response.send_message(
            f"❌ Не вдалося прочитати БД: `{exc!r}`", ephemeral=True
        )

    summary = (
        f"**Стан БД:** {'🟢 OK' if health['ok'] else '🔴 ПОМИЛКА'}\n"
        f"Integrity: `{health['integrity']}`\n"
        f"👥 Користувачів: **{health['users']}**\n"
        f"🎟️ Промокодів: **{health['promos']}**\n"
        f"📁 DB: `{DB_PATH}`\n"
        f"💾 Backups: `{BACKUP_DIR}`"
    )

    await interaction.response.send_message(
        embed=embed("🗄️ Повна інформація БД", summary, discord.Color.blurple()),
        ephemeral=True
    )

    for title, text in parts:
        chunks = _chunk_text(text)
        for number, chunk in enumerate(chunks, 1):
            suffix = f" ({number}/{len(chunks)})" if len(chunks) > 1 else ""
            e = embed(title + suffix, chunk, discord.Color.dark_grey())
            await interaction.followup.send(embed=e, ephemeral=True)


class AdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    async def check(self, interaction):
        if not is_admin(interaction.user.id):
            await admin_denied(interaction); return False
        return True

    @discord.ui.button(label="Видати гроші", style=discord.ButtonStyle.success, row=0)
    async def give_money(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(GiveMoneyModal())

    @discord.ui.button(label="Встановити гроші", style=discord.ButtonStyle.primary, row=0)
    async def set_money(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(SetMoneyModal())

    @discord.ui.button(label="Встановити розмір", style=discord.ButtonStyle.primary, row=0)
    async def set_dick(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(SetDickModal())

    @discord.ui.button(label="Накрутка рулетки", style=discord.ButtonStyle.danger, row=1)
    async def rig_roulette(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(RigRouletteModal())

    @discord.ui.button(label="Накрутка монетки", style=discord.ButtonStyle.danger, row=1)
    async def rig_coin(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(RigCoinModal())

    @discord.ui.button(label="Призначити адміністратора", style=discord.ButtonStyle.primary, row=2)
    async def give_admin_btn(self, interaction, button):
        if not is_owner(interaction.user.id):
            return await admin_denied(interaction)
        await interaction.response.send_modal(AdminUserModal())

    @discord.ui.button(label="Зняти адміністратора", style=discord.ButtonStyle.danger, row=2)
    async def take_admin_btn(self, interaction, button):
        if not is_owner(interaction.user.id):
            return await admin_denied(interaction)
        await interaction.response.send_modal(TakeAdminModal())

    @discord.ui.button(label="База даних", emoji="🗄️", style=discord.ButtonStyle.secondary, row=3)
    async def database_info_btn(self, interaction, button):
        await send_database_report(interaction)

    @discord.ui.button(label="Надіслати повідомлення", style=discord.ButtonStyle.secondary, row=3)
    async def msg_send_btn(self, interaction, button):
        if await self.check(interaction):
            await interaction.response.send_modal(MsgSendModal())

@bot.tree.command(name="admin", description="🔒 Адмін-панель")
@app_commands.default_permissions(administrator=True)
async def admin(interaction: discord.Interaction):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    await interaction.response.send_message(
        embed=embed("🛠️ Адмін-панель", "💰 Економіка • 🍆 Розміри • 🎟️ Промокоди • 🎲 Накрутки • 🗄️ База даних\n\nПанель доступна адміністраторам. Власник також може призначати та знімати адміністраторів.", discord.Color.dark_red()),
        view=AdminView(), ephemeral=True
    )

@bot.tree.command(name="givemoney", description="🔒 Видати гроші користувачу")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", amount="Кількість")
async def givemoney(interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1, MAX_BET]):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    money_add(user.id, amount); await interaction.response.send_message(f"{user.mention} отримав {money(amount)}.", ephemeral=True)

@bot.tree.command(name="setmoney", description="🔒 Встановити баланс користувачу")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", amount="Новий баланс")
async def setmoney(interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 0, MAX_BET]):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    old = get_user(user.id, user.name)["balance"]; money_set(user.id, amount)
    await interaction.response.send_message(f"Баланс {user.mention}: {money(old)} → {money(amount)}.", ephemeral=True)

@bot.tree.command(name="setdick", description="🔒 Встановити розмір користувачу")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", size="Новий розмір")
async def setdick(interaction: discord.Interaction, user: discord.Member, size: int):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    old = get_user(user.id, user.name)["dick_size"]; dick_set(user.id, size)
    await interaction.response.send_message(f"Розмір {user.mention}: {old} см → {size} см.", ephemeral=True)

@bot.tree.command(name="giveadmin", description="🔒 Призначити адміністратора")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач")
async def giveadmin(interaction: discord.Interaction, user: discord.Member):
    if not is_owner(interaction.user.id): return await admin_denied(interaction)
    await give_admin(interaction, user)

@bot.tree.command(name="takeadmin", description="🔒 Зняти адміністратора")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач")
async def takeadmin(interaction: discord.Interaction, user: discord.Member):
    if not is_owner(interaction.user.id): return await admin_denied(interaction)
    await take_admin(interaction, user)

@bot.tree.command(name="setadmin", description="🔒 Змінити статус адміністратора")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", enabled="True — видати, False — забрати")
async def setadmin(interaction: discord.Interaction, user: discord.Member, enabled: bool):
    if not is_owner(interaction.user.id):
        return await admin_denied(interaction)
    if enabled:
        await give_admin(interaction, user)
    else:
        await take_admin(interaction, user)

@bot.tree.command(name="msg_send", description="🔒 Надіслати повідомлення користувачу в лс")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", text="Текст", attachment="Фото або відео")
async def msg_send(interaction: discord.Interaction, user: discord.Member, text: str, attachment: Optional[discord.Attachment] = None):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    try:
        if attachment:
            await user.send(content=text, file=await attachment.to_file())
        else:
            await user.send(content=text)
    except discord.HTTPException:
        return await interaction.response.send_message("Не вдалося надіслати повідомлення в особисті повідомлення.", ephemeral=True)
    await interaction.response.send_message(f"Повідомлення надіслано {user.mention}.", ephemeral=True)

@bot.tree.command(name="promo_create", description="🔒 Створити промокод")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(code="Код", money_amount="Гроші", dick_amount="Скільки см")
async def promo_create(interaction: discord.Interaction, code: str, money_amount: app_commands.Range[int, 0, MAX_BET], dick_amount: int):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    code = code.strip().upper()
    conn = db()
    try:
        conn.execute("INSERT INTO promos(code, money, dick, created_by) VALUES (?, ?, ?, ?)", (code, money_amount, dick_amount, interaction.user.id)); conn.commit()
    except sqlite3.IntegrityError:
        conn.close(); return await interaction.response.send_message("Такий промокод уже існує.", ephemeral=True)
    conn.close(); await interaction.response.send_message(f"Промокод {code} створено. +{money(money_amount)}, {dick_amount:+d} см.", ephemeral=True)

# ---------------- START ----------------

@bot.event
async def on_ready():
    global _backup_task
    init_db()
    await resume_masturbation_sessions()
    if _backup_task is None or _backup_task.done():
        _backup_task = asyncio.create_task(backup_loop())
    try:
        health = await asyncio.to_thread(database_health)
        print(f"[DB] Health: {health}")
        if not health["ok"]:
            raise RuntimeError(f"Database integrity check failed: {health}")
        # Create a verified backup after successful startup/migrations.
        async with DB_LOCK:
            await asyncio.to_thread(_backup_once, "startup")
    except Exception as exc:
        print(f"[DB] Startup safety check failed: {exc!r}")
        raise
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"Logged in as {bot.user}. Synced {len(synced)} commands to guild {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            print(f"Logged in as {bot.user}. Synced {len(synced)} global commands.")
    except Exception as e:
        print("Slash command sync error:", repr(e))


init_db()

# Final best-effort backup on normal interpreter shutdown. Railway Volume remains
# the primary persistence layer; backups are an additional recovery layer.
import atexit
atexit.register(lambda: _backup_once("shutdown"))

bot.run(TOKEN)
