import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
default = "/data/bot.db" if railway else str(Path(__file__).resolve().parent / "bot.db")
path = Path(os.getenv("DB_PATH", default)).expanduser().resolve()
print(f"Database: {path}")
print(f"Exists: {path.exists()}")
if not path.exists():
    raise SystemExit("No database file found. This is normal before the bot has created it.")
print(f"Size: {path.stat().st_size:,} bytes")
con = sqlite3.connect(path)
print("Integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
print("Journal mode:", con.execute("PRAGMA journal_mode").fetchone()[0])
for table in ("users", "promos", "promo_uses", "roles", "bot_settings", "role_inventory", "cookie_games"):
    try:
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n}")
    except sqlite3.Error as e:
        print(f"{table}: ERROR {e}")
con.close()
