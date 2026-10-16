import os import logging import sqlite3 from datetime import datetime from telegram import ( Update, InlineKeyboardButton, InlineKeyboardMarkup, ) from telegram.ext import ( Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, ContextTypes, filters, )
logging.basicConfig( format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, ) logging.getLogger("httpx").setLevel(logging.WARNING)
TOKEN = os.getenv("BOT_TOKEN") DB_NAME = "trades.db"
ASSET, DIRECTION, RESULT, NOTES = range(4)
ASSETS = ["EUR/USD", "GBP/USD", "BTC/USD", "JP225"] DIRECTIONS = ["BUY", "SELL"] RESULTS = ["+3R", "+2R", "+1R", "0R", "-1R", "-2R", "-3R"]
def init_db(): with sqlite3.connect(DB_NAME) as conn: conn.execute(""" CREATE TABLE IF NOT EXISTS trades ( id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, asset TEXT NOT NULL, direction TEXT NOT NULL, result TEXT NOT NULL, notes TEXT ) """)
def main_menu(): keyboard = [ [InlineKeyboardButton("➕ Додати угоду", callback_data="add")], [ InlineKeyboardButton("📊 Статистика", callback_data="stats"), InlineKeyboardButton("📋 Останні угоди", callback_data="recent"), ], [InlineKeyboardButton("⚠️ Мої помилки", callback_data="mistakes")], ] return InlineKeyboardMarkup(keyboard)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text( "📈 Твій торговий журнал готовий!\n\n" "Веди угоди, результати та помилки.", reply_markup=main_menu(), )
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() action = query.data
if action == "add":
    keyboard = [
        [InlineKeyboardButton(asset, callback_data=f"asset:{asset}")]
        for asset in ASSETS
    ]
    await query.message.reply_text(
        "Обери актив:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

elif action.startswith("asset:"):
    context.user_data["asset"] = action.split(":", 1)[1]
    keyboard = [[
        InlineKeyboardButton("🟢 BUY", callback_data="dir:BUY"),
        InlineKeyboardButton("🔴 SELL", callback_data="dir:SELL"),
    ]]
    await query.message.reply_text(
        f"Актив: {context.user_data['asset']}\nОбери напрямок:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

elif action.startswith("dir:"):
    context.user_data["direction"] = action.split(":", 1)[1]
    keyboard = [
        [
            InlineKeyboardButton(result, callback_data=f"result:{result}")
            for result in RESULTS[i:i + 3]
        ]
        for i in range(0, len(RESULTS), 3)
    ]
    await query.message.reply_text(
        "Який результат угоди в R?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

elif action.startswith("result:"):
    context.user_data["result"] = action.split(":", 1)[1]
    await query.message.reply_text(
        "Напиши нотатку до угоди: причину входу, помилку або постав «-», якщо нотатки немає."
    )
    context.user_data["awaiting_notes"] = True

elif action == "stats":
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute(
            "SELECT result, COUNT(*) FROM trades GROUP BY result"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]

    wins = sum(count for result, count in rows if result.startswith("+"))
    losses = sum(count for result, count in rows if result.startswith("-"))
    winrate = wins / total * 100 if total else 0

    await query.message.reply_text(
        f"📊 Статистика\n\n"
        f"Угод: {total}\n"
        f"Прибуткових: {wins}\n"
        f"Збиткових: {losses}\n"
        f"Win rate: {winrate:.1f}%\n\n"
        "Результати зберігаються в R."
    )

elif action == "recent":
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute(
            "SELECT date, asset, direction, result, notes "
            "FROM trades ORDER BY id DESC LIMIT 10"
        ).fetchall()

    if not rows:
        await query.message.reply_text("Поки угод немає.")
    else:
        text = "📋 Останні угоди:\n\n"
[16.10.2026 14:11] Ігор Верещинський: for date, asset, direction, result, notes in rows:
            text += (
                f"🗓 {date}\n{asset} | {direction} | {result}\n"
                f"Нотатка: {notes or '-'}\n\n"
            )
        await query.message.reply_text(text)

elif action == "mistakes":
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute(
            "SELECT date, asset, result, notes FROM trades "
            "WHERE notes IS NOT NULL AND notes != '-' "
            "ORDER BY id DESC LIMIT 10"
        ).fetchall()

    if not rows:
        await query.message.reply_text(
            "Записів поки немає. Під час додавання угоди записуй помилки в нотатках."
        )
    else:
        text = "⚠️ Нотатки до угод:\n\n"
        for date, asset, result, notes in rows:
            text += f"{date} | {asset} | {result}\n{notes}\n\n"
        await query.message.reply_text(text)
async def save_notes(update: Update, context: ContextTypes.DEFAULT_TYPE): if not context.user_data.get("awaiting_notes"): return
notes = update.message.text.strip()
if not notes:
    await update.message.reply_text("Напиши текст або постав «-».")
    return

with sqlite3.connect(DB_NAME) as conn:
    conn.execute(
        "INSERT INTO trades (date, asset, direction, result, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            context.user_data.get("asset", "—"),
            context.user_data.get("direction", "—"),
            context.user_data.get("result", "0R"),
            notes,
        ),
    )

context.user_data.clear()
await update.message.reply_text(
    "✅ Угоду збережено!",
    reply_markup=main_menu(),
)
def main(): if not TOKEN: raise RuntimeError("Не задано змінну середовища BOT_TOKEN.")
init_db()
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(menu_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_notes))

app.run_polling()
if name == "main": main()
