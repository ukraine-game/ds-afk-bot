# DS AFK Bot — FULL FIX v4

v4 adds a manual recovery command for the business notification-frequency menu.

## `!imp`
If the old DM with buttons shows `AFK BOT не відповідає у заданий час`, run `!imp` in a bot command channel. The bot sends a **fresh menu with the same frequency buttons** to your DM.

The new menu is persistent and registered before sending, so it survives bot restarts/reconnects.

Keep the existing Railway Volume and `/data/bot.db`.
