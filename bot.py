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

    CREATE TABLE IF NOT EXISTS role_inventory (
        user_id INTEGER NOT NULL,
        role_id INTEGER NOT NULL,
        added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, role_id)
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

@bot.tree.command(name="dick", description="Щодня змінити свій розмір пісюна")
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
        "🎁 Щоденний бонус", f"🎁 Ти отримав `{money(DAILY_REWARD)}` 💰!", discord.Color.gold()
    ))


# ---------------- TOP / HELP ----------------

@bot.tree.command(name="top", description="Показати топ-3 користувачів за балансом")
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


@bot.tree.command(name="coinflip", description="Ставка на орла або решку")
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

@bot.tree.command(name="roulette", description="Спробувати вгадати випадкове число та примножити баланс")
async def roulette(interaction: discord.Interaction):
    if not normal_channel_only(interaction):
        return await reject_wrong_channel(interaction)
    await interaction.response.send_message(
        embed=embed(
            "Рулетка",
            "Бот загадає випадкове число. Якщо ти вгадаєш його, ставка помножиться на коефіцієнт. Якщо ні — ставка буде програна.\n\n"
            "**Рівні складності:**\n"
            "Легкий: від 1 до 3 — коефіцієнт X3\n"
            "Середній: від 1 до 5 — коефіцієнт X5\n"
            "Важкий: від 1 до 10 — коефіцієнт X10\n"
            "Неможливий: від 1 до 50 — коефіцієнт X1000\n\n"
            "Спочатку обери рівень складності."
        ),
        view=RouletteDifficultyView()
    )

class RouletteDifficultyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def choose(self, interaction: discord.Interaction, low: int, high: int, multiplier: int, label: str):
        if not normal_channel_only(interaction):
            return await reject_wrong_channel(interaction)
        u = get_user(interaction.user.id, interaction.user.name)
        if u["balance"] <= 0:
            return await interaction.response.send_message("Недостатньо грошей. Потрібен позитивний баланс.", ephemeral=True)

        await interaction.response.send_message(
            embed=embed(
                "Рулетка",
                f"Ти обрав рівень **{label}**.\nЗагадай число від **{low}** до **{high}** і напиши його нижче одним повідомленням.",
            ),
            ephemeral=True
        )

        def check(m: discord.Message):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id

        try:
            msg = await bot.wait_for("message", timeout=60, check=check)
            guess = int(msg.content.strip())
            if not low <= guess <= high:
                return await interaction.followup.send(f"Число має бути від {low} до {high}.", ephemeral=True)
        except (asyncio.TimeoutError):
            return await interaction.followup.send("Час на відповідь вичерпано.", ephemeral=True)
        except ValueError:
            return await interaction.followup.send("Потрібно написати число.", ephemeral=True)

        # Ставка дорівнює всьому поточному балансу користувача.
        u = get_user(interaction.user.id, interaction.user.name)
        bet = u["balance"]
        money_add(interaction.user.id, -bet)
        await interaction.followup.send(embed=embed("Рулетка", "Бот думає над числом..."))

        await asyncio.sleep(2)
        forced = get_setting("roulette_next")
        if forced is not None:
            try:
                forced_number = int(forced)
            except ValueError:
                forced_number = None
            if forced_number is not None and low <= forced_number <= high:
                result = forced_number
            else:
                result = random.randint(low, high)
            delete_setting("roulette_next")
        else:
            result = random.randint(low, high)

        if result == guess:
            winnings = bet * multiplier
            money_add(interaction.user.id, winnings)
            desc = (
                f"Число **{result}**!\n\n"
                f"Вітаю, ти вгадав!\n"
                f"Твоя ставка **{money(bet)}** перетворилась на **{money(winnings)}**.\n"
                f"Коефіцієнт: **X{multiplier}**."
            )
            color = discord.Color.green()
        else:
            desc = (
                f"Число **{result}**!\n\n"
                f"На жаль, ти не вгадав.\n"
                f"Ти програв **{money(bet)}**."
            )
            color = discord.Color.red()

        await interaction.followup.send(embed=embed("Результат рулетки", desc, color))

    @discord.ui.button(label="Легкий", style=discord.ButtonStyle.success)
    async def easy(self, interaction, button):
        await self.choose(interaction, 1, 3, 3, "Легкий")

    @discord.ui.button(label="Середній", style=discord.ButtonStyle.primary)
    async def medium(self, interaction, button):
        await self.choose(interaction, 1, 5, 5, "Середній")

    @discord.ui.button(label="Важкий", style=discord.ButtonStyle.danger)
    async def hard(self, interaction, button):
        await self.choose(interaction, 1, 10, 10, "Важкий")

    @discord.ui.button(label="Неможливий", style=discord.ButtonStyle.secondary)
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

@bot.tree.command(name="inventory", description="Переглянути інвентар ролей")
async def inventory(interaction: discord.Interaction):
    if not normal_channel_only(interaction): return await reject_wrong_channel(interaction)
    if not interaction.guild: return await interaction.response.send_message("Тільки на сервері.", ephemeral=True)
    await show_inventory(interaction)

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
        set_setting("coinflip_next", mapping[value]); await interaction.response.send_message(f"Наступного разу монетка покаже {mapping[value]}.", ephemeral=True)

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

    @discord.ui.button(label="Надіслати повідомлення", style=discord.ButtonStyle.secondary, row=3)
    async def msg_send_btn(self, interaction, button):
        if await self.check(interaction):
            await interaction.response.send_modal(MsgSendModal())

@bot.tree.command(name="admin", description="🔒 Адмін-панель")
async def admin(interaction: discord.Interaction):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    await interaction.response.send_message(
        embed=embed("Адмін-панель", "Панель доступна адміністраторам.\nВласник також може призначати та знімати адміністраторів.", discord.Color.dark_red()),
        view=AdminView(), ephemeral=True
    )

@bot.tree.command(name="givemoney", description="🔒 Видати гроші користувачу")
@app_commands.describe(user="Користувач", amount="Кількість")
async def givemoney(interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1, MAX_BET]):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    money_add(user.id, amount); await interaction.response.send_message(f"{user.mention} отримав {money(amount)}.", ephemeral=True)

@bot.tree.command(name="setmoney", description="🔒 Встановити баланс користувачу")
@app_commands.describe(user="Користувач", amount="Новий баланс")
async def setmoney(interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 0, MAX_BET]):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    old = get_user(user.id, user.name)["balance"]; money_set(user.id, amount)
    await interaction.response.send_message(f"Баланс {user.mention}: {money(old)} → {money(amount)}.", ephemeral=True)

@bot.tree.command(name="setdick", description="🔒 Встановити розмір користувачу")
@app_commands.describe(user="Користувач", size="Новий розмір")
async def setdick(interaction: discord.Interaction, user: discord.Member, size: int):
    if not is_admin(interaction.user.id): return await admin_denied(interaction)
    old = get_user(user.id, user.name)["dick_size"]; dick_set(user.id, size)
    await interaction.response.send_message(f"Розмір {user.mention}: {old} см → {size} см.", ephemeral=True)

@bot.tree.command(name="giveadmin", description="🔒 Призначити адміністратора")
@app_commands.describe(user="Користувач")
async def giveadmin(interaction: discord.Interaction, user: discord.Member):
    if not is_owner(interaction.user.id): return await admin_denied(interaction)
    await give_admin(interaction, user)

@bot.tree.command(name="takeadmin", description="🔒 Зняти адміністратора")
@app_commands.describe(user="Користувач")
async def takeadmin(interaction: discord.Interaction, user: discord.Member):
    if not is_owner(interaction.user.id): return await admin_denied(interaction)
    await take_admin(interaction, user)

@bot.tree.command(name="setadmin", description="🔒 Змінити статус адміністратора")
@app_commands.describe(user="Користувач", enabled="True — видати, False — забрати")
async def setadmin(interaction: discord.Interaction, user: discord.Member, enabled: bool):
    if not is_owner(interaction.user.id):
        return await admin_denied(interaction)
    if enabled:
        await give_admin(interaction, user)
    else:
        await take_admin(interaction, user)

@bot.tree.command(name="msg_send", description="🔒 Надіслати повідомлення користувачу в лс")
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
