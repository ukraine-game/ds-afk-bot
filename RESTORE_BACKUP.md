# Відновлення бази з backup

Бот автоматично створює перевірені SQLite backup-файли у:

`<папка бази>/backups/`

На Railway з Volume `/data` це:

`/data/backups/`

Файли мають вигляд:

`bot_YYYYMMDD_HHMMSS_microseconds_auto.db`

Перед відновленням **зупини бота**, щоб він не писав у базу.

## Безпечний спосіб

1. Зроби копію поточного `/data/bot.db`, якщо він ще читається.
2. Вибери останній backup.
3. Перевір backup:

```bash
python -c "import sqlite3; c=sqlite3.connect('/data/backups/FILE.db'); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()"
```

Повинно бути:

`ok`

4. Заміни `/data/bot.db` перевіреним backup-файлом.
5. Запусти бота.

Бот також сам намагається відновити останній валідний backup, якщо основна база пошкоджена.
