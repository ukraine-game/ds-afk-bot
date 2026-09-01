import os
import random
import sqlite3
import asyncio
import time
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
PURCHASE_LOG_CHANNEL_ID = 1543243790943391764
SYSTEM_LOG_CHANNEL_ID = 1543244165805117600
ADMIN_LOG_CHANNEL_ID = 1543248471102984222
MAX_LOAN_DAYS = 10
LEVEL_THRESHOLDS = [20, 40, 60, 80, 100, 120, 150, 200, 250, 300, 350, 450, 550, 650, 800, 1000, 1200, 1400, 1600]
BUSINESS_TAX_DEFAULT = 5
PRESIDENT_MAX_WITHDRAW = 1_000_000
PRESIDENT_WITHDRAW_COOLDOWN = 86400
PRESIDENT_NEWS_COOLDOWN = 7200
ELECTION_DURATION = 86400
ELECTION_INTERVAL = 7 * 86400
IDI_COOLDOWN_SECONDS = 30
IDI_REWARD_MIN = 500
IDI_REWARD_MAX = 5000
_idi_cooldowns: dict[int, float] = {}
_idi_cooldown_lock = asyncio.Lock()

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
ECONOMY_LOOP_SECONDS = max(15, int(os.getenv("ECONOMY_LOOP_SECONDS", "30")))
BUSINESS_DM_BATCH_SIZE = max(1, min(25, int(os.getenv("BUSINESS_DM_BATCH_SIZE", "10"))))
BUSINESS_DM_RETRY_BASE_SECONDS = max(15, int(os.getenv("BUSINESS_DM_RETRY_BASE_SECONDS", "30")))
BUSINESS_DM_RETRY_MAX_SECONDS = max(300, int(os.getenv("BUSINESS_DM_RETRY_MAX_SECONDS", "3600")))

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
            "active_business": "TEXT",
            "garage_type": "TEXT",
            "garage_purchased_at": "TEXT",
            "garage_offer_sent_at": "TEXT",
            "garage_offer_deadline": "TEXT",
            "garage_reminder_at": "TEXT",
            "garage_last_check_at": "TEXT",
            "bank_banned": "INTEGER NOT NULL DEFAULT 0",
            "bank_ban_reason": "TEXT",
            "stamina": "INTEGER NOT NULL DEFAULT 0",
            "level": "INTEGER NOT NULL DEFAULT 1",
            "successful_commands": "INTEGER NOT NULL DEFAULT 0",
            "robbery_at": "TEXT",
        },
        "businesses": {
            "last_paid_at": "TEXT NOT NULL DEFAULT ''",
        },
        "promos": {"created_at": "TEXT NOT NULL DEFAULT ''"},
        "promo_uses": {"used_at": "TEXT NOT NULL DEFAULT ''"},
        "loans": {"reminder_at": "TEXT"},
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
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        stamina INTEGER NOT NULL DEFAULT 0
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
        finished_at TEXT,
        channel_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS businesses (
        business_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        business_name TEXT NOT NULL,
        price INTEGER NOT NULL,
        hourly_profit INTEGER NOT NULL,
        purchased_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_paid_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS garage_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        event_at TEXT NOT NULL,
        details TEXT
    );

    CREATE TABLE IF NOT EXISTS loans (
        loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        lender_id INTEGER NOT NULL,
        borrower_id INTEGER NOT NULL,
        principal INTEGER NOT NULL,
        rate REAL NOT NULL,
        total_due INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        due_at TEXT NOT NULL,
        grace_until TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        due_notice_sent_at TEXT,
        reminder_at TEXT,
        closed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS loan_offers (
        offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        proposer_id INTEGER NOT NULL,
        counterparty_id INTEGER NOT NULL,
        lender_id INTEGER NOT NULL,
        borrower_id INTEGER NOT NULL,
        principal INTEGER NOT NULL,
        rate REAL NOT NULL,
        days INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

    CREATE TABLE IF NOT EXISTS business_payouts (
        payout_id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        gross_amount INTEGER NOT NULL,
        tax_amount INTEGER NOT NULL,
        net_amount INTEGER NOT NULL,
        paid_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS business_preferences (
        user_id INTEGER PRIMARY KEY,
        interval_seconds INTEGER NOT NULL DEFAULT 3600,
        last_dm_at TEXT,
        onboarding_sent INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS business_notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        payout_id INTEGER NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        business_name TEXT NOT NULL,
        gross_amount INTEGER NOT NULL,
        tax_amount INTEGER NOT NULL,
        net_amount INTEGER NOT NULL,
        hours INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        sent_at TEXT,
        attempts INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        next_attempt_at TEXT
    );

    CREATE TABLE IF NOT EXISTS president_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS elections (
        election_id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        ends_at TEXT NOT NULL,
        channel_id INTEGER,
        message_id INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        winner_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS election_votes (
        election_id INTEGER NOT NULL,
        voter_id INTEGER NOT NULL,
        candidate_id INTEGER NOT NULL,
        voted_at TEXT NOT NULL,
        PRIMARY KEY(election_id, voter_id)
    );

    CREATE TABLE IF NOT EXISTS president_motions (
        motion_id INTEGER PRIMARY KEY AUTOINCREMENT,
        president_id INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active'
    );

    CREATE TABLE IF NOT EXISTS president_motion_votes (
        motion_id INTEGER NOT NULL,
        voter_id INTEGER NOT NULL,
        voted_at TEXT NOT NULL,
        PRIMARY KEY(motion_id, voter_id)
    );
    """)
    _migrate_schema(conn)
    # Move legacy case inventory into the unified /inventory storage once.
    conn.execute("""INSERT INTO inventory_items(user_id, item_type, item_key, quantity)\n                       SELECT user_id, 'case', rarity, quantity FROM case_inventory WHERE quantity > 0\n                       ON CONFLICT(user_id, item_type, item_key) DO UPDATE SET quantity=MAX(inventory_items.quantity, excluded.quantity)""")
    conn.execute("INSERT OR IGNORE INTO president_state(key,value) VALUES ('treasury','10000000')")
    conn.execute("INSERT OR IGNORE INTO president_state(key,value) VALUES ('business_tax','5')")
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
        new_balance = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        conn.commit()
        if ok:
            # Systematic economy log: every balance mutation is recorded.
            asyncio.get_event_loop().create_task(log_system(
                f"💰 Гравець <@{user_id}>: зміна бюджету **{amount:+,} грн.**. "
                f"Бюджет після: **{money(new_balance)} грн.**"
            ))
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


def has_stamina(user_id: int) -> bool:
    return bool(get_user(user_id)["stamina"])


def toggle_stamina(user_id: int) -> bool:
    ensure_user(user_id)
    conn = db()
    row = conn.execute("SELECT stamina FROM users WHERE user_id=?", (user_id,)).fetchone()
    new_value = 0 if row and row[0] else 1
    conn.execute("UPDATE users SET stamina=? WHERE user_id=?", (new_value, user_id))
    conn.commit()
    conn.close()
    return bool(new_value)


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
    if not u["stamina"] and left.total_seconds() > 0:
        await interaction.response.send_message(
            f"⏳ Ти вже використовував команду сьогодні. До наступної спроби: **{fmt_duration(left)}**.",
            ephemeral=True,
        )
        return

    # Weighted random result from -3 to +8. Smaller changes are more common,
    # while larger positive results remain possible but rare.
    changes = list(range(-3, 9))
    weights = [8, 10, 12, 14, 14, 12, 10, 8, 6, 4, 3, 2]
    change = random.choices(changes, weights=weights, k=1)[0]

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


# ---------------- IDI ----------------

@bot.tree.command(name="idi", description="Послати іншого гравця нахуй та отримати гроші")
@app_commands.describe(user="Кого послати нахуй")
async def idi(interaction: discord.Interaction, user: discord.Member):
    """Public joke/economy command with a 30-second cooldown per user."""
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)

    if user.bot or user.id == interaction.user.id:
        return await interaction.response.send_message(
            "❌ Обери іншого користувача. Себе або бота посилати не можна 😄",
            ephemeral=True,
        )

    now = time.monotonic()
    async with _idi_cooldown_lock:
        last_used = _idi_cooldowns.get(interaction.user.id, 0.0)
        remaining = IDI_COOLDOWN_SECONDS - (now - last_used)
        if remaining > 0:
            return await interaction.response.send_message(
                f"⏳ Не так швидко! Повторно `/idi` можна використати через **{remaining:.1f} сек.**",
                ephemeral=True,
            )
        _idi_cooldowns[interaction.user.id] = now

    reward = random.randint(IDI_REWARD_MIN, IDI_REWARD_MAX) * level_multiplier(int(get_user(interaction.user.id)["level"] or 1))
    if not money_add(interaction.user.id, reward):
        # This should not normally happen, but don't consume the cooldown if
        # the economy update fails.
        async with _idi_cooldown_lock:
            _idi_cooldowns.pop(interaction.user.id, None)
        return await interaction.response.send_message(
            "❌ Не вдалося зарахувати нагороду. Спробуй ще раз.",
            ephemeral=True,
        )

    register_successful_command(interaction.user.id)
    await interaction.response.send_message(
        f"🖕 {interaction.user.mention} послав(ла) нахуй {user.mention} "
        f"і отримав(ла) **{money(reward)} грн.** 💰"
    )


# ---------------- LEVELS ----------------
def level_multiplier(level: int) -> int:
    return 2 ** max(0, int(level) - 1)

def register_successful_command(user_id: int, amount: int = 1):
    """Count only a completed, successful economy/action event."""
    if amount <= 0 or is_admin(user_id):
        return
    ensure_user(user_id)
    conn = db()
    row = conn.execute("SELECT successful_commands, level FROM users WHERE user_id=?", (user_id,)).fetchone()
    total = int(row["successful_commands"] or 0) + amount
    level = 1
    for threshold in LEVEL_THRESHOLDS:
        if total >= threshold:
            level += 1
        else:
            break
    old_level = int(row["level"] or 1)
    conn.execute("UPDATE users SET successful_commands=?, level=? WHERE user_id=?", (total, level, user_id))
    conn.commit(); conn.close()
    if level > old_level:
        try:
            asyncio.get_event_loop().create_task(safe_dm(user_id, embed_obj=embed(
                "🎉 Новий рівень!",
                f"Ти досяг **{level} рівня**!\n\n✨ Постійний множник бонусів: **x{level_multiplier(level)}**.",
                discord.Color.gold()
            )))
        except RuntimeError:
            pass

def get_level_info(user_id: int):
    u = get_user(user_id)
    level = int(u["level"] or 1)
    total = int(u["successful_commands"] or 0)
    if level >= 20:
        return level, total, None
    next_threshold = LEVEL_THRESHOLDS[level - 1]
    return level, total, next_threshold

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
    e.add_field(name="🚗 Автомобіль", value=f"**{u['active_car'] or 'немає'}**", inline=True)
    e.add_field(name="🏢 Бізнес", value=f"**{u['active_business'] or 'немає'}**", inline=True)
    e.add_field(name="🏠 Дім", value=f"**{u['primary_house'] or 'немає'}**", inline=True)
    e.add_field(name="🚘 Гараж", value=f"**{u['garage_type'] or 'немає'}**", inline=True)
    level, total, next_threshold = get_level_info(interaction.user.id if user is None else user.id)
    progress = f"{total}/{next_threshold}" if next_threshold else f"{total} (максимум)"
    e.add_field(name="⭐ Рівень", value=f"**{level}** • успішних команд: **{progress}** • бонуси: **x{level_multiplier(level)}**", inline=False)
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
    register_successful_command(interaction.user.id)
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
    if not u["stamina"] and left.total_seconds() > 0:
        await interaction.response.send_message(
            f"⏳ Наступний бонус буде доступний через **{fmt_duration(left)}**.", ephemeral=True
        )
        return
    reward = DAILY_REWARD * level_multiplier(int(u["level"] or 1))
    money_add(interaction.user.id, reward)
    register_successful_command(interaction.user.id)
    set_cooldown(interaction.user.id, "daily_at")
    await interaction.response.send_message(embed=embed(
         "🎁 Щоденний бонус",
        f"[🎁]({EMOJI_GIFT}) Ти отримав `{money(reward)}` [💰]({EMOJI_MONEY})!",
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
        if promo["money"] > 0:
            register_successful_command(interaction.user.id)
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
    def __init__(self, owner_id: int, bet: int, balance_before: int):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.bet = bet
        self.balance_before = balance_before
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
            register_successful_command(self.owner_id)
            await interaction.channel.send(
                embed=embed(title, text, color)
            )
            after_balance = get_user(self.owner_id)["balance"]
            asyncio.create_task(log_system(
                f"🪙 Гравець <@{self.owner_id}> поставив **{money(self.bet)} грн.** на **{self.choice}** в грі **Coinflip**. "
                f"Випало: **{result}**. "
                f"{'Виграш: +'+money(self.bet)+' грн.' if won else 'Забираю ставку: '+money(self.bet)+' грн.'} "
                f"Бюджет до: **{money(self.balance_before)}** — Бюджет після: **{money(after_balance)}**."
            ))
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
        view=CoinChoiceView(interaction.user.id, bet, u["balance"]),
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
    register_successful_command(a)
    register_successful_command(b)
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

            asyncio.create_task(log_purchase(f"Гравець **{interaction.user}** (<@{interaction.user.id}>) купив **{quantity} шт.** кейсів **{self.rarity}** за **{money(total)} грн.**"))
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

    @discord.ui.button(label="Відкрити в одному вікні", emoji="🎁", style=discord.ButtonStyle.success)
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


class BatchCaseResultView(discord.ui.View):
    """One compact menu for a multi-case opening.

    Nothing is committed to the player's inventory until they choose Claim.
    This prevents the old behaviour where 10 cases produced 10 separate menus.
    """

    def __init__(self, owner_id: int, rarity: str, results):
        super().__init__(timeout=600)
        self.owner_id = owner_id
        self.rarity = rarity
        self.results = [
            {"name": name, "value": value, "jackpot": jackpot, "chance": chance, "status": "pending"}
            for name, value, jackpot, chance in results
        ]
        self.lock = asyncio.Lock()
        self.selected_index = 0

        options = []
        for i, item in enumerate(self.results):
            marker = "🎰 " if item["jackpot"] else "🚗 "
            options.append(discord.SelectOption(
                label=f"{i + 1}. {item['name']}"[:100],
                description=f"{money(item['value'])} грн • {'джекпот' if item['jackpot'] else 'авто'}",
                emoji=marker.strip(),
                value=str(i)
            ))
        if options:
            select = discord.ui.Select(
                placeholder="🚗 Обери одну машину для окремої дії",
                options=options[:25],
                row=1
            )
            select.callback = self.select_car
            self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Це меню належить гравцю, який відкрив кейси.", ephemeral=True
            )
            return False
        return True

    def pending(self):
        return [x for x in self.results if x["status"] == "pending"]

    def build_embed(self):
        data = CASE_DATA[self.rarity]
        pending = self.pending()
        claimed = sum(x["status"] == "claimed" for x in self.results)
        sold = sum(x["status"] == "sold" for x in self.results)
        total_value = sum(x["value"] for x in pending)

        lines = []
        for i, item in enumerate(self.results, 1):
            if item["status"] == "claimed":
                state = "🚗 **ЗАБРАНО**"
            elif item["status"] == "sold":
                state = "💰 **ПРОДАНО**"
            else:
                state = "🟢 **ДОСТУПНО**"
            jackpot = " 🎰" if item["jackpot"] else ""
            lines.append(
                f"`{i:02}` • {state} • **{item['name']}** — {money(item['value'])} грн{jackpot}"
            )

        description = (
            f"{data['emoji']} **Рідкість:** {self.rarity}\n"
            f"📦 **Відкрито кейсів:** {len(self.results)}\n\n"
            + "\n".join(lines)
            + f"\n\n📊 **Забрано:** {claimed} • **Продано:** {sold} • **Залишилось:** {len(pending)}"
        )
        if pending:
            description += (
                f"\n💰 Сума вартості доступних машин: **{money(total_value)} грн**"
                "\n\n👇 Обери машину нижче для окремої дії або скористайся масовою кнопкою."
            )
        else:
            description += "\n\n✅ **Усі машини вже оброблені.**"

        title = "🎰 Результати відкриття кейсів!" if any(x["jackpot"] for x in self.results) else "🎁 Результати відкриття кейсів"
        return embed(title, description, discord.Color.gold() if any(x["jackpot"] for x in self.results) else discord.Color.blurple())

    def refresh_buttons(self):
        pending = self.pending()
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id in {"batch_claim", "batch_sell"}:
                    child.disabled = not bool(pending)
                elif child.custom_id in {"single_claim", "single_sell"}:
                    child.disabled = not (
                        0 <= self.selected_index < len(self.results)
                        and self.results[self.selected_index]["status"] == "pending"
                    )

    async def select_car(self, interaction: discord.Interaction):
        select = next((x for x in self.children if isinstance(x, discord.ui.Select)), None)
        if not select:
            return await interaction.response.send_message("❌ Не вдалося знайти вибір машини.", ephemeral=True)
        self.selected_index = int(select.values[0])
        item = self.results[self.selected_index]
        await interaction.response.send_message(
            f"🚗 Обрано **{item['name']}** — **{money(item['value'])} грн**.\n"
            "Тепер натисни **«Забрати обрану»** або **«Продати обрану»**.",
            ephemeral=True
        )

    @discord.ui.button(label="Забрати все", emoji="🚗", style=discord.ButtonStyle.success, row=0, custom_id="batch_claim")
    async def claim_all(self, interaction: discord.Interaction, button):
        async with self.lock:
            pending = self.pending()
            if not pending:
                return await interaction.response.send_message("❌ Усі машини вже оброблені.", ephemeral=True)
            for item in pending:
                add_inventory_item(self.owner_id, "car", item["name"], 1)
                item["status"] = "claimed"
            conn = db()
            row = conn.execute("SELECT active_car FROM users WHERE user_id=?", (self.owner_id,)).fetchone()
            if row and not row["active_car"] and self.results:
                first_claimed = next((x for x in self.results if x["status"] == "claimed"), None)
                if first_claimed:
                    conn.execute("UPDATE users SET active_car=? WHERE user_id=?", (first_claimed["name"], self.owner_id))
            conn.commit()
            conn.close()

            total = sum(x["value"] for x in pending)
            await log_purchase(
                f"Гравець <@{self.owner_id}> забрав **усі {len(pending)} автомобілі** з відкриття {self.rarity} кейсів. "
                f"Загальна вартість: **{money(total)} грн.**"
            )
            for x in self.results:
                if x["status"] == "claimed":
                    pass
            self.refresh_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await send_garage_offer(self.owner_id)

    @discord.ui.button(label="Продати все", emoji="💰", style=discord.ButtonStyle.danger, row=0, custom_id="batch_sell")
    async def sell_all(self, interaction: discord.Interaction, button):
        async with self.lock:
            pending = self.pending()
            if not pending:
                return await interaction.response.send_message("❌ Усі машини вже оброблені.", ephemeral=True)
            total = sum(x["value"] for x in pending)
            money_add(self.owner_id, total)
            for item in pending:
                item["status"] = "sold"
            await log_purchase(
                f"Гравець <@{self.owner_id}> продав **усі {len(pending)} автомобілі** з відкриття {self.rarity} кейсів "
                f"за **{money(total)} грн.**"
            )
            self.refresh_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Забрати обрану", emoji="🚗", style=discord.ButtonStyle.primary, row=2, custom_id="single_claim")
    async def claim_selected(self, interaction: discord.Interaction, button):
        async with self.lock:
            if not (0 <= self.selected_index < len(self.results)):
                return await interaction.response.send_message("❌ Спочатку обери машину.", ephemeral=True)
            item = self.results[self.selected_index]
            if item["status"] != "pending":
                return await interaction.response.send_message("❌ Ця машина вже оброблена.", ephemeral=True)
            add_inventory_item(self.owner_id, "car", item["name"], 1)
            conn = db()
            row = conn.execute("SELECT active_car FROM users WHERE user_id=?", (self.owner_id,)).fetchone()
            if row and not row["active_car"]:
                conn.execute("UPDATE users SET active_car=? WHERE user_id=?", (item["name"], self.owner_id))
            conn.commit()
            conn.close()
            item["status"] = "claimed"
            await log_purchase(
                f"Гравець <@{self.owner_id}> забрав автомобіль **{item['name']}** "
                f"({money(item['value'])} грн.) з відкриття кейсів."
            )
            self.refresh_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await send_garage_offer(self.owner_id)

    @discord.ui.button(label="Продати обрану", emoji="💵", style=discord.ButtonStyle.secondary, row=2, custom_id="single_sell")
    async def sell_selected(self, interaction: discord.Interaction, button):
        async with self.lock:
            if not (0 <= self.selected_index < len(self.results)):
                return await interaction.response.send_message("❌ Спочатку обери машину.", ephemeral=True)
            item = self.results[self.selected_index]
            if item["status"] != "pending":
                return await interaction.response.send_message("❌ Ця машина вже оброблена.", ephemeral=True)
            money_add(self.owner_id, item["value"])
            item["status"] = "sold"
            await log_purchase(
                f"Гравець <@{self.owner_id}> продав автомобіль **{item['name']}** "
                f"({money(item['value'])} грн.) з відкриття кейсів."
            )
            self.refresh_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)


# Backward-compatible single-result view for one case opened from /inventory.
class CarResultView(discord.ui.View):
    def __init__(self, owner_id: int, car_name: str, car_value: int):
        super().__init__(timeout=300)
        self.owner_id, self.car_name, self.car_value, self.done = owner_id, car_name, car_value, False

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Ці кнопки доступні лише тому, хто відкрив кейс.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Забрати", emoji="🚗", style=discord.ButtonStyle.success)
    async def claim(self, interaction, button):
        if self.done:
            return await interaction.response.send_message("❌ Цю машину вже оброблено.", ephemeral=True)
        self.done = True
        add_inventory_item(interaction.user.id, "car", self.car_name, 1)
        conn = db()
        row = conn.execute("SELECT active_car FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()
        if row and not row["active_car"]:
            conn.execute("UPDATE users SET active_car=? WHERE user_id=?", (self.car_name, interaction.user.id))
        conn.commit(); conn.close()
        for item in self.children: item.disabled = True
        await log_purchase(f"Гравець **{interaction.user}** (<@{interaction.user.id}>) забрав з кейса автомобіль **{self.car_name}** вартістю **{money(self.car_value)} грн.**")
        await interaction.response.edit_message(embed=embed("🚗 Машину забрано", f"**{self.car_name}** додано до твого інвентарю.\n\nПеревір `/inventory` або профіль.", discord.Color.green()), view=self)
        await send_garage_offer(interaction.user.id)

    @discord.ui.button(label="Продати", emoji="💰", style=discord.ButtonStyle.danger)
    async def sell(self, interaction, button):
        if self.done:
            return await interaction.response.send_message("❌ Цю машину вже оброблено.", ephemeral=True)
        self.done = True
        money_add(interaction.user.id, self.car_value)
        for item in self.children: item.disabled = True
        await log_purchase(f"Гравець **{interaction.user}** (<@{interaction.user.id}>) продав з кейса автомобіль **{self.car_name}** за **{money(self.car_value)} грн.**")
        await interaction.response.edit_message(embed=embed("💰 Машину продано", f"**{self.car_name}** продано державі за **{money(self.car_value)}** 💰.", discord.Color.gold()), view=self)


async def open_cases_and_send(interaction: discord.Interaction, rarity: str, quantity: int):
    data = CASE_DATA[rarity]
    results = [roll_case(rarity) for _ in range(quantity)]
    view = BatchCaseResultView(interaction.user.id, rarity, results)
    view.refresh_buttons()
    await interaction.followup.send(
        embed=view.build_embed(),
        view=view,
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
            elif item_type == "business":
                label = f"🏢 {r['item_key']}"
                description = f"Кількість: {r['quantity']} • зробити активним"
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

        if item_type == "business":
            # Only one active business; switching is done here.
            if item_key not in BUSINESS_BY_NAME:
                return await interaction.response.send_message("❌ Невідомий бізнес.", ephemeral=True)
            conn=db()
            conn.execute("UPDATE users SET active_business=? WHERE user_id=?", (item_key,self.user_id))
            conn.execute("UPDATE businesses SET last_paid_at=? WHERE user_id=? AND business_name=?",
                         (datetime.now(timezone.utc).isoformat(),self.user_id,item_key))
            conn.commit(); conn.close()
            await interaction.response.send_message(
                embed=embed("🏢 Активний бізнес змінено",
                    f"Тепер твій активний бізнес: **{item_key}**.\n\n"
                    "Одночасно приносить прибуток лише один бізнес. Інші залишаються в інвентарі.",
                    discord.Color.green()), ephemeral=True)
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
        elif r["item_type"] == "business":
            active = " • 🟢 активний" if get_user(interaction.user.id)["active_business"] == r["item_key"] else ""
            label = f"🏢 **{r['item_key']}** — {r['quantity']} шт. • ⚙️ можна використати{active}"
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
        asyncio.create_task(log_purchase(f"Гравець **{interaction.user}** (<@{interaction.user.id}>) купив нерухомість **{name}** за **{money(price)} грн.**"))
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
        if listing["item_type"] == "car":
            await send_garage_offer(interaction.user.id)

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
        register_successful_command(user_id)
        other_id = row["opponent_id"] if user_id == row["proposer_id"] else row["proposer_id"]
        register_successful_command(other_id)
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
    if message.author.bot:
        return

    # Never run SQLite directly from on_message. This handler fires for every
    # Discord message, so a slow filesystem/SQLite operation here can freeze
    # the entire asyncio event loop and make unrelated slash commands/buttons
    # show "This interaction failed".
    cookie_game = cookie_games.get(message.channel.id)
    if cookie_game and cookie_game["status"] == "playing" and message.author.id in cookie_game["scores"]:
        cookie_game["scores"][message.author.id] += len(message.content)
        await asyncio.to_thread(
            _save_cookie_scores_sync,
            cookie_game["channel_id"],
            cookie_game["scores"][cookie_game["proposer_id"]],
            cookie_game["scores"][cookie_game["opponent_id"]],
        )

    row = await asyncio.to_thread(_get_active_number_game_sync, message.channel.id)
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

def _save_cookie_scores_sync(channel_id: int, proposer_score: int, opponent_score: int) -> None:
    conn = db()
    try:
        conn.execute(
            "UPDATE cookie_games SET proposer_score=?, opponent_score=? WHERE channel_id=?",
            (proposer_score, opponent_score, channel_id),
        )
        conn.commit()
    finally:
        conn.close()


def _get_active_number_game_sync(channel_id: int):
    conn = db()
    try:
        row = conn.execute(
            "SELECT * FROM number_games WHERE channel_id=? AND status='playing'",
            (channel_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------- MASTURBATION ----------------
async def finish_masturbation_session(session_id: int):
    await asyncio.sleep(MASTURBATION_DURATION)
    conn=db()
    try:
        row=conn.execute("SELECT * FROM masturbation_sessions WHERE session_id=? AND status='running'",(session_id,)).fetchone()
        if not row: return
        reward = int(row["reward"]) * level_multiplier(int(get_user(row["user_id"])["level"] or 1))
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(reward,row["user_id"]))
        conn.execute("UPDATE masturbation_sessions SET status='finished', finished_at=? WHERE session_id=?",
                     (datetime.now(timezone.utc).isoformat(),session_id))
        conn.commit()
        register_successful_command(row["user_id"])
        # Completion is public in the same channel where /masturbation was started.
        channel = bot.get_channel(row["channel_id"]) if row["channel_id"] else None
        if channel:
            try:
                await channel.send(embed=embed(
                    "💰 Активність завершена!",
                    f"<@{row['user_id']}> завершив активність та отримав бонус **{money(reward)}** 💰.",
                    discord.Color.green()
                ))
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
            if not get_user(interaction.user.id)["stamina"] and left.total_seconds()>0:
                conn.rollback()
                return await interaction.response.send_message(f"⏳ Наступний раз можна через **{fmt_duration(left)}**.",ephemeral=True)
        now=datetime.now(timezone.utc)
        finishes=now+timedelta(seconds=MASTURBATION_DURATION)
        reward=random.randint(5_000,15_000)
        cur=conn.execute("""INSERT INTO masturbation_sessions(user_id,started_at,finishes_at,reward,status,channel_id)
                            VALUES(?,?,?,?, 'running', ?)""",(interaction.user.id,now.isoformat(),finishes.isoformat(),reward,interaction.channel_id))
        session_id=cur.lastrowid
        conn.commit()
    finally: conn.close()
    asyncio.create_task(finish_masturbation_session(session_id))
    await interaction.response.send_message(embed=embed("⏳ Активність розпочато",
        "Ти почав. Коли завершиш, отримаєш випадковий бонус **від 5 000 до 15 000 💰**.\n\n⏱️ Тривалість: **30 секунд**.\n🔁 Повторити можна **раз на 2 години**.",discord.Color.blurple()),ephemeral=False)



# ============================================================
# BUSINESSES / GARAGES / BANK / LOANS
# ============================================================

BUSINESSES = [
    ("Мережа кав'ярень (Зернятко)", 5_000_000, 18_000),
    ("Спортивний комплекс (Viking)", 8_000_000, 30_000),
    ("Приватна школа (Step School)", 12_000_000, 46_000),
    ("Мережа автомийок самообслуговування (LuxWash)", 15_000_000, 59_000),
    ("IT-академія (IT STEP)", 20_000_000, 81_000),
    ("Мережа кінотеатрів (Планета Кіно)", 25_000_000, 103_000),
    ("Мережа заправок (OKKO)", 30_000_000, 125_000),
    ("Логістичний центр (Укр пошта)", 35_000_000, 148_000),
    ("Приватна лікарня (Добробут)", 45_000_000, 195_000),
    ("Мережа супермаркетів (Сільпо)", 55_000_000, 245_000),
    ("Торговий центр (Епіцентр)", 70_000_000, 320_000),
    ("Служба доставки (Нова Пошта)", 85_000_000, 398_000),
    ("Завод напоїв (Оболонь)", 100_000_000, 480_000),
    ("Міжнародний Аеропорт (Київ)", 125_000_000, 615_000),
    ("Мобільний оператор (Київстар)", 150_000_000, 760_000),
]
BUSINESS_BY_NAME = {x[0]: x for x in BUSINESSES}

GARAGES = {
    "Звичайний": {"price": 50_000, "risk": 0.10, "description": "Публічний гараж у центрі міста"},
    "Середній": {"price": 250_000, "risk": 0.02, "description": "Гараж на підземній парковці"},
    "Надійний": {"price": 1_000_000, "risk": 0.00001, "description": "Гараж на підземній парковці Банку"},
}
GARAGE_OFFER_HOURS = 24
GARAGE_CHECK_INTERVAL = 300  # 5 min; missed hours/days are caught up after restart.
BANK_MIN = 1_000
BANK_MAX = 100_000_000

def bank_rate(amount: int) -> float:
    # 0.1% at 1,000 and 10% at 100,000,000, linearly interpolated.
    amount = max(BANK_MIN, min(BANK_MAX, amount))
    return round(0.1 + (amount - BANK_MIN) * 9.9 / (BANK_MAX - BANK_MIN), 4)

def loan_total(principal: int, rate: float) -> int:
    return int(round(principal * (1 + rate / 100)))

def parse_days(value: str, minimum=1, maximum=MAX_LOAN_DAYS):
    try:
        n = int(str(value).strip())
        if not minimum <= n <= maximum:
            return None
        return n
    except (TypeError, ValueError):
        return None

async def send_log(channel_id: int, message: str, *, color=discord.Color.dark_grey()):
    channel = bot.get_channel(channel_id)
    if channel is None:
        try: channel = await bot.fetch_channel(channel_id)
        except discord.HTTPException: return
    try:
        await channel.send(embed=embed("📋 Лог", message, color))
    except discord.HTTPException:
        pass

async def log_purchase(message: str):
    await send_log(PURCHASE_LOG_CHANNEL_ID, message, color=discord.Color.green())

async def log_system(message: str):
    await send_log(SYSTEM_LOG_CHANNEL_ID, message, color=discord.Color.blurple())

async def log_admin_action(interaction: discord.Interaction, action: str):
    """Dedicated Ukrainian audit log for every successful admin action."""
    actor = interaction.user
    guild_name = interaction.guild.name if interaction.guild else "особисті повідомлення"
    message = (
        f"👮 **Адміністратор:** {actor.mention} (`{actor.id}`)\n"
        f"🛠️ **Дія:** {action}\n"
        f"🏠 **Сервер:** **{discord.utils.escape_markdown(guild_name)}**"
    )
    await send_log(ADMIN_LOG_CHANNEL_ID, message, color=discord.Color.dark_red())

async def safe_dm(user_id: int, *, embed_obj=None, content=None, view=None, retries=3):
    """Send a DM without blocking the event loop and retry transient failures.

    Returns True only when Discord confirms the message was sent.
    """
    user = bot.get_user(user_id)
    if user is None:
        try:
            user = await bot.fetch_user(user_id)
        except (discord.NotFound, discord.Forbidden):
            return False
        except discord.HTTPException as exc:
            print(f"[DM] fetch_user failed for {user_id}: {exc!r}")
            return False

    attempts = max(1, int(retries))
    for attempt in range(attempts):
        try:
            await user.send(content=content, embed=embed_obj, view=view)
            return True
        except discord.Forbidden:
            # User disabled DMs / bot is blocked. Retrying immediately cannot help.
            print(f"[DM] Forbidden for user {user_id} (DMs closed or bot blocked).")
            return False
        except discord.NotFound:
            # User/channel disappeared.
            return False
        except discord.HTTPException as exc:
            # Discord rate limits and transient 5xx errors are worth retrying.
            if attempt >= attempts - 1:
                print(f"[DM] HTTP failure for {user_id}: {exc!r}")
                return False
            retry_after = getattr(exc, "retry_after", None)
            delay = float(retry_after) if retry_after else min(8.0, 1.5 * (2 ** attempt))
            await asyncio.sleep(max(0.5, delay))
        except (asyncio.TimeoutError, TimeoutError) as exc:
            if attempt >= attempts - 1:
                print(f"[DM] Timeout for {user_id}: {exc!r}")
                return False
            await asyncio.sleep(min(8.0, 1.5 * (2 ** attempt)))
        except Exception as exc:
            print(f"[DM] Unexpected failure for {user_id}: {exc!r}")
            return False
    return False

async def send_garage_offer(user_id: int):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row or not row["active_car"] or row["garage_type"]:
        conn.close()
        return False
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=GARAGE_OFFER_HOURS)
    conn.execute("""UPDATE users SET garage_offer_sent_at=?, garage_offer_deadline=?, garage_reminder_at=?
                    WHERE user_id=? AND active_car IS NOT NULL AND garage_type IS NULL
                    AND garage_offer_sent_at IS NULL""",
                 (now.isoformat(), deadline.isoformat(), (now + timedelta(hours=1)).isoformat(), user_id))
    conn.commit()
    conn.close()

    view = GarageOfferView(user_id)
    ok = await safe_dm(user_id, embed_obj=embed(
        "🚗 Захист автомобіля",
        f"У твоєму інвентарі є автомобіль **{row['active_car']}**.\n\n"
        "У тебе є **24 години**, щоб придбати гараж для своєї машини. "
        "Гараж захистить автомобіль, але навіть у ньому існує невеликий ризик викрадення.\n\n"
        "Обери дію нижче.",
        discord.Color.orange()
    ), view=view)
    if not ok:
        conn = db()
        conn.execute("UPDATE users SET garage_offer_sent_at=NULL, garage_offer_deadline=NULL, garage_reminder_at=NULL WHERE user_id=?",
                     (user_id,))
        conn.commit(); conn.close()
    return ok

async def garage_reminder(user_id: int):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row or not row["active_car"] or row["garage_type"]:
        return
    await safe_dm(user_id, embed_obj=embed(
        "⏰ Нагадування про гараж",
        f"Ти ще не придбав гараж для **{row['active_car']}**.\n\n"
        "У тебе все ще є час захистити автомобіль. Відкрий попереднє повідомлення та натисни **«Купити»**.",
        discord.Color.orange()
    ))

class GarageOfferView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=24 * 60 * 60)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Це меню призначене власнику автомобіля.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Купити", emoji="🟢", style=discord.ButtonStyle.success)
    async def buy(self, interaction, button):
        u = get_user(interaction.user.id, interaction.user.name)
        if not u["active_car"]:
            return await interaction.response.send_message("❌ У тебе немає активного автомобіля.", ephemeral=True)
        if u["garage_type"]:
            return await interaction.response.send_message("❌ У тебе вже є гараж.", ephemeral=True)
        deadline = parse_time(u["garage_offer_deadline"])
        if deadline and deadline < datetime.now(timezone.utc):
            return await interaction.response.send_message(
                "❌ 24 години на придбання гаража вже минули.", ephemeral=True)
        await interaction.response.edit_message(
            embed=embed("🏢 Вибір гаража",
                "Обери гараж для свого автомобіля:\n\n"
                "🏠 **Звичайний** — публічний гараж у центрі міста.\n"
                "🅿️ **Середній** — підземна парковка.\n"
                "🏦 **Надійний** — підземна парковка Банку.\n\n"
                "⚠️ Ризик викрадення перевіряється щодня.",
                discord.Color.blurple()),
            view=GarageChoiceView(self.owner_id)
        )

    @discord.ui.button(label="Скасувати", emoji="❌", style=discord.ButtonStyle.secondary)
    async def remind(self, interaction, button):
        conn = db()
        conn.execute("UPDATE users SET garage_reminder_at=NULL WHERE user_id=?", (self.owner_id,))
        conn.commit(); conn.close()
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(
            embed=embed("❌ Пропозицію скасовано",
                        "Добре. Покупку гаража скасовано.\n\n"
                        "Якщо захочеш захистити автомобіль пізніше — скористайся **/garage**.",
                        discord.Color.greyple()),
            view=self
        )

class GarageChoiceView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=600)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Це меню належить іншому гравцю.", ephemeral=True)
            return False
        return True

    async def buy_garage(self, interaction, garage_type):
        u = get_user(interaction.user.id, interaction.user.name)
        data = GARAGES[garage_type]
        if u["garage_type"]:
            return await interaction.response.send_message("❌ У тебе вже є гараж.", ephemeral=True)
        if u["balance"] < data["price"]:
            return await interaction.response.send_message(
                f"❌ Недостатньо грошей. Потрібно **{money(data['price'])}** 💰.", ephemeral=True)
        if not money_add(interaction.user.id, -data["price"]):
            return await interaction.response.send_message("❌ Не вдалося списати кошти.", ephemeral=True)
        now = datetime.now(timezone.utc).isoformat()
        conn = db()
        conn.execute("""UPDATE users SET garage_type=?, garage_purchased_at=?,
                        garage_last_check_at=?, garage_offer_deadline=NULL, garage_reminder_at=NULL
                        WHERE user_id=?""", (garage_type, now, now, interaction.user.id))
        conn.commit(); conn.close()
        asyncio.create_task(log_purchase(f"Гравець **{interaction.user}** (<@{interaction.user.id}>) купив гараж **{garage_type}** за **{money(data['price'])} грн.** для автомобіля **{u['active_car']}**."))
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(
            embed=embed("🅿️ Гараж придбано",
                f"Твій автомобіль **{u['active_car']}** тепер зберігається у гаражі **{garage_type}**.\n\n"
                f"💰 Вартість: **{money(data['price'])}**\n"
                f"🛡️ Шанс викрадення на день: **{data['risk']*100:g}%**",
                discord.Color.green()), view=self)

    @discord.ui.button(label="Звичайний | 50 тис.", emoji="🏠", style=discord.ButtonStyle.secondary)
    async def common(self, interaction, button): await self.buy_garage(interaction, "Звичайний")

    @discord.ui.button(label="Середній | 250 тис.", emoji="🅿️", style=discord.ButtonStyle.primary)
    async def medium(self, interaction, button): await self.buy_garage(interaction, "Середній")

    @discord.ui.button(label="Надійний | 1 мільйон", emoji="🏦", style=discord.ButtonStyle.success)
    async def reliable(self, interaction, button): await self.buy_garage(interaction, "Надійний")

class GarageCommandView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=600)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Це меню доступне лише власнику гаража.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Купити гараж", emoji="🅿️", style=discord.ButtonStyle.success)
    async def buy(self, interaction, button):
        u = get_user(interaction.user.id, interaction.user.name)
        if u["garage_type"]:
            return await interaction.response.send_message("❌ У тебе вже є гараж.", ephemeral=True)
        if not u["active_car"]:
            return await interaction.response.send_message("❌ Спочатку придбай або забери автомобіль.", ephemeral=True)
        await interaction.response.edit_message(
            embed=embed(
                "🏢 Вибір гаража",
                f"🚗 **Автомобіль:** {u['active_car']}\n\n"
                "Гараж захищає автомобіль від викрадення та регулярно перевіряє безпеку.\n\n"
                "🏠 **Звичайний** — 50 000 грн • ризик 10% на день\n"
                "🅿️ **Середній** — 250 000 грн • ризик 2% на день\n"
                "🏦 **Надійний** — 1 000 000 грн • ризик 0,001% на день\n\n"
                "⚠️ Повністю виключити ризик викрадення не може жоден гараж.",
                discord.Color.blurple()
            ),
            view=GarageChoiceView(self.owner_id)
        )

    @discord.ui.button(label="Скасувати", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=embed(
                "❌ Купівлю скасовано",
                "Ти не купив гараж.\n\nКоли захочеш придбати захист для автомобіля, просто введи **/garage**.",
                discord.Color.greyple()
            ),
            view=self
        )


@bot.tree.command(name="garage", description="Купити гараж та захистити свій автомобіль")
async def garage(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    u = get_user(interaction.user.id, interaction.user.name)
    if u["garage_type"]:
        data = GARAGES.get(u["garage_type"], {})
        await interaction.response.send_message(
            embed=embed(
                "🅿️ Твій гараж",
                f"🚗 **Автомобіль:** {u['active_car'] or '—'}\n"
                f"🏢 **Гараж:** {u['garage_type']}\n"
                f"🛡️ **Ризик викрадення:** {(data.get('risk', 0)*100):g}% на день\n\n"
                "Твій автомобіль уже захищений гаражем.",
                discord.Color.green()
            ),
            ephemeral=True
        )
        return
    if not u["active_car"]:
        return await interaction.response.send_message(
            embed=embed(
                "🅿️ Гараж",
                "Щоб придбати гараж, спочатку потрібно мати **активний автомобіль**.\n\n"
                "Після отримання машини ти зможеш повернутися сюди через **/garage**.",
                discord.Color.orange()
            ),
            ephemeral=True
        )
    await interaction.response.send_message(
        embed=embed(
            "🛡️ Захист автомобіля",
            f"🚗 **Твій автомобіль:** {u['active_car']}\n\n"
            "Гараж захищає автомобіль від викрадення. Навіть у гаражі залишається "
            "невеликий ризик, але кращі гаражі значно підвищують безпеку.\n\n"
            "Обери **«Купити гараж»**, щоб переглянути доступні варіанти, "
            "або **«Скасувати»**, якщо поки не хочеш купувати.",
            discord.Color.orange()
        ),
        view=GarageCommandView(interaction.user.id),
        ephemeral=True
    )

async def process_garages():
    now = datetime.now(timezone.utc)
    conn = db()
    users = conn.execute("SELECT * FROM users WHERE active_car IS NOT NULL").fetchall()
    conn.close()
    for u in users:
        if u["garage_type"]:
            data = GARAGES.get(u["garage_type"])
            if not data:
                continue
            # One independent Bernoulli trial for each elapsed UTC calendar day.
            last = u["garage_last_check_at"] or u["garage_purchased_at"] or u["created_at"]
            last_dt = parse_time(last) or now
            days = max(0, (now.date() - last_dt.date()).days)
            if days > 0:
                stolen = False
                for _ in range(days):
                    if random.random() < data["risk"]:
                        stolen = True
                        break
                conn = db()
                conn.execute("UPDATE users SET garage_last_check_at=? WHERE user_id=?",
                             (now.isoformat(), u["user_id"]))
                if stolen:
                    stolen_car = u["active_car"]
                    conn.execute("""UPDATE inventory_items SET quantity=quantity-1
                                    WHERE user_id=? AND item_type='car' AND item_key=? AND quantity>0""",
                                 (u["user_id"], stolen_car))
                    conn.execute("""DELETE FROM inventory_items
                                    WHERE user_id=? AND item_type='car' AND item_key=? AND quantity<=0""",
                                 (u["user_id"], stolen_car))
                    replacement = conn.execute("""SELECT item_key FROM inventory_items
                                                  WHERE user_id=? AND item_type='car' AND quantity>0
                                                  ORDER BY item_key LIMIT 1""",(u["user_id"],)).fetchone()
                    conn.execute("UPDATE users SET active_car=? WHERE user_id=?",
                                 (replacement["item_key"] if replacement else None, u["user_id"]))
                    conn.execute("INSERT INTO garage_events(user_id,event_type,event_at,details) VALUES(?,?,?,?)",
                                 (u["user_id"], "stolen", now.isoformat(), f"Викрадено: {stolen_car}; гараж: {u['garage_type']}"))
                conn.commit(); conn.close()
                if stolen:
                    asyncio.create_task(log_system(f"🚨 Гравець <@{u['user_id']}> втратив автомобіль **{stolen_car}**: спрацював датчик у гаражі **{u['garage_type']}**. Автомобіль видалено з інвентарю."))
                    await safe_dm(u["user_id"], embed_obj=embed(
                        "🚨 Викрадення автомобіля!",
                        "🚨 **Спрацював датчик руху в вашому гаражі!**\n\n"
                        "Вашу машину було викрадено!\n"
                        "Автомобіль видалено з інвентарю та профілю.",
                        discord.Color.red()
                    ))
                    continue
        else:
            # First prompt for cars acquired before/after this update.
            if not u["garage_offer_sent_at"]:
                await send_garage_offer(u["user_id"])
            elif u["garage_reminder_at"] and parse_time(u["garage_reminder_at"]) and parse_time(u["garage_reminder_at"]) <= now:
                deadline = parse_time(u["garage_offer_deadline"])
                if not deadline or now < deadline:
                    await garage_reminder(u["user_id"])
                conn = db()
                conn.execute("UPDATE users SET garage_reminder_at=NULL WHERE user_id=?", (u["user_id"],))
                conn.commit(); conn.close()

def _pay_businesses_sync():
    """Apply accrued business income atomically.

    All SQLite work stays off the Discord event loop. A payout and its
    notification queue entry are committed in the same transaction, so a
    restart cannot lose an earned payout notification.
    """
    now = datetime.now(timezone.utc)
    notifications_created = 0
    conn = db()
    try:
        rows = conn.execute("""
            SELECT b.*, u.active_business
            FROM businesses b
            JOIN users u ON u.user_id=b.user_id
            ORDER BY b.business_id
        """).fetchall()

        for b in rows:
            if b["active_business"] != b["business_name"]:
                continue

            last = parse_time(b["last_paid_at"])
            if not last:
                # Old/corrupt timestamps are repaired without inventing profit.
                conn.execute(
                    "UPDATE businesses SET last_paid_at=? WHERE business_id=?",
                    (now.isoformat(), b["business_id"])
                )
                continue

            seconds = (now - last).total_seconds()
            hours = int(seconds // 3600)
            if hours <= 0:
                continue

            gross = hours * int(b["hourly_profit"])
            tax_percent = max(0, min(15, int(get_state("business_tax", BUSINESS_TAX_DEFAULT))))
            tax = gross * tax_percent // 100
            net = gross - tax
            new_last = last + timedelta(hours=hours)

            # One transaction: money + treasury + payout history + last_paid_at
            # + pending DM are either all saved or none are saved.
            conn.execute("BEGIN IMMEDIATE")
            try:
                if net > 0:
                    cur = conn.execute(
                        "UPDATE users SET balance=balance+? WHERE user_id=?",
                        (net, b["user_id"])
                    )
                    if cur.rowcount != 1:
                        raise RuntimeError(f"user {b['user_id']} disappeared during business payout")

                if tax:
                    cur = conn.execute("""
                        UPDATE president_state
                        SET value=CAST(value AS INTEGER)+?
                        WHERE key='treasury'
                    """, (tax,))
                    if cur.rowcount != 1:
                        raise RuntimeError("treasury state is missing")

                conn.execute(
                    "UPDATE businesses SET last_paid_at=? WHERE business_id=?",
                    (new_last.isoformat(), b["business_id"])
                )
                cur = conn.execute("""
                    INSERT INTO business_payouts(
                        business_id,user_id,gross_amount,tax_amount,net_amount,paid_at
                    ) VALUES(?,?,?,?,?,?)
                """, (
                    b["business_id"], b["user_id"], gross, tax, net, now.isoformat()
                ))
                payout_id = cur.lastrowid

                pref = conn.execute(
                    "SELECT interval_seconds,last_dm_at FROM business_preferences WHERE user_id=?",
                    (b["user_id"],)
                ).fetchone()
                if not pref:
                    conn.execute("""
                        INSERT INTO business_preferences(
                            user_id,interval_seconds,last_dm_at,onboarding_sent
                        ) VALUES(?,?,NULL,1)
                    """, (b["user_id"], 3600))
                    interval = 3600
                    last_dm = None
                else:
                    interval = int(pref["interval_seconds"] or 0)
                    last_dm = parse_time(pref["last_dm_at"])

                # Queue exactly one notification for this interval. The
                # timestamp is claimed in the same transaction as the payout.
                should_notify = (
                    interval > 0 and
                    (last_dm is None or (now - last_dm).total_seconds() >= interval)
                )
                if should_notify:
                    conn.execute("""
                        INSERT INTO business_notifications(
                            payout_id,user_id,business_name,gross_amount,tax_amount,
                            net_amount,hours,created_at,next_attempt_at
                        ) VALUES(?,?,?,?,?,?,?,?,?)
                    """, (
                        payout_id, b["user_id"], b["business_name"], gross, tax,
                        net, hours, now.isoformat(), now.isoformat()
                    ))
                    conn.execute(
                        "UPDATE business_preferences SET last_dm_at=? WHERE user_id=?",
                        (now.isoformat(), b["user_id"])
                    )
                    notifications_created += 1

                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return notifications_created
    finally:
        conn.close()


async def pay_businesses():
    """Run the blocking economy calculation in a worker thread."""
    try:
        return await asyncio.to_thread(_pay_businesses_sync)
    except Exception:
        # Caller logs the exception; never let one bad business kill the loop.
        raise


def _get_pending_business_notifications(limit=10):
    now = datetime.now(timezone.utc).isoformat()
    conn = db()
    try:
        rows = conn.execute("""
            SELECT *
            FROM business_notifications
            WHERE sent_at IS NULL
              AND (next_attempt_at IS NULL OR next_attempt_at<=?)
            ORDER BY notification_id
            LIMIT ?
        """, (now, int(limit))).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _mark_business_notification_result(notification_id, success, error_text=None):
    conn = db()
    try:
        if success:
            conn.execute("""
                UPDATE business_notifications
                SET sent_at=?, last_error=NULL
                WHERE notification_id=? AND sent_at IS NULL
            """, (datetime.now(timezone.utc).isoformat(), notification_id))
        else:
            row = conn.execute(
                "SELECT attempts FROM business_notifications WHERE notification_id=?",
                (notification_id,)
            ).fetchone()
            attempts = int(row["attempts"] if row else 0) + 1
            delay = min(
                BUSINESS_DM_RETRY_MAX_SECONDS,
                BUSINESS_DM_RETRY_BASE_SECONDS * (2 ** min(attempts - 1, 6))
            )
            next_try = datetime.now(timezone.utc) + timedelta(seconds=delay)
            conn.execute("""
                UPDATE business_notifications
                SET attempts=?, last_error=?, next_attempt_at=?
                WHERE notification_id=? AND sent_at IS NULL
            """, (
                attempts, str(error_text or "unknown error")[:1000],
                next_try.isoformat(), notification_id
            ))
        conn.commit()
    finally:
        conn.close()


async def process_business_notification_queue():
    """Reliably deliver queued business DMs with retry/backoff."""
    rows = await asyncio.to_thread(
        _get_pending_business_notifications, BUSINESS_DM_BATCH_SIZE
    )
    for row in rows:
        try:
            ok = await safe_dm(
                row["user_id"],
                embed_obj=embed(
                    "🏢 Прибуток бізнесу",
                    f"**{row['business_name']}** приніс **{money(row['gross_amount'])} грн.** "
                    f"за {row['hours']} год.\n\n"
                    f"🏛️ У казну: **{money(row['tax_amount'])} грн.**\n"
                    f"💰 Тобі: **{money(row['net_amount'])} грн.**",
                    discord.Color.green()
                ),
                retries=3
            )
            await asyncio.to_thread(
                _mark_business_notification_result,
                row["notification_id"], ok,
                None if ok else "Discord DM failed"
            )
            if not ok:
                print(
                    f"[BUSINESS DM] delivery failed: user={row['user_id']} "
                    f"notification={row['notification_id']} attempts={row['attempts'] + 1}"
                )
        except Exception as exc:
            print(
                f"[BUSINESS DM] queue item error: "
                f"user={row['user_id']} notification={row['notification_id']}: {exc!r}"
            )
            try:
                await asyncio.to_thread(
                    _mark_business_notification_result,
                    row["notification_id"], False, repr(exc)
                )
            except Exception as mark_exc:
                print(f"[BUSINESS DM] failed to persist retry state: {mark_exc!r}")

async def process_political_state():
    now=datetime.now(timezone.utc)
    scheduled=get_state("election_scheduled")
    if scheduled and parse_time(scheduled) and parse_time(scheduled)<=now:
        set_state("election_scheduled","")
        await start_election("scheduled")
    conn=db(); active=conn.execute("SELECT election_id,ends_at FROM elections WHERE status='active' ORDER BY election_id DESC LIMIT 1").fetchone(); conn.close()
    if active and parse_time(active["ends_at"])<=now: await finish_election(active["election_id"])
    last=parse_time(get_state("last_election_finished"))
    if not active and (not last or (now-last).total_seconds()>=ELECTION_INTERVAL): await start_election("weekly")

async def economy_loop():
    """Long-running economy worker with independent stages.

    A failure in one stage is isolated. The loop also runs frequently enough
    that hourly payouts/notifications are not dependent on a fragile 5-minute
    timing boundary.
    """
    await asyncio.sleep(3)
    while not bot.is_closed():
        cycle_started = time.monotonic()
        try:
            try:
                await pay_businesses()
            except Exception as exc:
                print(f"[ECONOMY] business payout error: {exc!r}")

            try:
                await process_business_notification_queue()
            except Exception as exc:
                print(f"[ECONOMY] business DM queue error: {exc!r}")

            try:
                await process_garages()
            except Exception as exc:
                print(f"[ECONOMY] garage error: {exc!r}")

            try:
                await process_loans()
            except Exception as exc:
                print(f"[ECONOMY] loan error: {exc!r}")

            try:
                await process_political_state()
            except Exception as exc:
                print(f"[ECONOMY] political-state error: {exc!r}")

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[ECONOMY] unexpected loop error: {exc!r}")

        elapsed = time.monotonic() - cycle_started
        await asyncio.sleep(max(1, ECONOMY_LOOP_SECONDS - elapsed))

class BusinessView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=600)
        self.owner_id = owner_id
        options=[]
        for name, price, hourly in BUSINESSES:
            options.append(discord.SelectOption(
                label=name[:100], description=f"{money(price)} 💰 • +{money(hourly)}/год.", value=name))
        select=discord.ui.Select(placeholder="Обери бізнес для покупки", options=options)
        select.callback=self.buy
        self.add_item(select)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Це меню належить іншому гравцю.", ephemeral=True)
            return False
        return True

    async def buy(self, interaction):
        name=self.children[0].values[0]
        _, price, hourly=BUSINESS_BY_NAME[name]
        u=get_user(interaction.user.id, interaction.user.name)
        if u["balance"] < price:
            return await interaction.response.send_message(
                f"❌ Недостатньо грошей. Потрібно **{money(price)}** 💰.", ephemeral=True)
        if find_inventory_item(interaction.user.id, "business", name):
            return await interaction.response.send_message(
                "❌ Такий бізнес уже є у твоєму інвентарі. Придбати дубль цього бізнесу не можна.",
                ephemeral=True)
        if not money_add(interaction.user.id, -price):
            return await interaction.response.send_message("❌ Не вдалося списати гроші.", ephemeral=True)
        now=datetime.now(timezone.utc).isoformat()
        conn=db()
        conn.execute("""INSERT INTO inventory_items(user_id,item_type,item_key,quantity)
                        VALUES(?,?,?,1) ON CONFLICT(user_id,item_type,item_key)
                        DO UPDATE SET quantity=quantity+1""",
                     (interaction.user.id,"business",name))
        # First business becomes active automatically. Further businesses are inventory only.
        row=conn.execute("SELECT active_business FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()
        if not row["active_business"]:
            conn.execute("UPDATE users SET active_business=? WHERE user_id=?", (name,interaction.user.id))
        conn.execute("INSERT INTO businesses(user_id,business_name,price,hourly_profit,last_paid_at) VALUES(?,?,?,?,?)",
                     (interaction.user.id,name,price,hourly,now))
        conn.commit(); conn.close()
        active = get_user(interaction.user.id)["active_business"]
        msg = (f"🏢 Бізнес **{name}** придбано за **{money(price)}** 💰.\n\n"
               f"💵 Прибуток: **{money(hourly)} грн./год.**\n")
        if active == name:
            msg += "🟢 Він автоматично став твоїм **активним бізнесом**."
        else:
            msg += "ℹ️ **Активний бізнес можна мати лише один.** Цей бізнес додано в `/inventory`; там його можна зробити активним замість поточного."
        await interaction.response.send_message(embed=embed("🏢 Бізнес придбано",msg,discord.Color.green()), ephemeral=True)
        await send_business_preference(interaction.user.id, force=True)
        asyncio.create_task(log_purchase(f"Гравець **{interaction.user}** (<@{interaction.user.id}>) купив бізнес **{name}** за **{money(price)} грн.**. Прибуток: **+{money(hourly)} грн./год.**"))


# ---------------- BUSINESS STATS / NOTIFICATIONS ----------------
BUSINESS_NOTIFICATION_OPTIONS = [("1 год.",3600),("2 год.",7200),("5 год.",18000),("1 день",86400),("Ніколи",0)]

def get_state(key, default=None):
    conn=db(); row=conn.execute("SELECT value FROM president_state WHERE key=?",(key,)).fetchone(); conn.close()
    return row["value"] if row else default

def set_state(key,value):
    conn=db(); conn.execute("INSERT INTO president_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value))); conn.commit(); conn.close()

def get_treasury(): return int(get_state("treasury",10000000))

def add_treasury(amount):
    if amount <= 0: return True
    conn=db(); conn.execute("UPDATE president_state SET value=CAST(value AS INTEGER)+? WHERE key='treasury'",(int(amount),)); conn.commit(); conn.close(); return True

def remove_treasury(amount):
    if amount <= 0: return True
    conn=db(); cur=conn.execute("UPDATE president_state SET value=CAST(value AS INTEGER)-? WHERE key='treasury' AND CAST(value AS INTEGER)>=?",(int(amount),int(amount))); ok=cur.rowcount==1; conn.commit(); conn.close(); return ok

def business_stats(user_id):
    conn=db()
    businesses=conn.execute("SELECT * FROM businesses WHERE user_id=? ORDER BY business_id",(user_id,)).fetchall()
    since=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).isoformat()
    rows=[]
    for b in businesses:
        today=conn.execute("SELECT COALESCE(SUM(net_amount),0) x FROM business_payouts WHERE business_id=? AND paid_at>=?",(b["business_id"],since)).fetchone()["x"]
        total=conn.execute("SELECT COALESCE(SUM(net_amount),0) x FROM business_payouts WHERE business_id=?",(b["business_id"],)).fetchone()["x"]
        rows.append((b,int(b["hourly_profit"]),int(today),int(total)))
    conn.close(); return rows

def business_embed(user_id):
    rows=business_stats(user_id)
    if not rows:
        return embed("🏢 Бізнес", "У тебе ще немає бізнесу. Придбати його можна через `/business`.", discord.Color.red())
    lines=[]
    for b,h,today,total in rows:
        active=" 🟢" if get_user(user_id)["active_business"]==b["business_name"] else ""
        lines.append(f"### 🏢 {b['business_name']}{active}\n💵 Прибуток: **{money(h)} грн/год.**\n📅 Сьогодні: **{money(today)} грн.**\n📈 За весь час: **{money(total)} грн.**")
    tax=int(get_state("business_tax",5))
    return embed("📊 Статистика бізнесу", "\n\n".join(lines)+f"\n\n🏛️ До казни зараз йде **{tax}%** прибутку бізнесів.", discord.Color.gold())

# Persistent business-preference buttons.
# IMPORTANT: Discord component interactions sent from an old message can arrive
# after a bot restart. A normal View stored only in RAM then produces
# "This interaction failed / AFK BOT не відповідає у заданий час".
# These buttons have stable custom_ids and timeout=None, and are re-registered
# for every business owner on every on_ready.
_business_pref_registered: set[int] = set()


def _set_business_preference_sync(user_id: int, seconds: int) -> None:
    conn = db()
    try:
        conn.execute(
            """INSERT INTO business_preferences(user_id,interval_seconds,onboarding_sent)
               VALUES(?,?,1)
               ON CONFLICT(user_id) DO UPDATE SET interval_seconds=?, onboarding_sent=1""",
            (user_id, seconds, seconds),
        )
        conn.commit()
    finally:
        conn.close()


async def send_business_preference(user_id, force=False):
    # All SQLite work is off the Discord event loop. This is critical because
    # an interaction must be acknowledged within Discord's short deadline.
    row = await asyncio.to_thread(_get_business_preference_row, user_id)
    if row and row["onboarding_sent"] and not force:
        return

    await asyncio.to_thread(_set_business_onboarding_sent, user_id)
    view = BusinessPreferenceView(user_id)
    # Register immediately as well as on startup. timeout=None makes the view
    # persistent and prevents it from dying after 24 hours.
    _register_business_preference_view(view)
    ok = await safe_dm(
        user_id,
        content="🏢 У тебе є бізнес! Обери, як часто повідомляти про прибуток:",
        view=view,
    )
    if not ok:
        print(f"[BUSINESS PREF] failed to send preference menu to user={user_id}; it will be retried on next startup/check")


def _get_business_preference_row(user_id: int):
    conn = db()
    try:
        row = conn.execute("SELECT * FROM business_preferences WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _set_business_onboarding_sent(user_id: int) -> None:
    conn = db()
    try:
        conn.execute(
            """INSERT INTO business_preferences(user_id,interval_seconds,onboarding_sent)
               VALUES(?,?,1)
               ON CONFLICT(user_id) DO UPDATE SET onboarding_sent=1""",
            (user_id, 3600),
        )
        conn.commit()
    finally:
        conn.close()


def _register_business_preference_view(view: "BusinessPreferenceView") -> None:
    owner_id = view.owner_id
    if owner_id in _business_pref_registered:
        return
    try:
        bot.add_view(view)
        _business_pref_registered.add(owner_id)
    except (ValueError, RuntimeError) as exc:
        # Duplicate registration is harmless; keep startup resilient.
        print(f"[BUSINESS PREF] view registration warning for user={owner_id}: {exc!r}")


class BusinessPreferenceView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = int(owner_id)
        self._add_button("Раз в 1 год.", discord.ButtonStyle.primary, 3600, "раз в 1 годину")
        self._add_button("Раз в 2 год.", discord.ButtonStyle.primary, 7200, "раз в 2 години")
        self._add_button("Раз в 5 год.", discord.ButtonStyle.primary, 18000, "раз в 5 годин")
        self._add_button("Раз в день", discord.ButtonStyle.primary, 86400, "раз в день")
        self._add_button("Ніколи", discord.ButtonStyle.secondary, 0, "ніколи")

    def _add_button(self, label: str, style: discord.ButtonStyle, seconds: int, text: str):
        button = discord.ui.Button(
            label=label,
            style=style,
            custom_id=f"business_pref:{self.owner_id}:{seconds}",
        )

        async def callback(interaction: discord.Interaction):
            await self.choose(interaction, seconds, text)

        button.callback = callback
        self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Це меню належить іншому гравцю.", ephemeral=True
                )
            return False
        return True

    async def choose(self, interaction: discord.Interaction, seconds: int, label: str):
        # ACK FIRST. Never perform SQLite/network work before Discord receives
        # the interaction acknowledgement. This directly fixes intermittent
        # "AFK BOT не відповідає у заданий час" component failures.
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except discord.HTTPException as exc:
            print(f"[BUSINESS PREF] defer failed user={interaction.user.id}: {exc!r}")
            return

        try:
            await asyncio.to_thread(_set_business_preference_sync, self.owner_id, int(seconds))
            await interaction.edit_original_response(
                content=f"✅ Повідомлення про прибуток: **{label}**.",
                view=None,
            )
        except sqlite3.Error as exc:
            print(f"[BUSINESS PREF] database error user={self.owner_id}: {exc!r}")
            try:
                await interaction.edit_original_response(
                    content="❌ Не вдалося зберегти налаштування. Спробуй натиснути кнопку ще раз.",
                    view=self,
                )
            except Exception as response_exc:
                print(f"[BUSINESS PREF] DB error response failed: {response_exc!r}")
        except discord.HTTPException as exc:
            print(f"[BUSINESS PREF] Discord response error user={self.owner_id}: {exc!r}")
        except Exception as exc:
            print(f"[BUSINESS PREF] unexpected error user={self.owner_id}: {exc!r}")
            try:
                await interaction.edit_original_response(
                    content="❌ Сталася тимчасова помилка. Спробуй ще раз.",
                    view=self,
                )
            except Exception as response_exc:
                print(f"[BUSINESS PREF] fallback response failed: {response_exc!r}")

class BizShareModal(discord.ui.Modal,title="Поділитися бізнесом"):
    user_id=discord.ui.TextInput(label="Discord ID гравця",placeholder="123456789012345678")
    async def on_submit(self,interaction):
        try: uid=int(str(self.user_id.value).strip())
        except ValueError: return await interaction.response.send_message("❌ Невірний Discord ID.",ephemeral=True)
        target=interaction.guild.get_member(uid) if interaction.guild else bot.get_user(uid)
        if not target: target=await bot.fetch_user(uid)
        if not target or target.id==interaction.user.id: return await interaction.response.send_message("❌ Не вдалося знайти іншого гравця.",ephemeral=True)
        await safe_dm(target.id,embed_obj=embed("📊 Статистика бізнесу",f"<@{interaction.user.id}> поділився з вами статистикою свого бізнеса.",discord.Color.blurple()))
        await safe_dm(target.id,embed_obj=business_embed(interaction.user.id))
        await interaction.response.send_message(f"✅ Статистику надіслано <@{target.id}>.",ephemeral=True)

class BizView(discord.ui.View):
    def __init__(self,owner_id): super().__init__(timeout=300); self.owner_id=owner_id
    async def interaction_check(self,interaction):
        if interaction.user.id!=self.owner_id: await interaction.response.send_message("❌ Це меню належить іншому гравцю.",ephemeral=True); return False
        return True
    @discord.ui.button(label="Закрити",style=discord.ButtonStyle.secondary)
    async def close(self,interaction,button): await interaction.response.edit_message(content="📊 Статистику закрито.",embed=None,view=None)
    @discord.ui.button(label="Поділитися",style=discord.ButtonStyle.success)
    async def share(self,interaction,button): await interaction.response.send_modal(BizShareModal())

@bot.tree.command(name="biz",description="Статистика твого бізнесу")
async def biz(interaction: discord.Interaction):
    await interaction.response.send_message(embed=business_embed(interaction.user.id),view=BizView(interaction.user.id),ephemeral=True)

# ---------------- TREASURY / PRESIDENT ----------------
class AmountModal(discord.ui.Modal,title="Сума"):
    amount=discord.ui.TextInput(label="Сума",placeholder="100000")
    def __init__(self,mode): super().__init__(); self.mode=mode
    async def on_submit(self,interaction):
        try: amount=int(str(self.amount.value).replace(" ","").replace(",","")); assert amount>0
        except (ValueError,AssertionError): return await interaction.response.send_message("❌ Невірна сума.",ephemeral=True)
        if self.mode=="deposit":
            if not money_add(interaction.user.id,-amount): return await interaction.response.send_message("❌ Недостатньо грошей.",ephemeral=True)
            add_treasury(amount); await interaction.response.send_message(f"✅ Ти вклав **{money(amount)} грн.** у казну.",ephemeral=True)
        elif self.mode=="withdraw":
            if not remove_treasury(amount): return await interaction.response.send_message("❌ У казні недостатньо грошей.",ephemeral=True)
            money_add(interaction.user.id,amount); await interaction.response.send_message(f"✅ Отримано з казни **{money(amount)} грн.**.",ephemeral=True)

@bot.tree.command(name="kazna",description="Казна сервера та внесення грошей")
async def kazna(interaction):
    class V(discord.ui.View):
        def __init__(self): super().__init__(timeout=300)
        @discord.ui.button(label="Вкласти гроші",style=discord.ButtonStyle.success)
        async def dep(self,i,b): await i.response.send_modal(AmountModal("deposit"))
    await interaction.response.send_message(embed=embed("🏛️ Казна",f"У казні: **{money(get_treasury())} грн.**\nПодаток з бізнесів: **{int(get_state('business_tax',5))}%**.",discord.Color.gold()),view=V(),ephemeral=True)

def current_president():
    value=get_state("president")
    return int(value) if value and value.isdigit() else None

async def start_election(reason="weekly"):
    conn=db(); active=conn.execute("SELECT * FROM elections WHERE status='active' AND ends_at>?",(datetime.now(timezone.utc).isoformat(),)).fetchone()
    if active: conn.close(); return
    now=datetime.now(timezone.utc); end=now+timedelta(seconds=ELECTION_DURATION)
    cur=conn.execute("INSERT INTO elections(started_at,ends_at,channel_id,status) VALUES(?,?,?, 'active')",(now.isoformat(),end.isoformat(),NORMAL_CHANNEL_ID)); eid=cur.lastrowid
    conn.commit(); conn.close()
    guild=bot.get_guild(GUILD_ID) if GUILD_ID else None
    if guild:
        ch=guild.get_channel(NORMAL_CHANNEL_ID)
        if ch:
            view=ElectionView(eid)
            msg=await ch.send(embed=embed("🇺🇦 Вибори президента", "Протягом **24 годин** обери кандидата кнопкою нижче. За себе голосувати не можна.",discord.Color.gold()),view=view)
            conn=db(); conn.execute("UPDATE elections SET message_id=? WHERE election_id=?",(msg.id,eid)); conn.commit(); conn.close()
        for m in guild.members:
            if not m.bot: await safe_dm(m.id,content="🇺🇦 На сервері розпочалися вибори президента. Обрати кандидата можна у каналі сервера.")

class ElectionView(discord.ui.View):
    def __init__(self,election_id): super().__init__(timeout=ELECTION_DURATION); self.election_id=election_id
    @discord.ui.button(label="Проголосувати",emoji="🗳️",style=discord.ButtonStyle.primary)
    async def vote(self,interaction,button):
        if not interaction.guild: return await interaction.response.send_message("❌ Голосувати можна лише на сервері.",ephemeral=True)
        conn=db(); e=conn.execute("SELECT * FROM elections WHERE election_id=? AND status='active'",(self.election_id,)).fetchone(); conn.close()
        if not e: return await interaction.response.send_message("❌ Вибори вже завершені.",ephemeral=True)
        select=discord.ui.UserSelect(placeholder="Оберіть кандидата",min_values=1,max_values=1)
        class V(discord.ui.View):
            def __init__(self): super().__init__(timeout=120); self.add_item(select)
        v=V()
        async def cb(i):
            cand=select.values[0]
            if cand.bot: return await i.response.send_message("❌ За ботів голосувати не можна.",ephemeral=True)
            if cand.id==i.user.id: return await i.response.send_message("❌ За себе голосувати не можна.",ephemeral=True)
            conn=db(); conn.execute("INSERT OR REPLACE INTO election_votes(election_id,voter_id,candidate_id,voted_at) VALUES(?,?,?,?)",(self.election_id,i.user.id,cand.id,datetime.now(timezone.utc).isoformat())); conn.commit(); conn.close()
            await i.response.edit_message(content=f"✅ Твій голос віддано за {cand.mention}.",view=None)
        select.callback=cb
        await interaction.response.send_message("Обери кандидата:",view=v,ephemeral=True)

async def finish_election(election_id):
    conn=db(); e=conn.execute("SELECT * FROM elections WHERE election_id=? AND status='active'",(election_id,)).fetchone()
    if not e: conn.close(); return
    now=datetime.now(timezone.utc)
    if parse_time(e["ends_at"])>now: conn.close(); return
    winner=conn.execute("SELECT candidate_id,COUNT(*) c FROM election_votes WHERE election_id=? GROUP BY candidate_id ORDER BY c DESC,candidate_id ASC LIMIT 1",(election_id,)).fetchone()
    set_state("last_election_finished",now.isoformat())
    if winner:
        set_state("president",str(winner["candidate_id"]))
        set_state("president_started",now.isoformat())
    conn.execute("UPDATE elections SET status='finished',winner_id=? WHERE election_id=?",(winner["candidate_id"] if winner else None,election_id)); conn.commit(); conn.close()
    if winner:
        await safe_dm(winner["candidate_id"],content="🇺🇦 Вітаємо! Ви стали президентом сервера.")
        guild=bot.get_guild(GUILD_ID) if GUILD_ID else None
        if guild:
            for m in guild.members:
                if not m.bot and m.id!=winner["candidate_id"]: await safe_dm(m.id,content=f"🇺🇦 Президентом сервера став <@{winner['candidate_id']}>.")

@bot.tree.command(name="prezident_vuboru",description="🔒 Запустити вибори президента через вказаний час (години)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(time="Через скільки годин розпочати вибори")
async def prezident_vuboru(interaction,time:app_commands.Range[int,0,168]):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    if time==0: await start_election("admin"); return await interaction.response.send_message("✅ Вибори запущено.",ephemeral=True)
    set_state("election_scheduled",(datetime.now(timezone.utc)+timedelta(hours=time)).isoformat())
    await interaction.response.send_message(f"✅ Вибори заплановано через **{time} год.**",ephemeral=True)

class UkraineView(discord.ui.View):
    def __init__(self,owner_id): super().__init__(timeout=600); self.owner_id=owner_id
    async def interaction_check(self,i):
        if i.user.id!=self.owner_id: await i.response.send_message("❌ Меню президента доступне лише президенту.",ephemeral=True); return False
        return True
    @discord.ui.button(label="Взяти з казни",style=discord.ButtonStyle.danger)
    async def take(self,i,b): await i.response.send_modal(AmountModal("withdraw"))
    @discord.ui.button(label="Покласти в казну",style=discord.ButtonStyle.success)
    async def put(self,i,b): await i.response.send_modal(AmountModal("deposit"))
    @discord.ui.button(label="Видати всім",style=discord.ButtonStyle.primary)
    async def give(self,i,b): await i.response.send_modal(PresidentGiveAllModal())
    @discord.ui.button(label="Новина жителям",style=discord.ButtonStyle.primary)
    async def news(self,i,b): await i.response.send_modal(PresidentNewsModal())
    @discord.ui.button(label="Змінити податок",style=discord.ButtonStyle.secondary)
    async def tax(self,i,b): await i.response.send_modal(PresidentTaxModal())

class PresidentGiveAllModal(discord.ui.Modal,title="Видати всім"):
    amount=discord.ui.TextInput(label="Сума кожному",placeholder="10000")
    async def on_submit(self,i):
        try: amount=int(str(self.amount.value)); assert amount>0
        except (ValueError,AssertionError): return await i.response.send_message("❌ Невірна сума.",ephemeral=True)
        guild=i.guild; users=[m for m in guild.members if not m.bot]
        total=amount*len(users)
        if not remove_treasury(total): return await i.response.send_message(f"❌ У казні недостатньо. Потрібно {money(total)} грн.",ephemeral=True)
        for m in users: money_add(m.id,amount)
        await i.response.send_message(f"✅ Видано **{money(amount)} грн.** кожному з {len(users)} жителів.",ephemeral=True)

class PresidentNewsModal(discord.ui.Modal,title="Новина президента"):
    text=discord.ui.TextInput(label="Текст",style=discord.TextStyle.paragraph,max_length=2000)
    async def on_submit(self,i):
        last=parse_time(get_state("president_news_at")); now=datetime.now(timezone.utc)
        if last and (now-last).total_seconds()<PRESIDENT_NEWS_COOLDOWN: return await i.response.send_message("⏳ Новину можна оголошувати раз на 2 години.",ephemeral=True)
        set_state("president_news_at",now.isoformat())
        for m in i.guild.members:
            if not m.bot and m.id!=i.user.id: await safe_dm(m.id,content=f"🇺🇦 **Новина від президента <@{i.user.id}>**\n\n{self.text.value}")
        await i.response.send_message("✅ Новину надіслано жителям у ЛС.",ephemeral=True)

class PresidentTaxModal(discord.ui.Modal,title="Податок бізнесу"):
    percent=discord.ui.TextInput(label="Відсоток 0-15",placeholder="5")
    async def on_submit(self,i):
        try: p=int(str(self.percent.value)); assert 0<=p<=15
        except (ValueError,AssertionError): return await i.response.send_message("❌ Вкажи число від 0 до 15.",ephemeral=True)
        set_state("business_tax",p); await i.response.send_message(f"✅ Податок бізнесів встановлено: **{p}%**.",ephemeral=True)

@bot.tree.command(name="ukraine",description="Меню керування країною президента")
async def ukraine(interaction):
    if current_president()!=interaction.user.id: return await interaction.response.send_message("❌ Ти не президент.",ephemeral=True)
    await interaction.response.send_message(embed=embed("🇺🇦 Україна",f"Президент: <@{interaction.user.id}>\n🏛️ Казна: **{money(get_treasury())} грн.**\n📊 Податок бізнесу: **{int(get_state('business_tax',5))}%**",discord.Color.gold()),view=UkraineView(interaction.user.id),ephemeral=True)

ROBBERY_COOLDOWN_SECONDS = 2 * 60 * 60
ROBBERY_MIN_BALANCE_RATIO = 0.15

@bot.tree.command(name="robbery",description="50/50 пограбувати іншого гравця")
@app_commands.describe(user="Кого пограбувати")
async def robbery(interaction,user:discord.Member):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if user.bot or user.id==interaction.user.id:
        return await interaction.response.send_message("❌ Обери іншого гравця.",ephemeral=True)

    victim=get_user(user.id)
    robber=get_user(interaction.user.id)
    robber_balance=int(robber["balance"] or 0)
    victim_balance=int(victim["balance"] or 0)

    if victim_balance <= 0:
        return await interaction.response.send_message("❌ У цього гравця немає грошей для пограбування.",ephemeral=True)

    required_balance=max(1, int(victim_balance * ROBBERY_MIN_BALANCE_RATIO))
    if robber_balance < required_balance:
        return await interaction.response.send_message(
            f"❌ Для пограбування потрібно мати щонайменше **15%** від балансу жертви.\n"
            f"💰 У жертви: **{money(victim_balance)} грн.**\n"
            f"💳 Тобі потрібно: **{money(required_balance)} грн.**, а в тебе **{money(robber_balance)} грн.**.",
            ephemeral=True,
        )

    # Cooldown is persisted in SQLite, so restarting the bot does not reset it.
    now=datetime.now(timezone.utc)
    last_raw=robber["robbery_at"]
    if last_raw:
        try:
            last=datetime.fromisoformat(str(last_raw).replace("Z","+00:00"))
            if last.tzinfo is None: last=last.replace(tzinfo=timezone.utc)
            remaining=ROBBERY_COOLDOWN_SECONDS-(now-last).total_seconds()
            if remaining>0:
                hours=int(remaining//3600); minutes=int((remaining%3600)//60); seconds=int(remaining%60)
                return await interaction.response.send_message(
                    f"⏳ Пограбування ще на кулдауні. Спробуй через **{hours} год. {minutes} хв. {seconds} сек.**.",
                    ephemeral=True,
                )
        except (ValueError,TypeError):
            pass

    conn=db()
    conn.execute("UPDATE users SET robbery_at=? WHERE user_id=?",(now.isoformat(),interaction.user.id))
    conn.commit(); conn.close()

    if random.random()<0.5:
        amount=victim_balance
        if amount>0:
            money_add(user.id,-amount); money_add(interaction.user.id,amount)
        register_successful_command(interaction.user.id)
        await interaction.response.send_message(f"💰 {interaction.user.mention} повністю пограбував {user.mention} і забрав **{money(amount)} грн.**!")
    else:
        lost=robber_balance
        if lost>0:
            money_add(interaction.user.id,-lost); add_treasury(lost)
        register_successful_command(interaction.user.id)
        await interaction.response.send_message(f"🚨 {interaction.user.mention} не зміг пограбувати {user.mention} і втратив **{money(lost)} грн.** — гроші пішли в казну.")

class MotionView(discord.ui.View):
    def __init__(self,motion_id): super().__init__(timeout=86400); self.motion_id=motion_id
    @discord.ui.button(label="За!",style=discord.ButtonStyle.danger)
    async def yes(self,i,b):
        if i.user.id==current_president(): return await i.response.send_message("❌ Президент не може голосувати за своє зняття.",ephemeral=True)
        conn=db(); conn.execute("INSERT OR IGNORE INTO president_motion_votes(motion_id,voter_id,voted_at) VALUES(?,?,?)",(self.motion_id,i.user.id,datetime.now(timezone.utc).isoformat())); count=conn.execute("SELECT COUNT(*) c FROM president_motion_votes WHERE motion_id=?",(self.motion_id,)).fetchone()["c"]; conn.commit(); conn.close()
        if count>=2:
            old=current_president(); set_state("president",""); conn=db(); conn.execute("UPDATE president_motions SET status='passed' WHERE motion_id=?",(self.motion_id,)); conn.commit(); conn.close()
            if old: await safe_dm(old,content="🇺🇦 Вас зняли з посади президента мітингом.")
            await start_election("motion")
            return await i.response.edit_message(content="🇺🇦 Мітинг успішний! Президент знятий, розпочалися нові вибори.",view=None)
        await i.response.send_message(f"✅ Голос зараховано. Потрібно ще **{2-count}** голос(и).",ephemeral=True)

@bot.tree.command(name="mitung",description="Ініціювати мітинг за зняття президента")
async def mitung(interaction):
    if not current_president(): return await interaction.response.send_message("❌ Зараз немає президента.",ephemeral=True)
    conn=db(); active=conn.execute("SELECT * FROM president_motions WHERE status='active' LIMIT 1").fetchone()
    if active: conn.close(); return await interaction.response.send_message("⚠️ Мітинг уже триває.",ephemeral=True)
    cur=conn.execute("INSERT INTO president_motions(president_id,started_at) VALUES(?,?)",(current_president(),datetime.now(timezone.utc).isoformat())); mid=cur.lastrowid; conn.commit(); conn.close()
    await interaction.response.send_message(embed=embed("📢 Мітинг",f"<@{interaction.user.id}> ініціював мітинг за зняття президента <@{current_president()}>. Потрібно **2 голоси «За!»**.",discord.Color.red()),view=MotionView(mid))

@bot.tree.command(name="business", description="Купити бізнес")
async def business(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    lines=[f"{i}. **{n}** — {money(p)} 💰 • +{money(h)}/год. (~{money(h*24)}/день)" for i,(n,p,h) in enumerate(BUSINESSES,1)]
    await interaction.response.send_message(
        embed=embed("🏢 Бізнес-центр", "Обери бізнес, який хочеш придбати:\n\n"+"\n".join(lines)+
                    "\n\n🟢 Активним одночасно може бути лише **один** бізнес. Інші зберігаються в `/inventory`.",discord.Color.gold()),
        view=BusinessView(interaction.user.id), ephemeral=False)

class BankMainView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=600)
        self.owner_id=owner_id
    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Це банківське меню відкрив інший гравець.", ephemeral=True)
            return False
        return True
    @discord.ui.button(label="Оформити кредит", emoji="💳", style=discord.ButtonStyle.success, row=0)
    async def take_bank(self, interaction, button): await interaction.response.send_modal(BankLoanModal())
    @discord.ui.button(label="Погасити кредит", emoji="💰", style=discord.ButtonStyle.primary, row=0)
    async def repay(self, interaction, button): await show_repay_menu(interaction)
    @discord.ui.button(label="Кредити", emoji="📋", style=discord.ButtonStyle.secondary, row=0)
    async def credits(self, interaction, button): await show_loans(interaction)
    @discord.ui.button(label="Взяти у кредит від гравця", emoji="🤝", style=discord.ButtonStyle.primary, row=1)
    async def borrow_player(self, interaction, button): await interaction.response.send_modal(PlayerBorrowModal())
    @discord.ui.button(label="Запропонувати в кредит гравцю", emoji="💼", style=discord.ButtonStyle.success, row=1)
    async def lend_player(self, interaction, button): await interaction.response.send_modal(PlayerLendModal())

class BankLoanModal(discord.ui.Modal, title="Оформлення кредиту"):
    amount=discord.ui.TextInput(label="Введіть суму кредиту", placeholder="Наприклад: 10000", min_length=4, max_length=12)
    days=discord.ui.TextInput(label="Через скільки днів погасити кредит?", placeholder="Наприклад: 10", min_length=1, max_length=3)
    async def on_submit(self, interaction):
        if get_user(interaction.user.id)["bank_banned"]:
            return await interaction.response.send_message("❌ Тобі більше недоступне кредитування банку.", ephemeral=True)
        try: amount=int(str(self.amount.value).replace(" ","")); assert BANK_MIN<=amount<=BANK_MAX
        except (ValueError,AssertionError): return await interaction.response.send_message("❌ Сума має бути від 1 000 до 100 000 000 грн.", ephemeral=True)
        days=parse_days(self.days.value,1,MAX_LOAN_DAYS)
        if days is None: return await interaction.response.send_message("❌ Кількість днів: від 1 до 10.", ephemeral=True)
        rate=bank_rate(amount); total=loan_total(amount,rate)
        await interaction.response.send_message(
            embed=embed("💳 Підтвердження кредиту",
                f"Ти впевнений, що береш кредит **{money(amount)} грн.** на **{days} дн.**?\n\n"
                f"📈 Відсоток: **{rate:.4f}%**\n"
                f"💰 До погашення: **{money(total)} грн.**\n"
                f"📅 Дата погашення: <t:{int((datetime.now(timezone.utc)+timedelta(days=days)).timestamp())}:F>",
                discord.Color.gold()), view=BankConfirmView(interaction.user.id,amount,rate,days), ephemeral=True)

class BankConfirmView(discord.ui.View):
    def __init__(self,user_id,amount,rate,days):
        super().__init__(timeout=300); self.user_id=user_id; self.amount=amount; self.rate=rate; self.days=days; self.done=False
    async def interaction_check(self,interaction):
        if interaction.user.id!=self.user_id:
            await interaction.response.send_message("❌ Це підтвердження належить іншому гравцю.",ephemeral=True); return False
        return True
    @discord.ui.button(label="Підтвердити",emoji="✅",style=discord.ButtonStyle.success)
    async def yes(self,interaction,button):
        if self.done: return
        self.done=True
        if get_user(self.user_id)["bank_banned"]:
            return await interaction.response.send_message("❌ Банк більше не кредитує тебе.",ephemeral=True)
        due=datetime.now(timezone.utc)+timedelta(days=self.days)
        total=loan_total(self.amount,self.rate)
        conn=db()
        # Only one active bank/player loan at a time per borrower.
        exists=conn.execute("SELECT 1 FROM loans WHERE borrower_id=? AND status IN ('active','grace')",(self.user_id,)).fetchone()
        if exists:
            conn.close(); return await interaction.response.send_message("❌ У тебе вже є непогашений кредит.",ephemeral=True)
        conn.execute("""INSERT INTO loans(lender_id,borrower_id,principal,rate,total_due,created_at,due_at,status)
                        VALUES(0,?,?,?,?,?,?, 'active')""",
                     (self.user_id,self.amount,self.rate,total,datetime.now(timezone.utc).isoformat(),due.isoformat()))
        conn.commit(); conn.close()
        money_add(self.user_id,self.amount)
        due_ts = int(due.timestamp())
        await interaction.response.edit_message(embed=embed("💳 Кредит оформлено",
            f"Банк зарахував **{money(self.amount)} грн.** на твій баланс.\n\n"
            f"До погашення: **{money(total)} грн.** ({self.rate:.4f}%).\n"
            f"Термін: **{self.days} дн.**\n"
            f"📅 Погасити до: <t:{due_ts}:F>\n\n"
            "Дострокове погашення доступне через `/bank` → **Погасити кредит**.",discord.Color.green()),view=None)
        await safe_dm(self.user_id, embed_obj=embed(
            "🏦 Банк схвалив кредит",
            f"Банк схвалив тобі кредит на **{money(self.amount)} грн.** 💰\n\n"
            f"📈 Відсоток: **{self.rate:.4f}%**\n"
            f"📅 Термін: **{self.days} дн.**\n"
            f"💵 До погашення: **{money(total)} грн.**\n"
            f"🗓️ Погасити до: <t:{due_ts}:F>\n\n"
            "Можеш погасити його достроково через `/bank`.", discord.Color.green()))
    @discord.ui.button(label="Відмовитись",emoji="❌",style=discord.ButtonStyle.danger)
    async def no(self,interaction,button):
        self.done=True
        await interaction.response.edit_message(content="❌ Кредит скасовано.",embed=None,view=None)

async def show_loans(interaction):
    conn=db()
    rows=conn.execute("SELECT * FROM loans WHERE status IN ('active','grace') ORDER BY due_at ASC").fetchall()
    conn.close()
    if not rows: text="Наразі активних кредитів немає."
    else:
        lines=[]
        for r in rows:
            lender="🏦 Банк" if r["lender_id"]==0 else f"<@{r['lender_id']}>"
            lines.append(f"• <@{r['borrower_id']}> ← {lender} — **{money(r['principal'])} грн.** • **{r['rate']:.4f}%** • до <t:{int(datetime.fromisoformat(r['due_at']).timestamp())}:R>")
        text="\n".join(lines)
    await interaction.response.send_message(embed=embed("📋 Активні кредити",text,discord.Color.blurple()),ephemeral=False)

async def show_repay_menu(interaction):
    conn=db()
    rows=conn.execute("SELECT * FROM loans WHERE borrower_id=? AND status IN ('active','grace') ORDER BY due_at",(interaction.user.id,)).fetchall()
    conn.close()
    if not rows: return await interaction.response.send_message("❌ У тебе немає активних кредитів.",ephemeral=True)
    options=[discord.SelectOption(label=f"{money(r['total_due'])} грн. — {('банк' if r['lender_id']==0 else 'гравець')}",value=str(r["loan_id"])) for r in rows[:25]]
    v=RepaySelectView(interaction.user.id,options)
    await interaction.response.send_message(embed=embed("💰 Погашення кредиту","Обери кредит, який хочеш погасити.",discord.Color.gold()),view=v,ephemeral=True)

class RepaySelectView(discord.ui.View):
    def __init__(self,owner_id,options):
        super().__init__(timeout=300); self.owner_id=owner_id
        select=discord.ui.Select(placeholder="Обери кредит",options=options); select.callback=self.select; self.add_item(select)
    async def interaction_check(self,interaction):
        if interaction.user.id!=self.owner_id:
            await interaction.response.send_message("❌ Це меню не для тебе.",ephemeral=True); return False
        return True
    async def select(self,interaction):
        loan_id=int(self.children[0].values[0])
        conn=db(); loan=conn.execute("SELECT * FROM loans WHERE loan_id=? AND borrower_id=? AND status IN ('active','grace')",(loan_id,self.owner_id)).fetchone(); conn.close()
        if not loan: return await interaction.response.send_message("❌ Кредит уже закрито.",ephemeral=True)
        await interaction.response.send_message(embed=embed("💰 Підтвердження погашення",
            f"Точно погасити кредит на **{money(loan['total_due'])} грн.**?\n"
            f"📈 Відсоток: **{loan['rate']:.4f}%**",discord.Color.gold()),view=RepayConfirmView(self.owner_id,loan_id),ephemeral=True)

class RepayConfirmView(discord.ui.View):
    def __init__(self,owner_id,loan_id):
        super().__init__(timeout=300); self.owner_id=owner_id; self.loan_id=loan_id
    async def interaction_check(self,interaction):
        if interaction.user.id!=self.owner_id:
            await interaction.response.send_message("❌ Це меню не для тебе.",ephemeral=True); return False
        return True
    @discord.ui.button(label="Погасити",emoji="💚",style=discord.ButtonStyle.success)
    async def repay(self,interaction,button):
        conn=db()
        loan=conn.execute("SELECT * FROM loans WHERE loan_id=? AND borrower_id=? AND status IN ('active','grace')",(self.loan_id,self.owner_id)).fetchone()
        if not loan:
            conn.close(); return await interaction.response.send_message("❌ Кредит уже закрито.",ephemeral=True)
        u=conn.execute("SELECT balance FROM users WHERE user_id=?",(self.owner_id,)).fetchone()
        if not u or u["balance"]<loan["total_due"]:
            conn.close(); return await interaction.response.send_message(f"❌ Недостатньо коштів. Потрібно **{money(loan['total_due'])} грн.**",ephemeral=True)
        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?",(loan["total_due"],self.owner_id))
        if loan["lender_id"] != 0:
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(loan["total_due"],loan["lender_id"]))
        conn.execute("UPDATE loans SET status='paid',closed_at=? WHERE loan_id=?",(datetime.now(timezone.utc).isoformat(),self.loan_id))
        conn.commit(); conn.close()
        await interaction.response.edit_message(embed=embed("✅ Кредит погашено","Дякуємо за співпрацю! Кредит успішно погашено.",discord.Color.green()),view=None)
    @discord.ui.button(label="Відмовитись",emoji="❌",style=discord.ButtonStyle.danger)
    async def cancel(self,interaction,button):
        await interaction.response.edit_message(content="❌ Погашення скасовано.",embed=None,view=None)

async def process_loans():
    now=datetime.now(timezone.utc)
    conn=db()
    due=conn.execute("SELECT * FROM loans WHERE status='active' AND due_at<=?",(now.isoformat(),)).fetchall()
    for loan in due:
        grace=now+timedelta(hours=24)
        conn.execute("UPDATE loans SET status='grace',grace_until=?,due_notice_sent_at=? WHERE loan_id=?",
                     (grace.isoformat(),now.isoformat(),loan["loan_id"]))
        # Notice is sent after commit below.
    conn.commit(); conn.close()
    for loan in due:
        await safe_dm(loan["borrower_id"],embed_obj=embed(
            "⏰ Час погашення кредиту настав!",
            f"У тебе є **24 год.** щоб погасити кредит на суму **{money(loan['total_due'])} грн.**\n\n"
            "Натисни **«Погасити»** у цьому повідомленні або скористайся `/bank` → «Погасити кредит».",
            discord.Color.orange()),view=LoanDueView(loan["borrower_id"],loan["loan_id"]))
    conn=db()
    reminders=conn.execute("SELECT * FROM loans WHERE status='grace' AND reminder_at IS NOT NULL AND reminder_at<=?",(now.isoformat(),)).fetchall()
    conn.execute("UPDATE loans SET reminder_at=NULL WHERE status='grace' AND reminder_at IS NOT NULL AND reminder_at<=?", (now.isoformat(),))
    expired=conn.execute("SELECT * FROM loans WHERE status='grace' AND grace_until<=?",(now.isoformat(),)).fetchall()
    for loan in expired:
        u=conn.execute("SELECT balance FROM users WHERE user_id=?",(loan["borrower_id"],)).fetchone()
        bal = u["balance"] if u else 0
        if bal >= loan["total_due"]:
            conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?",(loan["total_due"],loan["borrower_id"]))
            if loan["lender_id"] != 0:
                conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(loan["total_due"],loan["lender_id"]))
            reason="Сума боргу автоматично списана з твого балансу."
            status="paid"
        else:
            # For a bank loan the bank takes the remaining available balance and
            # permanently blocks future bank credit. Player loans are only
            # reported to the lender when funds are insufficient.
            if loan["lender_id"] == 0:
                if bal > 0:
                    conn.execute("UPDATE users SET balance=0 WHERE user_id=?",(loan["borrower_id"],))
                conn.execute("UPDATE users SET bank_banned=1 WHERE user_id=?",(loan["borrower_id"],))
                reason="На балансі не вистачило коштів. Доступ до банківського кредитування заблоковано."
            else:
                if bal > 0:
                    conn.execute("UPDATE users SET balance=0 WHERE user_id=?",(loan["borrower_id"],))
                    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(bal,loan["lender_id"]))
                reason="На балансі не вистачило коштів для повного погашення. Кредитор отримав доступну суму."
            status="defaulted"
        conn.execute("UPDATE loans SET status=?,closed_at=? WHERE loan_id=?",(status,now.isoformat(),loan["loan_id"]))
        if loan["lender_id"] != 0:
            asyncio.create_task(safe_dm(loan["lender_id"],embed_obj=embed(
                "⚠️ Кредит прострочено",
                f"<@{loan['borrower_id']}> не погасив кредит **{money(loan['total_due'])} грн.** у встановлений строк.",
                discord.Color.red())))
        asyncio.create_task(safe_dm(loan["borrower_id"],embed_obj=embed(
            "⚠️ До вас прийшли кредитори" if loan["lender_id"] != 0 else "⚠️ Кредит прострочено",
            f"Термін погашення кредиту минув.\n\n{reason}" +
            ("\n\nБанк більше не надаватиме тобі нові кредити." if loan["lender_id"] == 0 else ""),
            discord.Color.red())))
    conn.commit(); conn.close()

    for loan in reminders:
        await safe_dm(loan["borrower_id"],embed_obj=embed(
            "⏰ Нагадування про кредит",
            f"Нагадую: тобі потрібно погасити кредит на **{money(loan['total_due'])} грн.**.\n"
            "У тебе ще є час до завершення 24-годинного пільгового періоду.",
            discord.Color.orange()),
            view=LoanDueView(loan["borrower_id"],loan["loan_id"]))

class LoanDueView(discord.ui.View):
    def __init__(self,owner_id,loan_id):
        super().__init__(timeout=24*60*60); self.owner_id=owner_id; self.loan_id=loan_id
    async def interaction_check(self,interaction):
        if interaction.user.id!=self.owner_id:
            await interaction.response.send_message("❌ Це повідомлення призначене іншому гравцю.",ephemeral=True); return False
        return True
    @discord.ui.button(label="Погасити",emoji="💚",style=discord.ButtonStyle.success)
    async def repay(self,interaction,button):
        conn=db(); loan=conn.execute("SELECT * FROM loans WHERE loan_id=? AND borrower_id=? AND status='grace'",(self.loan_id,self.owner_id)).fetchone()
        if not loan: conn.close(); return await interaction.response.send_message("❌ Кредит уже закрито.",ephemeral=True)
        bal=conn.execute("SELECT balance FROM users WHERE user_id=?",(self.owner_id,)).fetchone()["balance"]
        if bal<loan["total_due"]:
            conn.close(); return await interaction.response.send_message(f"❌ Недостатньо коштів. Потрібно {money(loan['total_due'])} грн.",ephemeral=True)
        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?",(loan["total_due"],self.owner_id))
        if loan["lender_id"] != 0:
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(loan["total_due"],loan["lender_id"]))
        conn.execute("UPDATE loans SET status='paid',closed_at=? WHERE loan_id=?",(datetime.now(timezone.utc).isoformat(),self.loan_id))
        conn.commit(); conn.close()
        await interaction.response.edit_message(embed=embed("🤝 Дякуємо за співпрацю","Кредит успішно погашено.",discord.Color.green()),view=None)
    @discord.ui.button(label="Нагадати через 1 год.",emoji="⏰",style=discord.ButtonStyle.danger)
    async def remind(self,interaction,button):
        conn=db()
        loan=conn.execute("SELECT * FROM loans WHERE loan_id=? AND borrower_id=? AND status='grace'",
                          (self.loan_id,self.owner_id)).fetchone()
        if not loan:
            conn.close()
            return await interaction.response.send_message("❌ Кредит уже закрито.",ephemeral=True)
        reminder=datetime.now(timezone.utc)+timedelta(hours=1)
        conn.execute("UPDATE loans SET reminder_at=? WHERE loan_id=?",(reminder.isoformat(),self.loan_id))
        conn.commit(); conn.close()
        await interaction.response.edit_message(
            content="⏰ Нагадування встановлено. Я напишу тобі через **1 годину**.",
            view=None)

def valid_player_loan(principal, rate, days):
    return 1_000 <= principal <= MAX_BET and 0.1 <= rate <= 70 and 1 <= days <= MAX_LOAN_DAYS

class PlayerLoanModal(discord.ui.Modal):
    def __init__(self, title, target_label):
        super().__init__(title=title)
        self.target=discord.ui.TextInput(label=target_label,placeholder="Discord ID або @нік")
        self.amount=discord.ui.TextInput(label="Сума",placeholder="Наприклад: 10000")
        self.rate=discord.ui.TextInput(label="Відсоток",placeholder="Наприклад: 10")
        self.days=discord.ui.TextInput(label="Кількість днів",placeholder="Наприклад: 10")
        for x in (self.target,self.amount,self.rate,self.days): self.add_item(x)
    async def parse(self,interaction):
        target=await resolve_member(interaction.guild,str(self.target.value).strip())
        if not target or target.bot or target.id==interaction.user.id:
            await interaction.response.send_message("❌ Не вдалося знайти потрібного гравця.",ephemeral=True); return None
        try: amount=int(str(self.amount.value).replace(" ","")); rate=float(str(self.rate.value).replace(",",".")); days=int(self.days.value)
        except ValueError:
            await interaction.response.send_message("❌ Перевір суму, відсоток та кількість днів.",ephemeral=True); return None
        if not valid_player_loan(amount,rate,days):
            await interaction.response.send_message("❌ Сума: 1 000+; відсоток: 0.1–70%; термін: 1–10 днів.",ephemeral=True); return None
        return target,amount,rate,days

class PlayerBorrowModal(PlayerLoanModal):
    def __init__(self):
        super().__init__("Взяти у кредит від гравця","У кого взяти кредит?")

    async def on_submit(self,interaction):
        parsed=await self.parse(interaction)
        if not parsed:return
        lender,amount,rate,days=parsed
        await create_player_offer(interaction.user.id,lender.id,lender.id,interaction.user.id,amount,rate,days)

class PlayerLendModal(PlayerLoanModal):
    def __init__(self):
        super().__init__("Запропонувати кредит гравцю","Кому запропонувати кредит?")

    async def on_submit(self,interaction):
        parsed=await self.parse(interaction)
        if not parsed:return
        borrower,amount,rate,days=parsed
        if get_user(interaction.user.id)["balance"]<amount:
            return await interaction.response.send_message("❌ У тебе недостатньо коштів для такої пропозиції.",ephemeral=True)
        await create_player_offer(interaction.user.id,borrower.id,interaction.user.id,borrower.id,amount,rate,days)

async def create_player_offer(proposer_id,counterparty_id,lender_id,borrower_id,amount,rate,days):
    conn=db()
    cur=conn.execute("""INSERT INTO loan_offers(proposer_id,counterparty_id,lender_id,borrower_id,principal,rate,days)
                        VALUES(?,?,?,?,?,?,?)""",(proposer_id,counterparty_id,lender_id,borrower_id,amount,rate,days))
    offer_id=cur.lastrowid
    conn.commit();conn.close()
    role_text=f"<@{lender_id}> → <@{borrower_id}>"
    view=PlayerOfferView(offer_id,counterparty_id)
    ok=await safe_dm(counterparty_id,embed_obj=embed("🤝 Пропозиція кредиту",
        f"💰 Сума: **{money(amount)} грн.**\n📈 Відсоток: **{rate:.2f}%**\n📅 Термін: **{days} дн.**\n"
        f"💵 До погашення: **{money(loan_total(amount,rate))} грн.**\n\n"
        f"Учасники: {role_text}\n\nОбери: схвалити, відмовити або запропонувати свої умови.",discord.Color.gold()),view=view)
    if not ok:
        conn=db();conn.execute("UPDATE loan_offers SET status='failed' WHERE offer_id=?",(offer_id,));conn.commit();conn.close()
    return offer_id

class PlayerOfferView(discord.ui.View):
    def __init__(self,offer_id,owner_id):
        super().__init__(timeout=3600);self.offer_id=offer_id;self.owner_id=owner_id
    async def interaction_check(self,interaction):
        if interaction.user.id!=self.owner_id:
            await interaction.response.send_message("❌ Ця пропозиція призначена іншому гравцю.",ephemeral=True);return False
        return True
    @discord.ui.button(label="Схвалити",emoji="✅",style=discord.ButtonStyle.success)
    async def accept(self,interaction,button):
        conn=db();offer=conn.execute("SELECT * FROM loan_offers WHERE offer_id=? AND status='pending'",(self.offer_id,)).fetchone()
        if not offer:conn.close();return await interaction.response.send_message("❌ Пропозиція вже недійсна.",ephemeral=True)
        lender=conn.execute("SELECT balance FROM users WHERE user_id=?",(offer["lender_id"],)).fetchone()
        if not lender or lender["balance"]<offer["principal"]:
            conn.close();return await interaction.response.send_message("❌ У кредитора зараз недостатньо коштів.",ephemeral=True)
        # Borrower can have only one active loan.
        active=conn.execute("SELECT 1 FROM loans WHERE borrower_id=? AND status IN ('active','grace')",(offer["borrower_id"],)).fetchone()
        if active:
            conn.close();return await interaction.response.send_message("❌ Позичальник уже має непогашений кредит.",ephemeral=True)
        now=datetime.now(timezone.utc);due=now+timedelta(days=offer["days"])
        total=loan_total(offer["principal"],offer["rate"])
        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?",(offer["principal"],offer["lender_id"]))
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(offer["principal"],offer["borrower_id"]))
        conn.execute("""INSERT INTO loans(lender_id,borrower_id,principal,rate,total_due,created_at,due_at,status)
                        VALUES(?,?,?,?,?,?,?,'active')""",
                     (offer["lender_id"],offer["borrower_id"],offer["principal"],offer["rate"],total,now.isoformat(),due.isoformat()))
        conn.execute("UPDATE loan_offers SET status='accepted',updated_at=? WHERE offer_id=?",(now.isoformat(),self.offer_id))
        conn.commit();conn.close()
        due_ts = int(due.timestamp())
        await interaction.response.edit_message(embed=embed("🤝 Кредит схвалено",
            f"Кредит на **{money(offer['principal'])} грн.** оформлено.\n"
            f"До погашення: **{money(total)} грн.**\n"
            f"📅 Погасити до: <t:{due_ts}:F>",discord.Color.green()),view=None)
        await safe_dm(offer["borrower_id"],embed_obj=embed("💳 Кредит схвалено",
            f"Гравець <@{offer['lender_id']}> схвалив тобі кредит на **{money(offer['principal'])} грн.** 💰\n\n"
            f"📈 Відсоток: **{offer['rate']:.2f}%**\n"
            f"📅 Термін: **{offer['days']} дн.**\n"
            f"💵 До погашення: **{money(total)} грн.**\n"
            f"🗓️ Погасити до: <t:{due_ts}:F>\n\n"
            "Достроково погасити можна через `/bank`.",discord.Color.green()))
        await safe_dm(offer["lender_id"],embed_obj=embed("💰 Кредит видано",
            f"<@{offer['borrower_id']}> отримав від тебе **{money(offer['principal'])} грн.**.\n"
            f"До повернення: **{money(total)} грн.**\n"
            f"📅 Погасити до: <t:{due_ts}:F>",discord.Color.green()))
    @discord.ui.button(label="Відмовити",emoji="❌",style=discord.ButtonStyle.danger)
    async def decline(self,interaction,button):
        conn=db();conn.execute("UPDATE loan_offers SET status='declined',updated_at=? WHERE offer_id=? AND status='pending'",
                               (datetime.now(timezone.utc).isoformat(),self.offer_id));conn.commit();conn.close()
        await interaction.response.edit_message(embed=embed("❌ Пропозицію відхилено","Кредитна пропозиція була відхилена.",discord.Color.red()),view=None)
    @discord.ui.button(label="Запропонувати свої умови",emoji="✏️",style=discord.ButtonStyle.primary)
    async def counter(self,interaction,button):
        await interaction.response.send_modal(CounterLoanModal(self.offer_id,self.owner_id))

class CounterLoanModal(discord.ui.Modal,title="Нові умови кредиту"):
    amount=discord.ui.TextInput(label="Нова сума",placeholder="Наприклад: 20000")
    rate=discord.ui.TextInput(label="Новий відсоток",placeholder="Наприклад: 15")
    days=discord.ui.TextInput(label="Новий термін у днях",placeholder="Наприклад: 14")
    def __init__(self,offer_id,owner_id):
        super().__init__();self.offer_id=offer_id;self.owner_id=owner_id
    async def on_submit(self,interaction):
        try:amount=int(self.amount.value.replace(" ",""));rate=float(self.rate.value.replace(",","."));days=int(self.days.value)
        except ValueError:return await interaction.response.send_message("❌ Невірні умови.",ephemeral=True)
        if not valid_player_loan(amount,rate,days):return await interaction.response.send_message("❌ Сума від 1 000, відсоток 0.1–70%, термін 1–10 днів.",ephemeral=True)
        conn=db();offer=conn.execute("SELECT * FROM loan_offers WHERE offer_id=? AND status='pending'",(self.offer_id,)).fetchone()
        if not offer:conn.close();return await interaction.response.send_message("❌ Пропозиція вже недійсна.",ephemeral=True)
        # Counteroffer keeps the same lender/borrower roles and goes back to original proposer.
        conn.execute("""UPDATE loan_offers SET principal=?,rate=?,days=?,counterparty_id=?,updated_at=? WHERE offer_id=?""",
                     (amount,rate,days,offer["proposer_id"],datetime.now(timezone.utc).isoformat(),self.offer_id))
        conn.commit();conn.close()
        await interaction.response.edit_message(embed=embed("✏️ Нові умови надіслано","Твої умови відправлено іншій стороні кредиту.",discord.Color.blurple()),view=None)
        await safe_dm(offer["proposer_id"],embed_obj=embed("✏️ Контрпропозиція",
            f"Гравець <@{self.owner_id}> запропонував нові умови:\n\n"
            f"💰 **{money(amount)} грн.**\n📈 **{rate:.2f}%**\n📅 **{days} дн.**\n"
            f"💵 До погашення: **{money(loan_total(amount,rate))} грн.**",discord.Color.gold()),
            view=PlayerOfferView(self.offer_id,offer["proposer_id"]))

@bot.tree.command(name="bank_offer", description="Запропонувати гравцю кредит")
@app_commands.describe(user="Кому запропонувати", money="Сума", procent="Відсоток", days="Кількість днів")
async def bank_offer(interaction: discord.Interaction, user: discord.Member, money: app_commands.Range[int, 1000, MAX_BET], procent: app_commands.Range[float, 0.1, 70.0], days: app_commands.Range[int, 1, MAX_LOAN_DAYS]):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if user.bot or user.id == interaction.user.id:
        return await interaction.response.send_message("❌ Обери іншого гравця.", ephemeral=True)
    if get_user(interaction.user.id, interaction.user.name)["balance"] < money:
        return await interaction.response.send_message("❌ У тебе недостатньо коштів для цієї пропозиції.", ephemeral=True)
    await create_player_offer(interaction.user.id, user.id, interaction.user.id, user.id, money, float(procent), days)
    await interaction.response.send_message(embed=embed("💼 Пропозицію надіслано",
        f"Гравцю {user.mention} надіслано кредитну пропозицію.\n\n💰 Сума: **{money} грн.**\n📈 Відсоток: **{float(procent):.2f}%**\n📅 Термін: **{days} дн.**\n💵 До погашення: **{loan_total(money, float(procent))} грн.**", discord.Color.gold()), ephemeral=True)


@bot.tree.command(name="bank_borrow", description="Попросити гравця видати тобі кредит")
@app_commands.describe(user="У кого попросити", money="Сума", procent="Відсоток", days="Кількість днів")
async def bank_borrow(interaction: discord.Interaction, user: discord.Member, money: app_commands.Range[int, 1000, MAX_BET], procent: app_commands.Range[float, 0.1, 70.0], days: app_commands.Range[int, 1, MAX_LOAN_DAYS]):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if user.bot or user.id == interaction.user.id:
        return await interaction.response.send_message("❌ Обери іншого гравця.", ephemeral=True)
    await create_player_offer(interaction.user.id, user.id, user.id, interaction.user.id, money, float(procent), days)
    await interaction.response.send_message(embed=embed("🤝 Заявку надіслано",
        f"Гравцю {user.mention} надіслано заявку на кредит.\n\n💰 Сума: **{money} грн.**\n📈 Відсоток: **{float(procent):.2f}%**\n📅 Термін: **{days} дн.**\n💵 До погашення: **{loan_total(money, float(procent))} грн.**", discord.Color.blurple()), ephemeral=True)


@bot.tree.command(name="bank", description="Відкрити банк та керувати кредитами")
async def bank(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if get_user(interaction.user.id, interaction.user.name)["bank_banned"]:
        return await interaction.response.send_message(
            "❌ **Банк більше недоступний для тебе.** Тобі закрито можливість брати кредити через порушення строків погашення та несплату попереднього боргу.",
            ephemeral=True)
    await interaction.response.send_message(embed=embed(
        "🏦 Вітаємо у банку!",
        "Тут ти можеш оформити кредит, погасити вже взятий борг або домовитися про кредит з іншим гравцем.\n\n"
        "💳 **Оформити кредит** — отримати кошти від банку.\n"
        "💰 **Погасити кредит** — достроково закрити борг.\n"
        "📋 **Кредити** — переглянути активні кредити.\n"
        "🤝 **Кредит від гравця** — подати заявку іншому гравцю.\n"
        "💼 **Запропонувати кредит** — виступити кредитором.\n\n"
        "⚡ **Швидкі команди:** `/bank_offer` — запропонувати кредит гравцю; `/bank_borrow` — попросити кредит у гравця.",
        discord.Color.gold()),view=BankMainView(interaction.user.id))

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

    await log_admin_action(interaction, f"Призначив користувача {user.mention} (`{user.id}`) адміністратором.")
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
    await log_admin_action(interaction, f"Зняв з користувача {user.mention} (`{user.id}`) права адміністратора.")
    await interaction.response.send_message(f"Адміністратора знято: {user.mention}.", ephemeral=True)

class GiveMoneyModal(discord.ui.Modal, title="Видати гроші"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    amount = discord.ui.TextInput(label="Кількість грошей", placeholder="50000")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        try: uid, amount = int(self.user_id.value.strip()), int(self.amount.value.strip()); assert amount > 0
        except (ValueError, AssertionError): return await interaction.response.send_message("Невірні дані.", ephemeral=True)
        old = get_user(uid)["balance"]
        money_add(uid, amount)
        new = get_user(uid)["balance"]
        await log_admin_action(interaction, f"Видав гроші користувачу <@{uid}> (`{uid}`). Сума: **{money(amount)} грн**. Баланс: **{money(old)} → {money(new)} грн**.")
        await interaction.response.send_message(f"{uid} отримав {money(amount)}.", ephemeral=True)

class SetMoneyModal(discord.ui.Modal, title="Встановити гроші"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    amount = discord.ui.TextInput(label="Новий баланс", placeholder="50000")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        try: uid, amount = int(self.user_id.value.strip()), int(self.amount.value.strip()); assert amount >= 0
        except (ValueError, AssertionError): return await interaction.response.send_message("Невірні дані.", ephemeral=True)
        old = get_user(uid)["balance"]; money_set(uid, amount)
        await log_admin_action(interaction, f"Встановив баланс користувачу <@{uid}> (`{uid}`). Було: **{money(old)} грн**, стало: **{money(amount)} грн**.")
        await interaction.response.send_message(f"Баланс {uid}: {money(old)} → {money(amount)}.", ephemeral=True)

class SetDickModal(discord.ui.Modal, title="Встановити розмір"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    size = discord.ui.TextInput(label="Новий розмір", placeholder="10")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        try: uid, size = int(self.user_id.value.strip()), int(self.size.value.strip())
        except ValueError: return await interaction.response.send_message("Невірні дані.", ephemeral=True)
        old = get_user(uid)["dick_size"]; dick_set(uid, size)
        await log_admin_action(interaction, f"Змінив розмір користувачу <@{uid}> (`{uid}`). Було: **{old} см**, стало: **{size} см**.")
        await interaction.response.send_message(f"Розмір {uid}: {old} см → {size} см.", ephemeral=True)

class RigRouletteModal(discord.ui.Modal, title="Накрутка рулетки"):
    number = discord.ui.TextInput(label="Наступне число (1-50)", placeholder="17")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        try: n = int(self.number.value.strip()); assert 1 <= n <= 50
        except (ValueError, AssertionError): return await interaction.response.send_message("Невірне число.", ephemeral=True)
        set_setting("roulette_next", str(n))
        await log_admin_action(interaction, f"Накрутив наступний результат рулетки: **{n}**.")
        await interaction.response.send_message(f"Наступного разу рулетка спробує показати {n}.", ephemeral=True)

class RigCoinModal(discord.ui.Modal, title="Накрутка монетки"):
    result = discord.ui.TextInput(label="Наступний результат", placeholder="Орел або Решка")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        value = self.result.value.strip().lower()
        mapping = {"орел": "Орел", "решка": "Решка", "heads": "Орел", "tails": "Решка"}
        if value not in mapping: return await interaction.response.send_message("Напиши Орел або Решка.", ephemeral=True)
        set_setting("coinflip_next", mapping[value])
        await log_admin_action(interaction, f"Накрутив наступний результат монетки: **{mapping[value]}**.")
        await interaction.response.send_message(
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
        await log_admin_action(interaction, f"Надіслав користувачу {member.mention} (`{member.id}`) особисте повідомлення. Текст: **{discord.utils.escape_markdown(str(self.text.value))[:500]}**" + (" (із вкладеним посиланням на медіа)" if self.attachment_url.value.strip() else "") + ".")
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
        business_rows = conn.execute(
            "SELECT user_id, business_name, price, hourly_profit, purchased_at, last_paid_at FROM businesses ORDER BY user_id, business_name"
        ).fetchall()
        loan_rows = conn.execute(
            "SELECT loan_id, lender_id, borrower_id, principal, rate, total_due, due_at, status FROM loans ORDER BY loan_id DESC LIMIT 100"
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

    business_text = [
        f"<@{x['user_id']}> | **{x['business_name']}** | +{money(x['hourly_profit'])}/год. | купівля `{money(x['price'])}`"
        for x in business_rows
    ]
    parts.append(("🏢 Бізнеси", "\n".join(business_text) or "Немає бізнесів."))

    loan_text = [
        f"#{x['loan_id']} | <@{x['borrower_id']}> ← {'🏦 Банк' if x['lender_id']==0 else '<@'+str(x['lender_id'])+'>'} | "
        f"`{money(x['principal'])}` → `{money(x['total_due'])}` | `{x['rate']:.4f}%` | `{x['status']}`"
        for x in loan_rows
    ]
    parts.append(("💳 Кредити", "\n".join(loan_text) or "Немає кредитів."))

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

    await log_admin_action(interaction, "Переглянув повний звіт бази даних.")
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



class BankBlockReasonModal(discord.ui.Modal, title="Причина блокування банку"):
    reason = discord.ui.TextInput(label="Причина (необов'язково)", placeholder="Наприклад: систематичне прострочення", required=False, max_length=300)
    def __init__(self, target: discord.Member, unblock=False):
        super().__init__(); self.target=target; self.unblock=unblock
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        reason=self.reason.value.strip() or ("Причина не вказана." if self.unblock else "Рішення адміністрації.")
        conn=db(); conn.execute("UPDATE users SET bank_banned=?, bank_ban_reason=? WHERE user_id=?", (0 if self.unblock else 1, None if self.unblock else reason, self.target.id)); conn.commit(); conn.close()
        if self.unblock:
            await safe_dm(self.target.id, embed_obj=embed("🏦 Банк розблоковано", f"Ваш банк було розблоковано адміністрацією.\n\nПричина: **{reason}**", discord.Color.green()))
            msg=f"Адміністратор **{interaction.user}** розблокував банк гравця **{self.target}**. Причина: **{reason}**"
        else:
            await safe_dm(self.target.id, embed_obj=embed("🚫 Банк заблоковано", f"Ваш доступ до кредитів банку заблоковано адміністрацією.\n\nПричина: **{reason}**", discord.Color.red()))
            msg=f"Адміністратор **{interaction.user}** заблокував банк гравця **{self.target}**. Причина: **{reason}**"
        asyncio.create_task(log_purchase(msg))
        await log_admin_action(
            interaction,
            f"{'Розблокував' if self.unblock else 'Заблокував'} банк користувачу {self.target.mention} (`{self.target.id}`). Причина: **{reason}**."
        )
        await interaction.response.send_message("✅ Готово.", ephemeral=True)

class BankUserSelect(discord.ui.UserSelect):
    def __init__(self, unblock=False):
        super().__init__(placeholder="Оберіть користувача", min_values=1, max_values=1)
        self.unblock=unblock
    async def callback(self, interaction):
        if not is_admin(interaction.user.id): return await admin_denied(interaction)
        await interaction.response.send_modal(BankBlockReasonModal(self.values[0], self.unblock))

class BankUserView(discord.ui.View):
    def __init__(self, unblock=False):
        super().__init__(timeout=300); self.add_item(BankUserSelect(unblock))

class GrantVehicleView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=300); self.owner_id=owner_id
        for rarity, data in CASE_DATA.items():
            options=[discord.SelectOption(label=name[:100], value=name, description=f"{money(value)} 💰") for name,value,_ in data["cars"]]
            select=discord.ui.Select(placeholder=f"🚗 {rarity}", options=options, row=list(CASE_DATA.keys()).index(rarity))
            async def cb(interaction, select=select):
                if interaction.user.id != self.owner_id: return await interaction.response.send_message("❌ Це меню доступне лише власнику.", ephemeral=True)
                await interaction.response.edit_message(content=f"🚗 Обрано автомобіль: **{select.values[0]}**\nТепер відмітьте користувача.", embed=None, view=GrantTargetView(self.owner_id, "car", select.values[0]))
            select.callback=cb; self.add_item(select)

class GrantBusinessView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=300); self.owner_id=owner_id
        options=[discord.SelectOption(label=n[:100], value=n, description=f"{money(p)} | +{money(h)}/год.") for n,p,h in BUSINESSES]
        sel=discord.ui.Select(placeholder="Оберіть бізнес", options=options)
        async def cb(interaction):
            if interaction.user.id != self.owner_id: return await interaction.response.send_message("❌ Це меню доступне лише власнику.", ephemeral=True)
            await interaction.response.edit_message(content=f"🏢 Обрано: **{sel.values[0]}**\nТепер відмітьте користувача.", embed=None, view=GrantTargetView(self.owner_id, "business", sel.values[0]))
        sel.callback=cb; self.add_item(sel)

class GrantTargetView(discord.ui.View):
    def __init__(self, owner_id, item_type, item_key):
        super().__init__(timeout=300); self.owner_id=owner_id; self.item_type=item_type; self.item_key=item_key
        select=discord.ui.UserSelect(placeholder="Оберіть користувача", min_values=1, max_values=1)
        async def cb(interaction):
            if interaction.user.id != self.owner_id: return await interaction.response.send_message("❌ Це меню доступне лише власнику.", ephemeral=True)
            target=select.values[0]; ensure_user(target.id,target.name)
            if self.item_type == "car":
                add_inventory_item(target.id,"car",self.item_key,1)
                conn=db(); row=conn.execute("SELECT active_car FROM users WHERE user_id=?",(target.id,)).fetchone()
                if not row["active_car"]: conn.execute("UPDATE users SET active_car=? WHERE user_id=?",(self.item_key,target.id))
                conn.commit(); conn.close()
                text=f"🚗 Автомобіль **{self.item_key}** видано {target.mention}."
            else:
                if find_inventory_item(target.id, "business", self.item_key):
                    return await interaction.response.send_message("❌ У цього гравця такий бізнес уже є.", ephemeral=True)
                add_inventory_item(target.id,"business",self.item_key,1)
                name, price, hourly = BUSINESS_BY_NAME[self.item_key]
                now=datetime.now(timezone.utc).isoformat()
                conn=db()
                active=conn.execute("SELECT active_business FROM users WHERE user_id=?",(target.id,)).fetchone()["active_business"]
                if not active: conn.execute("UPDATE users SET active_business=? WHERE user_id=?",(self.item_key,target.id))
                conn.execute("INSERT INTO businesses(user_id,business_name,price,hourly_profit,last_paid_at) VALUES(?,?,?,?,?)",(target.id,name,price,hourly,now))
                conn.commit(); conn.close()
                text=f"🏢 Бізнес **{self.item_key}** видано {target.mention}." + (" Він став активним." if not active else " Він доданий до інвентарю; активним залишається поточний бізнес.")
            await safe_dm(target.id,embed_obj=embed("🎁 Вам видано майно",text,discord.Color.green()))
            asyncio.create_task(log_purchase(f"Адміністратор **{interaction.user}** видав гравцю **{target}**: **{self.item_key}** ({self.item_type})."))
            await log_admin_action(interaction, f"Видав {('автомобіль' if self.item_type == 'car' else 'бізнес')} **{self.item_key}** користувачу {target.mention} (`{target.id}`).")
            await interaction.response.edit_message(content=text,view=None)
        select.callback=cb; self.add_item(select)

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

    @discord.ui.button(label="Блокувати банк", emoji="🚫", style=discord.ButtonStyle.danger, row=3)
    async def block_bank_btn(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_message("Оберіть користувача:", view=BankUserView(False), ephemeral=True)

    @discord.ui.button(label="Розблокувати банк", emoji="🔓", style=discord.ButtonStyle.success, row=3)
    async def unblock_bank_btn(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_message("Оберіть користувача:", view=BankUserView(True), ephemeral=True)

    @discord.ui.button(label="Видати авто", emoji="🚗", style=discord.ButtonStyle.primary, row=4)
    async def give_vehicle_btn(self, interaction, button):
        if not is_owner(interaction.user.id): return await admin_denied(interaction)
        await interaction.response.send_message("Оберіть автомобіль:", view=GrantVehicleView(interaction.user.id), ephemeral=True)

    @discord.ui.button(label="Видати бізнес", emoji="🏢", style=discord.ButtonStyle.primary, row=4)
    async def give_business_btn(self, interaction, button):
        if not is_owner(interaction.user.id): return await admin_denied(interaction)
        await interaction.response.send_message("Оберіть бізнес:", view=GrantBusinessView(interaction.user.id), ephemeral=True)

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
    await log_admin_action(interaction, "Відкрив адмін-панель.")
    await interaction.response.send_message(
        embed=embed("🛠️ Адмін-панель", "💰 Економіка • 🍆 Розміри • 🎟️ Промокоди • 🎲 Накрутки • 🗄️ База даних\n\nПанель доступна адміністраторам. Власник також може призначати та знімати адміністраторів.", discord.Color.dark_red()),
        view=AdminView(), ephemeral=True
    )

@bot.tree.command(name="givemoney", description="🔒 Видати гроші користувачу")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", amount="Кількість")
async def givemoney(interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1, MAX_BET]):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    old = get_user(user.id, user.name)["balance"]
    money_add(user.id, amount)
    new = get_user(user.id, user.name)["balance"]
    await log_admin_action(interaction, f"Видав гроші {user.mention} (`{user.id}`). Сума: **{money(amount)} грн**. Баланс: **{money(old)} → {money(new)} грн**.")
    await interaction.response.send_message(f"{user.mention} отримав {money(amount)}.", ephemeral=True)

@bot.tree.command(name="setmoney", description="🔒 Встановити баланс користувачу")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", amount="Новий баланс")
async def setmoney(interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 0, MAX_BET]):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    old = get_user(user.id, user.name)["balance"]; money_set(user.id, amount)
    await log_admin_action(interaction, f"Встановив баланс {user.mention} (`{user.id}`). Було: **{money(old)} грн**, стало: **{money(amount)} грн**.")
    await interaction.response.send_message(f"Баланс {user.mention}: {money(old)} → {money(amount)}.", ephemeral=True)

@bot.tree.command(name="setdick", description="🔒 Встановити розмір користувачу")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", size="Новий розмір")
async def setdick(interaction: discord.Interaction, user: discord.Member, size: int):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    old = get_user(user.id, user.name)["dick_size"]; dick_set(user.id, size)
    await log_admin_action(interaction, f"Встановив розмір {user.mention} (`{user.id}`). Було: **{old} см**, стало: **{size} см**.")
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

@bot.tree.command(name="stamina", description="🔋 Увімкнути/вимкнути безлімітну стаміну користувача")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач")
async def stamina(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction.user.id):
        return await admin_denied(interaction)
    enabled = toggle_stamina(user.id)
    status = "увімкнено ♾️" if enabled else "вимкнено 🔒"
    await log_admin_action(interaction, f"{('Увімкнув' if enabled else 'Вимкнув')} безлімітну стаміну користувачу {user.mention} (`{user.id}`).")
    await safe_dm(user.id, embed_obj=embed(
        "🔋 Стаміна",
        f"Адміністратор **{interaction.user.display_name}** {('увімкнув' if enabled else 'вимкнув')} тобі безлімітну стаміну.\n\nСтатус: **{status}**\n"
        f"{'Тепер /dick, /daily та /masturbation можна використовувати без очікування кулдауну.' if enabled else 'Звичайні кулдауни знову працюють.'}",
        discord.Color.green() if enabled else discord.Color.red()))
    await interaction.response.send_message(
        f"🔋 Для {user.mention} безлімітну стаміну **{('увімкнено ♾️' if enabled else 'вимкнено 🔒')}**.",
        ephemeral=True)


@bot.tree.command(name="block_bank", description="🔒 Заблокувати банківські кредити")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", reason="Причина (необов'язково)")
async def block_bank(interaction: discord.Interaction, user: discord.Member, reason: str = ""):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    reason=reason.strip() or "Рішення адміністрації."
    conn=db(); conn.execute("UPDATE users SET bank_banned=1, bank_ban_reason=? WHERE user_id=?",(reason,user.id)); conn.commit(); conn.close()
    await safe_dm(user.id,embed_obj=embed("🚫 Банк заблоковано",f"Ваш доступ до кредитів банку заблоковано.\n\nПричина: **{reason}**",discord.Color.red()))
    asyncio.create_task(log_purchase(f"Адміністратор **{interaction.user}** заблокував банк гравця **{user}**. Причина: **{reason}**"))
    await log_admin_action(interaction, f"Заблокував банк користувачу {user.mention} (`{user.id}`). Причина: **{reason}**.")
    await interaction.response.send_message(f"✅ Банк {user.mention} заблоковано.",ephemeral=True)

@bot.tree.command(name="unblock_bank", description="🔓 Розблокувати банківські кредити")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Користувач", reason="Причина (необов'язково)")
async def unblock_bank(interaction: discord.Interaction, user: discord.Member, reason: str = ""):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    reason=reason.strip()
    conn=db(); conn.execute("UPDATE users SET bank_banned=0, bank_ban_reason=NULL WHERE user_id=?",(user.id,)); conn.commit(); conn.close()
    if reason: await safe_dm(user.id,embed_obj=embed("🏦 Банк розблоковано",f"Ваш банк було розблоковано адміністрацією.\n\nПричина: **{reason}**",discord.Color.green()))
    asyncio.create_task(log_purchase(f"Адміністратор **{interaction.user}** розблокував банк гравця **{user}**." + (f" Причина: **{reason}**" if reason else "")))
    await log_admin_action(interaction, f"Розблокував банк користувачу {user.mention} (`{user.id}`)." + (f" Причина: **{reason}**." if reason else ""))
    await interaction.response.send_message(f"✅ Банк {user.mention} розблоковано.",ephemeral=True)

@bot.tree.command(name="give_vehicle", description="🔒 Видати автомобіль користувачу")
@app_commands.default_permissions(administrator=True)
async def give_vehicle(interaction: discord.Interaction):
    if not is_owner(interaction.user.id): return await admin_denied(interaction)
    await log_admin_action(interaction, "Відкрив меню видачі автомобіля.")
    await interaction.response.send_message("🚗 Оберіть автомобіль:",view=GrantVehicleView(interaction.user.id),ephemeral=True)

@bot.tree.command(name="give_business", description="🔒 Видати бізнес користувачу")
@app_commands.default_permissions(administrator=True)
async def give_business(interaction: discord.Interaction):
    if not is_owner(interaction.user.id): return await admin_denied(interaction)
    await log_admin_action(interaction, "Відкрив меню видачі бізнесу.")
    await interaction.response.send_message("🏢 Оберіть бізнес:",view=GrantBusinessView(interaction.user.id),ephemeral=True)

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
    await log_admin_action(interaction, f"Надіслав користувачу {user.mention} (`{user.id}`) особисте повідомлення: **{discord.utils.escape_markdown(text)[:500]}**" + (" (із вкладенням)." if attachment else "."))
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
    conn.close()
    await log_admin_action(interaction, f"Створив промокод **{code}**: +**{money(money_amount)} грн**, {dick_amount:+d} см.")
    await interaction.response.send_message(f"Промокод {code} створено. +{money(money_amount)}, {dick_amount:+d} см.", ephemeral=True)

# ---------------- GLOBAL ERROR / HEALTH HANDLERS ----------------

@bot.event
async def on_error(event_method, *args, **kwargs):
    """Never allow an event exception to silently kill a Discord event path."""
    import traceback
    print(f"[EVENT ERROR] method={event_method!r}")
    traceback.print_exc()

@bot.event
async def on_command_error(ctx, error):
    """Prefix-command safety net for commands that fail before responding."""
    original = getattr(error, "original", error)
    print(
        f"[PREFIX ERROR] command={getattr(ctx.command, 'qualified_name', 'unknown')} "
        f"user={getattr(ctx.author, 'id', 'unknown')}: {original!r}"
    )
    if getattr(ctx, "interaction", None):
        return
    try:
        await ctx.send("❌ Під час виконання команди сталася помилка. Спробуй ще раз.")
    except Exception as exc:
        print(f"[PREFIX ERROR RESPONSE FAILED] {exc!r}")

# ---------------- SLASH COMMAND ERROR HANDLER ----------------

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Prevent silent slash-command failures and always return a useful response."""
    original = getattr(error, "original", error)

    # Validation errors are normally handled by Discord before callback execution.
    # For unexpected runtime errors, log the full exception and give the user a
    # short, non-sensitive message instead of leaving the interaction hanging.
    import traceback
    print(
        f"[SLASH ERROR] command={getattr(interaction.command, 'qualified_name', 'unknown')} "
        f"user={getattr(interaction.user, 'id', 'unknown')}: {original!r}"
    )
    traceback.print_exception(type(original), original, original.__traceback__)

    message = "❌ Під час виконання команди сталася помилка. Спробуй ще раз."
    if isinstance(error, app_commands.CheckFailure):
        message = "❌ У тебе немає доступу до цієї команди."
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = "⏳ Цю команду зараз не можна використати. Спробуй трохи пізніше."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException as exc:
        print(f"[SLASH ERROR RESPONSE FAILED] {exc!r}")

# ---------------- START ----------------

_economy_task: Optional[asyncio.Task] = None

@bot.event
async def on_ready():
    global _backup_task, _economy_task
    init_db()
    await resume_masturbation_sessions()
    try:
        conn = db()
        existing_business_users = {
            r["user_id"]
            for r in conn.execute("SELECT DISTINCT user_id FROM businesses").fetchall()
        }
        conn.close()
        # Re-register persistent component views after every reconnect/restart.
        # This is what makes buttons from already-sent DM messages continue to
        # work instead of showing Discord's "This interaction failed" message.
        for uid in existing_business_users:
            _register_business_preference_view(BusinessPreferenceView(uid))
            # Only send onboarding when the DB says it has not been sent.
            asyncio.create_task(send_business_preference(uid))
    except Exception as exc:
        print(f"[BUSINESS DM] startup notification scheduling error: {exc!r}")
    if _economy_task is None or _economy_task.done():
        _economy_task = asyncio.create_task(economy_loop())
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
            try:
                global_synced = await bot.tree.sync()
                print(f"Logged in as {bot.user}. Synced {len(synced)} guild commands and {len(global_synced)} global commands.")
            except Exception as global_exc:
                print(f"Global slash command sync warning: {global_exc!r}")
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
