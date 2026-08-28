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
ROLE_CREATE_COST = 100_000
MIN_COINFLIP_BET = 100
MIN_COOKIE_BET = 1_000
MAX_BET = 2_000_000_000
COOKIE_WAIT_SECONDS = 10 * 60
COOKIE_COUNTDOWN_SECONDS = 10
COOKIE_PLAY_SECONDS = 60

ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing in .env / Railway Variables")

# Railway: set DB_PATH=/data/bot.db and attach a persistent Volume mounted at /data.
# Locally, bot.db is kept next to bot.py.
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.db"))


def db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
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
    """)
    conn.commit()
    conn.close()


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
    ensure_user(user_id)
    conn = db()
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
    conn.commit()
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


def is_admin(user_id: int):
    # ADMIN_IDS is a convenient emergency/owner override. The database admin flag
    # is also respected, so /setadmin can be used without editing code.
    if user_id in ADMIN_IDS:
        return True
    return bool(get_user(user_id)["admin"])


def embed(title, description="", color=discord.Color.blurple()):
    return discord.Embed(title=title, description=description, color=color)


def normal_channel_only(interaction: discord.Interaction) -> bool:
    return interaction.channel_id == NORMAL_CHANNEL_ID


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

@bot.tree.command(name="dick", description="🍆 Щодня змінити свій розмір пісюна")
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
        f"📈 Твій пісюн **{action}** на **{sign} см**!\n\n"
        f"Тепер його розмір: **{new_size} см** 🍆.",
        discord.Color.green() if change >= 0 else discord.Color.red(),
    ))


# ---------------- PROFILE / MONEY ----------------

@bot.tree.command(name="profile", description="👤 Показати профіль користувача")
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
    await interaction.response.send_message(embed=e)


@bot.tree.command(name="money", description="💰 Показати свій баланс")
async def money_cmd(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    u = get_user(interaction.user.id, interaction.user.name)
    await interaction.response.send_message(embed=embed(
        "💰 Баланс", f"{interaction.user.mention}, на твоєму балансі **{money(u['balance'])}** 💰."
    ))


@bot.tree.command(name="pay", description="💸 Відправити гроші іншому користувачу")
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

@bot.tree.command(name="daily", description="🎁 Отримати щоденний бонус")
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
        "🎁 Щоденний бонус", f"🎁 Ти отримав `{money(DAILY_REWARD)}` 💰!", discord.Color.gold()
    ))


# ---------------- TOP / HELP ----------------

@bot.tree.command(name="top", description="🏆 Показати топ-3 користувачів за балансом")
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


@bot.tree.command(name="help", description="📚 Список команд і пояснення")
async def help_cmd(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    e = embed("📚 Допомога", "Усі звичайні команди працюють тільки в цьому каналі.")
    e.add_field(name="🍆 Профіль", value="`/dick` — раз на день змінює розмір.\n`/profile [user]` — профіль.\n`/money` — баланс.", inline=False)
    e.add_field(name="💰 Економіка", value="`/daily` — щоденний бонус.\n`/pay member amount` — переказ грошей.\n`/top` — топ-3 за балансом.", inline=False)
    e.add_field(name="🎰 Ігри", value="`/coinflip bet` — монетка.\n`/roulette bet` — рулетка.\n`/cookie user bet` — запропонувати гру в печеньку.", inline=False)
    e.add_field(name="🏪 Ролі", value="`/role_create` — створити роль.\n`/role_sell role price` — виставити свою роль.\n`/role_shop` — магазин ролей; кнопка **Купити** купує вибрану роль.", inline=False)
    e.add_field(name="🎟️ Інше", value="`/promo` — активувати промокод.", inline=False)
    if is_admin(interaction.user.id):
        e.add_field(name="🔒 Адмін", value="`/admin` — адмін-панель.\n`/givemoney`, `/setmoney`, `/setdick`, `/promo_create` — адміністративні команди.\nУсі команди з позначкою 🔒 доступні тільки адмінам.", inline=False)
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


@bot.tree.command(name="promo", description="🎟️ Активувати промокод")
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

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Це не твоя ставка.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Орел", emoji="🦅", style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.choice = "Орел"; await self.finish(interaction)

    @discord.ui.button(label="Решка", emoji="🪙", style=discord.ButtonStyle.secondary)
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.choice = "Решка"; await self.finish(interaction)

    async def finish(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=embed("🪙 Підкинув монетку...", "Зачекай 2 секунди..."), view=None)
        await asyncio.sleep(2)
        forced = get_setting("coinflip_next")
        if forced in ("Орел", "Решка"):
            result = forced
            delete_setting("coinflip_next")
        else:
            result = random.choice(["Орел", "Решка"])
        won = result == self.choice
        if won:
            money_add(self.owner_id, self.bet * 2)
            text = f"🪙 Випало: **{result}**!\n\n🎉 Ти вгадав! Отримуєш **{money(self.bet * 2)}** 💰."
            color = discord.Color.green()
        else:
            text = f"🪙 Випало: **{result}**!\n\n❌ Ти програв ставку **{money(self.bet)}** 💰."
            color = discord.Color.red()
        await interaction.edit_original_response(embed=embed("🪙 Coinflip", text, color), view=None)
        self.stop()


@bot.tree.command(name="coinflip", description="🪙 Ставка на орла або решку")
@app_commands.describe(bet="Сума ставки")
async def coinflip(interaction: discord.Interaction, bet: app_commands.Range[int, MIN_COINFLIP_BET, MAX_BET]):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    u = get_user(interaction.user.id, interaction.user.name)
    if u["balance"] < bet:
        return await interaction.response.send_message(f"❌ Недостатньо грошей. Баланс: **{money(u['balance'])}**.", ephemeral=True)
    money_add(interaction.user.id, -bet)
    await interaction.response.send_message(embed=embed("🪙 Coinflip", f"Ставка: **{money(bet)}** 💰\n\n**Обирай: орел чи решка?**"), view=CoinChoiceView(interaction.user.id, bet))


# ---------------- ROULETTE ----------------

@bot.tree.command(name="roulette", description="🎰 Ставка на число рулетки 0-36")
@app_commands.describe(bet="Сума ставки", number="Число від 0 до 36")
async def roulette(interaction: discord.Interaction, bet: app_commands.Range[int, 100, MAX_BET], number: app_commands.Range[int, 0, 36]):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    u = get_user(interaction.user.id, interaction.user.name)
    if u["balance"] < bet:
        return await interaction.response.send_message("❌ Недостатньо грошей.", ephemeral=True)
    money_add(interaction.user.id, -bet)
    await interaction.response.send_message(embed=embed("🎰 Рулетка", "🎰 Крутимо..."))
    await asyncio.sleep(2)
    forced = get_setting("roulette_next")
    if forced is not None:
        try: result = int(forced)
        except ValueError: result = random.randint(0, 36)
        delete_setting("roulette_next")
    else:
        result = random.randint(0, 36)
    if result == number:
        winnings = bet * 35
        money_add(interaction.user.id, winnings)
        text = f"🎰 Випало: **{result}**\n\n🎉 Виграш! Ти отримуєш **{money(winnings)}** 💰."
        color = discord.Color.green()
    else:
        text = f"🎰 Випало: **{result}**\n\n❌ Ти програв **{money(bet)}** 💰."
        color = discord.Color.red()
    await interaction.edit_original_response(embed=embed("🎰 Рулетка", text, color))


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


@bot.tree.command(name="cookie", description="🍪 Запропонувати користувачу гру в печеньку")
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


class RoleCreateModal(discord.ui.Modal, title="Створення ролі"):
    name = discord.ui.TextInput(label="Назва ролі", placeholder="VIP")
    color = discord.ui.TextInput(label="Колір HEX", placeholder="#5865F2")
    async def on_submit(self, interaction):
        if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
        u = get_user(interaction.user.id, interaction.user.name)
        if u["balance"] < ROLE_CREATE_COST:
            return await interaction.response.send_message(f"❌ Потрібно **{money(ROLE_CREATE_COST)}** 💰.", ephemeral=True)
        try: color_int = role_color_to_int(self.color.value)
        except ValueError: return await interaction.response.send_message("❌ Невірний HEX-колір. Приклад: `#5865F2`.", ephemeral=True)
        name = str(self.name.value).strip()
        if not 1 <= len(name) <= 100: return await interaction.response.send_message("❌ Назва має бути 1–100 символів.", ephemeral=True)
        role = await interaction.guild.create_role(name=name, colour=discord.Colour(color_int), reason=f"Custom role created by {interaction.user}")
        await interaction.user.add_roles(role)
        money_add(interaction.user.id, -ROLE_CREATE_COST)
        conn = db(); conn.execute("INSERT INTO roles(role_id, guild_id, owner_id, name, color, price, for_sale) VALUES (?, ?, ?, ?, ?, 0, 0)", (role.id, interaction.guild.id, interaction.user.id, name, color_int)); conn.commit(); conn.close()
        await interaction.response.send_message(f"✅ Роль {role.mention} створено та видано тобі.\n💸 Вартість: **{money(ROLE_CREATE_COST)}** 💰.", ephemeral=True)


@bot.tree.command(name="role_create", description="🏷️ Створити власну роль за 100,000")
async def role_create(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if not interaction.guild: return await interaction.response.send_message("❌ Тільки на сервері.", ephemeral=True)
    await interaction.response.send_modal(RoleCreateModal())


async def role_shop_rows(guild):
    conn = db(); rows = conn.execute("SELECT * FROM roles WHERE guild_id=? AND for_sale=1 ORDER BY price ASC", (guild.id,)).fetchall(); conn.close()
    return [r for r in rows if guild.get_role(r["role_id"])][:20]


async def role_shop_text(guild):
    rows = await role_shop_rows(guild)
    if not rows: return "🏪 Зараз у продажу немає ролей."
    return "\n".join(f"**{r['name']}** — **{money(r['price'])}** 💰 — продавець: <@{r['owner_id']}> — ID `{r['role_id']}`" for r in rows)


class RoleBuyModal(discord.ui.Modal, title="Купити роль"):
    role_id = discord.ui.TextInput(label="ID ролі", placeholder="Встав ID ролі з магазину")
    async def on_submit(self, interaction):
        if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
        try: rid = int(self.role_id.value.strip())
        except ValueError: return await interaction.response.send_message("❌ Невірний ID ролі.", ephemeral=True)
        await buy_role(interaction, rid)


async def buy_role(interaction: discord.Interaction, role_id: int):
    conn = db(); row = conn.execute("SELECT * FROM roles WHERE role_id=? AND guild_id=? AND for_sale=1", (role_id, interaction.guild.id)).fetchone()
    conn.close()
    if not row: return await interaction.response.send_message("❌ Ця роль не продається.", ephemeral=True)
    if row["owner_id"] == interaction.user.id: return await interaction.response.send_message("❌ Не можна купити власну роль.", ephemeral=True)
    buyer = get_user(interaction.user.id, interaction.user.name)
    if buyer["balance"] < row["price"]: return await interaction.response.send_message("❌ Недостатньо грошей.", ephemeral=True)
    role = interaction.guild.get_role(role_id)
    if not role: return await interaction.response.send_message("❌ Роль більше не існує на сервері.", ephemeral=True)
    price, seller_id = row["price"], row["owner_id"]
    conn = db()
    conn.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (price, interaction.user.id, price))
    changed = conn.execute("SELECT changes() AS c").fetchone()["c"]
    if not changed:
        conn.close(); return await interaction.response.send_message("❌ Недостатньо грошей.", ephemeral=True)
    conn.execute("INSERT OR IGNORE INTO users(user_id, username, dick_size, balance) VALUES (?, ?, ?, 0)", (seller_id, str(seller_id), START_DICK_SIZE))
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (price, seller_id))
    conn.execute("UPDATE roles SET owner_id=?, for_sale=0 WHERE role_id=?", (interaction.user.id, role_id))
    conn.commit(); conn.close()
    seller = interaction.guild.get_member(seller_id)
    if seller:
        try: await seller.remove_roles(role)
        except discord.HTTPException: pass
    try: await interaction.user.add_roles(role)
    except discord.HTTPException:
        money_add(interaction.user.id, price); money_add(seller_id, -price)
        conn = db(); conn.execute("UPDATE roles SET owner_id=?, for_sale=1 WHERE role_id=?", (seller_id, role_id)); conn.commit(); conn.close()
        return await interaction.response.send_message("⚠️ Discord не дозволив видати роль, покупку скасовано.", ephemeral=True)
    await interaction.response.send_message(f"✅ Ти купив {role.mention} за **{money(price)}** 💰.", ephemeral=True)


class RoleShopView(discord.ui.View):
    def __init__(self): super().__init__(timeout=300)
    @discord.ui.button(label="Оновити", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction, button):
        if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
        await interaction.response.edit_message(embed=embed("🏪 Магазин ролей", await role_shop_text(interaction.guild)), view=RoleShopView())
    @discord.ui.button(label="Купити", emoji="💰", style=discord.ButtonStyle.success)
    async def buy(self, interaction, button):
        if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
        await interaction.response.send_modal(RoleBuyModal())


@bot.tree.command(name="role_shop", description="🏪 Переглянути та купити ролі")
async def role_shop(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if not interaction.guild: return await interaction.response.send_message("❌ Тільки на сервері.", ephemeral=True)
    await interaction.response.send_message(embed=embed("🏪 Магазин ролей", await role_shop_text(interaction.guild)), view=RoleShopView())


@bot.tree.command(name="role_sell", description="🏷️ Виставити свою роль на продаж")
@app_commands.describe(role="Роль", price="Ціна")
async def role_sell(interaction: discord.Interaction, role: discord.Role, price: app_commands.Range[int, 1, MAX_BET]):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    conn = db(); row = conn.execute("SELECT * FROM roles WHERE role_id=? AND guild_id=? AND owner_id=?", (role.id, interaction.guild.id, interaction.user.id)).fetchone()
    if not row: conn.close(); return await interaction.response.send_message("❌ Це не твоя роль, створена через бота.", ephemeral=True)
    conn.execute("UPDATE roles SET price=?, for_sale=1 WHERE role_id=?", (price, role.id)); conn.commit(); conn.close()
    await interaction.response.send_message(f"✅ {role.mention} виставлена на продаж за **{money(price)}** 💰.", ephemeral=True)


@bot.tree.command(name="role_buy", description="🏷️ Купити роль за ID")
@app_commands.describe(role_id="ID ролі з /role_shop")
async def role_buy(interaction: discord.Interaction, role_id: str):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    try: rid = int(role_id)
    except ValueError: return await interaction.response.send_message("❌ Невірний ID ролі.", ephemeral=True)
    await buy_role(interaction, rid)


# ---------------- ADMIN ----------------

def get_setting(key: str) -> Optional[str]:
    conn = db(); row = conn.execute("SELECT value FROM bot_settings WHERE key=?", (key,)).fetchone(); conn.close()
    return row["value"] if row else None


def set_setting(key: str, value: str):
    conn = db(); conn.execute("INSERT INTO bot_settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value)); conn.commit(); conn.close()


def delete_setting(key: str):
    conn = db(); conn.execute("DELETE FROM bot_settings WHERE key=?", (key,)); conn.commit(); conn.close()


class GiveMoneyModal(discord.ui.Modal, title="Видати гроші"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    amount = discord.ui.TextInput(label="Кількість грошей", placeholder="50000")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
        try: uid, amount = int(self.user_id.value.strip()), int(self.amount.value.strip()); assert amount > 0
        except (ValueError, AssertionError): return await interaction.response.send_message("❌ Невірні дані.", ephemeral=True)
        money_add(uid, amount); await interaction.response.send_message(f"✅ <@{uid}> отримав **{money(amount)}** 💰.", ephemeral=True)


class SetMoneyModal(discord.ui.Modal, title="Встановити гроші"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    amount = discord.ui.TextInput(label="Новий баланс", placeholder="50000")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
        try: uid, amount = int(self.user_id.value.strip()), int(self.amount.value.strip()); assert amount >= 0
        except (ValueError, AssertionError): return await interaction.response.send_message("❌ Невірні дані.", ephemeral=True)
        old = get_user(uid)["balance"]; money_set(uid, amount)
        await interaction.response.send_message(f"✅ Баланс <@{uid}> змінено: **{money(old)} → {money(amount)}** 💰.", ephemeral=True)


class SetDickModal(discord.ui.Modal, title="Встановити розмір"):
    user_id = discord.ui.TextInput(label="ID користувача", placeholder="123456789012345678")
    size = discord.ui.TextInput(label="Новий розмір", placeholder="10")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
        try: uid, size = int(self.user_id.value.strip()), int(self.size.value.strip())
        except ValueError: return await interaction.response.send_message("❌ Невірні дані.", ephemeral=True)
        old = get_user(uid)["dick_size"]; dick_set(uid, size)
        await interaction.response.send_message(f"✅ Розмір <@{uid}> змінено: **{old} см → {size} см**.", ephemeral=True)


class RigRouletteModal(discord.ui.Modal, title="Накрутка рулетки"):
    number = discord.ui.TextInput(label="Наступне число (0-36)", placeholder="Наприклад: 17")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
        try: n = int(self.number.value.strip()); assert 0 <= n <= 36
        except (ValueError, AssertionError): return await interaction.response.send_message("❌ Вкажи число від 0 до 36.", ephemeral=True)
        set_setting("roulette_next", str(n)); await interaction.response.send_message(f"🎰 Наступного разу рулетка примусово покаже **{n}**.", ephemeral=True)


class RigCoinModal(discord.ui.Modal, title="Накрутка монетки"):
    result = discord.ui.TextInput(label="Наступний результат", placeholder="Орел або Решка")
    async def on_submit(self, interaction):
        if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
        value = self.result.value.strip().lower()
        mapping = {"орел": "Орел", "решка": "Решка", "heads": "Орел", "tails": "Решка"}
        if value not in mapping: return await interaction.response.send_message("❌ Напиши `Орел` або `Решка`.", ephemeral=True)
        set_setting("coinflip_next", mapping[value]); await interaction.response.send_message(f"🪙 Наступного разу монетка покаже **{mapping[value]}**.", ephemeral=True)


class AdminView(discord.ui.View):
    def __init__(self): super().__init__(timeout=600)
    async def check(self, interaction):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Немає доступу.", ephemeral=True); return False
        return True
    @discord.ui.button(label="Видати гроші", emoji="💸", style=discord.ButtonStyle.success, row=0)
    async def give_money(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(GiveMoneyModal())
    @discord.ui.button(label="Встановити гроші", emoji="💰", style=discord.ButtonStyle.primary, row=0)
    async def set_money(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(SetMoneyModal())
    @discord.ui.button(label="Встановити розмір", emoji="🍆", style=discord.ButtonStyle.primary, row=0)
    async def set_dick(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(SetDickModal())
    @discord.ui.button(label="Накрутка рулетки", emoji="🎰", style=discord.ButtonStyle.danger, row=1)
    async def rig_roulette(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(RigRouletteModal())
    @discord.ui.button(label="Накрутка монетки", emoji="🪙", style=discord.ButtonStyle.danger, row=1)
    async def rig_coin(self, interaction, button):
        if await self.check(interaction): await interaction.response.send_modal(RigCoinModal())


@bot.tree.command(name="admin", description="🔒 Адмін-панель (тільки для адмінів)")
async def admin(interaction: discord.Interaction):
    if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
    await interaction.response.send_message(embed=embed("🛠️ Адмін-панель", "🔒 **Ця панель доступна тільки адміністраторам.**\n\nОбери потрібну дію нижче.", discord.Color.dark_red()), view=AdminView(), ephemeral=True)


@bot.tree.command(name="givemoney", description="🔒 Адмін: видати гроші користувачу")
@app_commands.describe(user="Користувач", amount="Кількість")
async def givemoney(interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1, MAX_BET]):
    if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
    money_add(user.id, amount); await interaction.response.send_message(f"✅ {user.mention} отримав **{money(amount)}** 💰.", ephemeral=True)


@bot.tree.command(name="setmoney", description="🔒 Адмін: встановити баланс користувачу")
@app_commands.describe(user="Користувач", amount="Новий баланс")
async def setmoney(interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 0, MAX_BET]):
    if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
    old = get_user(user.id, user.name)["balance"]; money_set(user.id, amount)
    await interaction.response.send_message(f"✅ Баланс {user.mention}: **{money(old)} → {money(amount)}** 💰.", ephemeral=True)


@bot.tree.command(name="setdick", description="🔒 Адмін: встановити розмір користувачу")
@app_commands.describe(user="Користувач", size="Новий розмір")
async def setdick(interaction: discord.Interaction, user: discord.Member, size: int):
    if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
    old = get_user(user.id, user.name)["dick_size"]; dick_set(user.id, size)
    await interaction.response.send_message(f"✅ Розмір {user.mention}: **{old} см → {size} см**.", ephemeral=True)


@bot.tree.command(name="setadmin", description="🔒 Адмін: видати або забрати адмін-права")
@app_commands.describe(user="Користувач", enabled="True — видати, False — забрати")
async def setadmin(interaction: discord.Interaction, user: discord.Member, enabled: bool):
    if not is_admin(interaction.user.id):
        return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
    conn = db()
    conn.execute("INSERT OR IGNORE INTO users(user_id, username, dick_size, balance) VALUES (?, ?, ?, 0)", (user.id, user.name, START_DICK_SIZE))
    conn.execute("UPDATE users SET username=?, admin=? WHERE user_id=?", (user.name, int(enabled), user.id))
    conn.commit(); conn.close()
    await interaction.response.send_message(
        f"{'✅ Адмін-права видано' if enabled else '🛑 Адмін-права забрано'}: {user.mention}.", ephemeral=True
    )


@bot.tree.command(name="promo_create", description="🔒 Адмін: створити промокод")
@app_commands.describe(code="Код", money_amount="Гроші", dick_amount="Скільки см")
async def promo_create(interaction: discord.Interaction, code: str, money_amount: app_commands.Range[int, 0, MAX_BET], dick_amount: int):
    if not is_admin(interaction.user.id): return await interaction.response.send_message("❌ Немає доступу.", ephemeral=True)
    code = code.strip().upper()
    conn = db()
    try:
        conn.execute("INSERT INTO promos(code, money, dick, created_by) VALUES (?, ?, ?, ?)", (code, money_amount, dick_amount, interaction.user.id)); conn.commit()
    except sqlite3.IntegrityError:
        conn.close(); return await interaction.response.send_message("❌ Такий промокод уже існує.", ephemeral=True)
    conn.close(); await interaction.response.send_message(f"✅ Промокод **{code}** створено!\n💰 +{money(money_amount)}\n🍆 {dick_amount:+d} см", ephemeral=True)


# ---------------- START ----------------

@bot.event
async def on_ready():
    init_db()
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
bot.run(TOKEN)
