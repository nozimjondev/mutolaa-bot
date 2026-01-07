import os
import re
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8505705288:AAGb9UMdymiy4eIZ-y-_rwVz5ph5hqkU9gE")
API_URL = os.getenv("API_URL", "http://localhost:8000/api")

# =============================================================================
# Helper functions
# =============================================================================

async def api_request(method: str, endpoint: str, data: dict = None, params: dict = None):
    url = f"{API_URL}/{endpoint}"
    async with aiohttp.ClientSession() as session:
        try:
            if method == "GET":
                async with session.get(url, params=params) as response:
                    return await response.json()
            elif method == "POST":
                async with session.post(url, json=data, params=params) as response:
                    return await response.json()
            elif method == "PUT":
                async with session.put(url, json=data, params=params) as response:
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, params=params) as response:
                    return await response.json()
        except Exception as e:
            return {"error": str(e)}

def parse_date(date_str: str) -> datetime:
    formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError("❌ Sana formati noto'g'ri! DD.MM.YYYY ishlating.")

# =============================================================================
# Commands
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Chat ID:", update.message.chat_id)
    user = update.effective_user
    await api_request("POST", "users", {
        "telegram_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    })
    await update.message.reply_text(f"""
🌟 Assalomu alaykum, {user.first_name}!
Sahifa sohili botiga xush kelibsiz! 📚

📋 Asosiy buyruqlar:
/add 50 - Bugungi natija
/add 05.01.2026 50 - Sana bilan
/edit 05.01.2026 60 - Natijani tahrirlash
/delete 05.01.2026 - Natijani o'chirish
/mystats - Statistikam
/leaderboard - Reyting
/setgoal daily 50 - Maqsad qo'yish
/reminder 20:00 - Eslatma vaqti
/report hafta - Haftalik hisobot
/report oy - Oylik hisobot
/help - Yordam
""")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📖 Mutolaa Bot qo'llanmasi

/add 50 - bugun uchun
/add 05.01.2026 50 - sana bilan
/edit 05.01.2026 60 - natijani tahrirlash
/delete 05.01.2026 - natijani o'chirish
/mystats - statistikangiz
/leaderboard - reyting
/setgoal daily 50 - maqsad qo'yish
/reminder 20:00 - eslatma vaqti
/report hafta - haftalik hisobot
/report oy - oylik hisobot
""")

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text("❌ Format noto'g'ri!\n/add 50 yoki /add 05.01.2026 50")
        return
    try:
        if len(args) == 1:
            date = datetime.now()
            pages = int(args[0])
        elif len(args) == 2:
            date = parse_date(args[0])
            pages = int(args[1])
        else:
            await update.message.reply_text("❌ Format noto'g'ri!")
            return
    except ValueError:
        await update.message.reply_text("❌ Sahifalar soni faqat butun son bo'lishi kerak!")
        return
    if pages <= 0 or pages > 500:
        await update.message.reply_text("❌ Sahifalar soni 1-500 oralig'ida bo'lishi kerak!")
        return
    if date.date() > datetime.now().date():
        await update.message.reply_text("❌ Kelajak sanasi uchun natija qo'shib bo'lmaydi!")
        return
    await api_request("POST", "reading-logs", {
        "date": date.isoformat(),
        "pages": pages,
        "book_id": None
    }, params={"telegram_id": user.id})
    user_data = await api_request("GET", f"users/by-telegram/{user.id}")
    if not user_data or "detail" in user_data:
        await update.message.reply_text("❌ Foydalanuvchi ma'lumotlari topilmadi! Avval /start buyrug'ini yuboring.")
        return
    await update.message.reply_text(f"""
✅ Tabriklaymiz!
📅 Sana: {date.strftime('%d.%m.%Y')}
📄 Sahifalar: {pages}
📚 Jami: {user_data.get('total_pages', 0)} sahifa
🔥 Ketma-ketlik: {user_data.get('current_streak', 0)} kun
""")

async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Format: /edit 05.01.2026 60")
        return
    try:
        date = parse_date(args[0])
        pages = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Format noto'g'ri!")
        return
    await api_request("PUT", f"reading-logs/{date.strftime('%Y-%m-%d')}", {"pages": pages}, params={"telegram_id": user.id})
    await update.message.reply_text(f"✅ Yangilandi: {date.strftime('%d.%m.%Y')} - {pages} sahifa")

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Format: /delete 05.01.2026")
        return
    try:
        date = parse_date(args[0])
    except ValueError:
        await update.message.reply_text("❌ Sana noto'g'ri!")
        return
    keyboard = [
        [InlineKeyboardButton("✅ Ha", callback_data=f"delete_confirm_{date.strftime('%Y-%m-%d')}"),
         InlineKeyboardButton("❌ Yo'q", callback_data="delete_cancel")]
    ]
    await update.message.reply_text(
        f"⚠️ {date.strftime('%d.%m.%Y')} uchun natijani o'chirishni tasdiqlaysizmi?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await api_request("GET", f"users/by-telegram/{user.id}")
    if not user_data or "detail" in user_data:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi!")
        return
    await update.message.reply_text(f"""
📊 Statistikangiz:
📚 Jami sahifalar: {user_data.get('total_pages', 0)}
🔥 Ketma-ketlik: {user_data.get('current_streak', 0)} kun
🎯 Maqsad: {user_data.get('daily_goal', 0)} sahifa/kun
""")

async def setgoal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Format: /setgoal kunlik 50 yoki /setgoal oylik 1500")
        return
    goal_type = args[0].lower()
    try:
        goal_value = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Maqsad soni noto'g'ri!")
        return
    if goal_type not in ["kunlik", "oylik"]:
        await update.message.reply_text("❌ Turi 'kunlik' yoki 'oylik' bo'lishi kerak!")
        return
    field = "daily_goal" if goal_type == "kunlik" else "monthly_goal"
    await api_request("PUT", f"users/{user.id}/update", {field: goal_value})
    await update.message.reply_text(f"✅ {goal_type.capitalize()} maqsad: {goal_value} sahifa")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    period = args[0] if args else "hafta"
    if period not in ["hafta", "oy"]:
        await update.message.reply_text("❌ Format: /report hafta yoki /report oy")
        return

    report = await api_request("GET", f"report/{period}")
    if not report or (isinstance(report, dict) and "error" in report):
        await update.message.reply_text("❌ Hisobotni olishda xatolik!")
        return

    if period == "hafta":
        text = "📊 Haftalik hisobot (Shanba–Juma):\n\n"
        for entry in report:
            medal = "🥇" if entry.get("winner") else ""
            status = "✅ G‘olib!" if entry.get("winner") else ""
            text += f"{medal} {entry['name']} – {entry['pages']} sahifa {status}\n"
    else:
        text = "📊 Oylik hisobot:\n\n"
        for entry in report:
            text += f"{entry['rank']}. {entry['name']} – {entry['pages']} sahifa\n"

    await update.message.reply_text(text)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    period = args[0] if args else "hafta"
    leaderboard = await api_request("GET", "leaderboard", params={"period": period, "limit": 10})

    if not leaderboard or (isinstance(leaderboard, dict) and "error" in leaderboard):
        await update.message.reply_text("❌ Reytingni olishda xatolik!")
        return

    text = f"🏆 {period.capitalize()} reytingi:\n\n"

    for entry in leaderboard:
        # Agar entry dict bo‘lsa
        if isinstance(entry, dict):
            rank = entry.get("rank")
            name = entry.get("name")
            pages = entry.get("pages")
        # Agar entry list/tuple bo‘lsa
        elif isinstance(entry, (list, tuple)):
            rank, name, pages = entry
        else:
            continue

        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else ""
        text += f"{medal} {rank}. {name} - {pages} sahifa\n"

    await update.message.reply_text(text)

async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await api_request("GET", f"users/by-telegram/{user.id}")
    if not user_data or "detail" in user_data:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi!")
        return
    current = user_data.get("current_streak", 0)
    longest = user_data.get("longest_streak", 0)
    await update.message.reply_text(f"""
🔥 Ketma-ketlik:
Hozirgi: {current} kun
Eng uzun: {longest} kun
""")

async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) != 1 or not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", args[0]):
        await update.message.reply_text("❌ Format: /reminder HH:MM (masalan: 20:00)")
        return
    time_str = args[0]
    await api_request("PUT", f"users/{user.id}/update", {"reminder_time": time_str})
    await update.message.reply_text(f"✅ Har kuni {time_str} da eslatma yuboriladi.")

# =============================================================================
# Callbacks
# =============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if query.data.startswith("delete_confirm_"):
        date_str = query.data.replace("delete_confirm_", "")
        await api_request("DELETE", f"reading-logs/{date_str}", params={"telegram_id": user.id})
        await query.edit_message_text("✅ Natija o'chirildi!")
    elif query.data == "delete_cancel":
        await query.edit_message_text("❌ Bekor qilindi")

# =============================================================================
# Reminder scheduler
# =============================================================================

async def send_reminders(app):
    users = await api_request("GET", "users/need-reminder")
    if isinstance(users, dict) and "error" in users:
        print("Reminder fetch error:", users["error"])
        return
    for u in users or []:
        try:
            await app.bot.send_message(
                chat_id=u["telegram_id"],
                text=f"🔔Asslomu alaykum  {u.get('first_name','')}! Bugun necha sahifa o'qiganingizni botga junatishingizni so'rab qolamiz! . Hurmat bilan Sahifa sohili bot! "
            )
        except Exception as e:
            print("Reminder send error:", e)


import requests
from telegram import Update
from telegram.ext import ContextTypes

API_URL = "http://localhost:8000/api"

async def send_announcements(application):
    try:
        response = requests.get(f"{API_URL}/announcements")
        announcements = response.json()
        if not announcements:
            return

        for ann in announcements:
            # faqat yuborilmagan e’lonlar
            if ann.get("sent_at") is None:
                message = ann["message"]

                # Guruhga yuborish
                group_id = -1002184957543  # o‘zingning guruh ID
                await application.bot.send_message(chat_id=group_id, text=f"📢 {message}")

                # Har bir foydalanuvchiga yuborish
                users = requests.get(f"{API_URL}/users").json()
                for u in users:
                    try:
                        await application.bot.send_message(chat_id=u["telegram_id"], text=f"📢 {message}")
                    except Exception as e:
                        print(f"Failed to send to {u['telegram_id']}: {e}")

                # ✅ API’da e’lonni yuborilgan deb belgilash
                requests.put(f"{API_URL}/announcements/{ann['id']}/mark-sent", json={})

    except Exception as e:
        print("Error fetching announcements:", e)



# =============================================================================
# Main
# =============================================================================

import asyncio 
from apscheduler.schedulers.asyncio import AsyncIOScheduler


import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("mystats", mystats_command))
    application.add_handler(CommandHandler("setgoal", setgoal_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CommandHandler("streak", streak_command))
    application.add_handler(CommandHandler("reminder", reminder_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    # ✅ Event loopni qo‘l bilan olish
    loop = asyncio.get_event_loop()
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(send_reminders, "interval", minutes=1, args=[application])
    scheduler.add_job(send_announcements, "interval", minutes=1, args=[application])

    scheduler.start()

    print("🤖 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
