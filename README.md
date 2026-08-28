# Discord Economy Bot — Railway + SQLite Volume

## What is used
- Python + discord.py
- SQLite (`bot.db`)
- Railway persistent Volume for the database
- No MySQL required
- No database file should be committed to GitHub

## Commands
### User
- `/dick` — daily size change; first-ever use is always positive.
- `/profile [user]` — profile.
- `/money` — balance.
- `/daily` — daily reward.
- `/pay member amount` — transfer money.
- `/top` — top 3 by balance.
- `/help` — help.
- `/promo` — activate promo.
- `/coinflip bet` — coin flip.
- `/roulette bet number` — roulette, number 0–36.
- `/cookie user bet` — cookie-game proposal, minimum 1000.
- `/role_create` — create a custom role.
- `/role_sell role price` — sell a custom role.
- `/role_shop` — shop with Refresh and Buy buttons.
- `/role_buy role_id` — buy a role by ID.
- `!pecenka` — only inside an active cookie-game channel.

### Admin
All admin commands are marked `🔒 Адмін` in Discord:
- `/admin`
- `/givemoney`
- `/setmoney`
- `/setdick`
- `/setadmin`
- `/promo_create`

Admin panel contains:
- Видати гроші
- Встановити гроші
- Встановити розмір
- Накрутка рулетки
- Накрутка монетки

The roulette/coinflip rig is consumed by the next corresponding game and then removed.

## Important Discord settings
Enable **Message Content Intent** in the Discord Developer Portal because `!pecenka` and cookie-game message counting use message content.

The bot needs at least:
- View Channels
- Send Messages
- Embed Links
- Read Message History
- Manage Channels (for cookie-game private channels)
- Manage Roles (for role features)

The bot's highest role must be above roles it creates/manages.

## Local run
1. Copy `.env.example` to `.env`.
2. Put your token/server ID/admin IDs in `.env`.
3. For local use, change `DB_PATH` to `bot.db` or remove it.
4. Install dependencies:
```bash
py -m pip install -r requirements.txt
```
5. Run:
```bash
py bot.py
```

## Railway deployment
1. Push the project to GitHub. Do **not** push `.env` or `bot.db`.
2. Create a Railway project and deploy the GitHub repository.
3. Add Variables:
   - `DISCORD_TOKEN`
   - `GUILD_ID`
   - `ADMIN_IDS` (optional)
   - `DB_PATH=/data/bot.db`
4. Add a Railway **Volume** to the bot service and mount it at `/data`.
5. Set the start command to:
```bash
python bot.py
```
6. Deploy/redeploy.

The bot creates the SQLite database and tables automatically on first start. Because `bot.db` is on the persistent Volume, balances, dick sizes, roles, promo uses, admin flags, rigged results and cookie-game records survive container restarts and redeploys.

## GitHub .gitignore
Use:
```gitignore
.env
bot.db
*.db
__pycache__/
*.pyc
```
