# Discord Economy Bot — SAFE Railway Persistence Edition

Ця версія спеціально підготовлена так, щоб оновлення `bot.py` **не створювало нову порожню SQLite-базу** на Railway.

## 🔒 Головне

На Railway база повинна лежати на **Railway Volume**, а не всередині контейнера.

Рекомендована схема:

```text
Railway Service
├── код bot.py                 ← можна змінювати та redeploy
└── Volume /data               ← НЕ видаляється при redeploy
    ├── bot.db                 ← основна база
    └── backups/               ← автоматичні перевірені backup-и
```

У базі зберігаються, зокрема:
- баланс користувачів;
- розмір 🍆;
- cooldown `/daily` та `/dick`;
- адміністратори;
- промокоди;
- використані промокоди;
- налаштування бота;
- власники/ціни ролей;
- інвентар ролей;
- дані ігор у печеньку.

## 🚂 Railway — ОБОВ'ЯЗКОВО

### 1. Створи Volume

У Railway відкрий свій сервіс бота → **Volumes** → створи Volume.

Mount Path:

```text
/data
```

### 2. Variables

```env
DISCORD_TOKEN=твій_токен
GUILD_ID=ID_сервера
ADMIN_IDS=
DB_PATH=/data/bot.db
DB_BACKUP_DIR=/data/backups
DB_BACKUP_INTERVAL_SECONDS=300
MAX_DB_BACKUPS=30
```

`DB_PATH=/data/bot.db` — найважливіше.

### 3. Чому бот тепер не мовчить і не обнуляє дані

Якщо Railway визначений, але `DB_PATH` вказує не на `/data`, бот **зупиниться з помилкою** замість того, щоб непомітно працювати на ephemeral storage.

Це навмисний safety-stop.

## 🛡️ Що перевіряє бот

При запуску:

1. Перевіряє шлях до БД.
2. Перевіряє, що каталог існує та доступний для запису.
3. Перевіряє `PRAGMA integrity_check`.
4. Якщо основна БД пошкоджена — шукає останній валідний backup.
5. Якщо основної БД немає, але backup існує — відновлює backup замість створення порожньої бази.
6. Перед міграціями робить backup.
7. Виконує безпечні additive migrations для старих версій БД.
8. Після запуску знову перевіряє цілісність.
9. Створює перевірений startup backup.
10. Кожні 5 хвилин створює автоматичний backup.
11. Старі backup-и автоматично очищаються після ліміту `MAX_DB_BACKUPS`.
12. Кожен backup проходить окремий `integrity_check`.
13. Тимчасові backup-файли не підміняють справжній backup, поки файл не пройшов перевірку.
14. SQLite працює з `WAL`, `synchronous=FULL`, `busy_timeout=30s`.

## ♻️ Важливий захист від старих БД

Якщо в тебе вже є база старої версії бота, код не робить `DROP TABLE` і не стирає дані.

Відсутні колонки додаються через `ALTER TABLE`, тому старі:

```text
💰 гроші
🍆 см
👑 адміни
🎟️ промокоди
🏷️ ролі
```

залишаються.

Перед такою міграцією створюється `pre_migration` backup.

## 💾 Backup-и

За замовчуванням на Railway:

```text
/data/backups/
```

Наприклад:

```text
bot_20260828_180000_123456_auto.db
bot_20260828_180500_123456_auto.db
bot_20260828_181000_123456_auto.db
```

## 🔧 Перевірка БД вручну

Є файл:

```text
python db_check.py
```

На Railway:

```bash
python db_check.py
```

Він покаже:
- шлях до БД;
- існування файлу;
- розмір;
- `integrity_check`;
- journal mode;
- кількість користувачів;
- кількість промокодів;
- кількість використань та інших записів.

## ♻️ Відновлення

Дивись `RESTORE_BACKUP.md`.

ВАЖЛИВО: backup-и в `/data/backups` захищають від пошкодження/помилки основного `bot.db`, але **не є захистом від повного видалення самого Railway Volume**.

Для максимальної надійності рекомендується періодично копіювати backup-файли на окреме сховище.

## ⚠️ Не роби

Не видаляй Railway Volume.

Не став:

```env
DB_PATH=bot.db
```

на Railway.

Не додавай `bot.db` у Git як основний спосіб зберігання продакшн-даних.

Не запускай дві копії бота одночасно з однією SQLite-БД.

## Локальний запуск

```bash
py -m pip install -r requirements.txt
py bot.py
```

Локально, якщо `DB_PATH` не заданий, використовується:

```text
bot.db
```

поруч із `bot.py`.


## New in this build
- `/roulette` asks for the bet first, then the number. It no longer bets the whole balance.
- Coinflip uses an unbiased `random.choice(("Орел", "Решка"))` 50/50 result when no one-shot admin override is active.
- Coinflip admin rig is a one-shot global override: the first next coinflip by any user consumes it atomically.
- Admin panel has a private `🗄️ База даних` button that shows saved users, balances, sizes, promo codes/usages, roles, settings and cookie-game records.
- Persistent Railway database and verified automatic backups remain enabled.
