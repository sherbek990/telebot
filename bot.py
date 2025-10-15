import telebot
from telebot import types
import json
import os

BOT_TOKEN = "8028224751:AAEFTNP3yJyG4f_RS7NsJ9dtjCZjmsbLRHc"  # <-- bu yerga bot tokeningizni yozing
CHANNEL_USERNAME = "@anidreamuz"  # <-- bu yerga kanal usernomi yoki chat_id
ADMIN_IDS = [8382153274]  # <-- bu yerga admin Telegram ID

DATA_FILE = "anime_db.json"
bot = telebot.TeleBot(BOT_TOKEN)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"anime": [], "next_id": 1}, f, ensure_ascii=False, indent=2)

def load_db():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("creator", "administrator", "member")
    except:
        return False

@bot.message_handler(commands=["start"])
def start(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📺 Anime ko‘rish", callback_data="watch_list"))
    kb.add(types.InlineKeyboardButton("🔔 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"))
    bot.reply_to(m, "Salom! Anime ko‘rish uchun kanalga obuna bo‘ling va pastdagi tugmani bosing 👇", reply_markup=kb)

admin_temp = {}

@bot.message_handler(commands=["upload"])
def upload_cmd(m):
    if m.from_user.id not in ADMIN_IDS:
        bot.reply_to(m, "Bu buyruq faqat adminlar uchun.")
        return
    bot.reply_to(m, "Anime faylini yoki YouTube linkini yuboring.\nYuborganingizdan so‘ng /save yozing.")
    admin_temp[m.from_user.id] = {}

@bot.message_handler(commands=["save"])
def save_cmd(m):
    uid = m.from_user.id
    if uid not in ADMIN_IDS or uid not in admin_temp or not admin_temp[uid]:
        bot.reply_to(m, "Avval anime yuboring va keyin /save yozing.")
        return

    db = load_db()
    nid = db["next_id"]
    temp = admin_temp[uid]
    entry = {
        "id": nid,
        "title": temp.get("title", f"Anime {nid}"),
        "type": temp["type"],
        "file_id": temp.get("file_id"),
        "link": temp.get("link")
    }
    db["anime"].append(entry)
    db["next_id"] += 1
    save_db(db)

    # --- 🆕 KANALGA POST TASHLAYDI ---
    try:
        watch_button = types.InlineKeyboardMarkup()
        watch_button.add(types.InlineKeyboardButton("▶️ Tomosha qilish", url=f"https://t.me/{bot.get_me().username}?start=watch{nid}"))
        caption = f"📢 **Yangi Anime:** {entry['title']}"
        if entry["type"] == "video" and entry.get("file_id"):
            bot.send_video(CHANNEL_USERNAME, entry["file_id"], caption=caption, reply_markup=watch_button, parse_mode="Markdown")
        elif entry["type"] == "link":
            bot.send_message(CHANNEL_USERNAME, f"{caption}\n\n🔗 {entry['link']}", reply_markup=watch_button, parse_mode="Markdown")
        bot.send_message(uid, f"✅ Anime saqlandi va kanalga post joylandi!")
    except Exception as e:
        bot.send_message(uid, f"⚠️ Kanalga post joylab bo‘lmadi: {e}")

    admin_temp.pop(uid, None)

@bot.message_handler(content_types=["video", "text"])
def handle_uploads(m):
    uid = m.from_user.id
    if uid not in ADMIN_IDS or uid not in admin_temp:
        return

    if m.content_type == "video":
        admin_temp[uid] = {"type": "video", "file_id": m.video.file_id, "title": m.video.file_name or "Video"}
        bot.reply_to(m, "🎬 Video qabul qilindi. Endi /save yozing.")
    elif m.content_type == "text":
        text = m.text.strip()
        admin_temp[uid] = {"type": "link", "link": text, "title": text}
        bot.reply_to(m, "🔗 Link qabul qilindi. Endi /save yozing.")

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    data = c.data
    if data == "watch_list":
        user_id = c.from_user.id
        if not is_subscribed(user_id):
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"))
            bot.send_message(user_id, "Avval kanalga obuna bo‘ling 👇", reply_markup=kb)
            return

        db = load_db()
        kb = types.InlineKeyboardMarkup(row_width=1)
        for it in db["anime"]:
            kb.add(types.InlineKeyboardButton(it["title"], callback_data=f"anime_{it['id']}"))
        bot.send_message(user_id, "Tanlang 👇", reply_markup=kb)

    elif data.startswith("anime_"):
        aid = int(data.split("_")[1])
        user_id = c.from_user.id
        if not is_subscribed(user_id):
            bot.send_message(user_id, "Avval kanalga obuna bo‘ling 👇")
            return

        db = load_db()
        anime = next((x for x in db["anime"] if x["id"] == aid), None)
        if not anime:
            bot.send_message(user_id, "Bu anime topilmadi.")
            return

        if anime["type"] == "video":
            bot.send_video(user_id, anime["file_id"], caption=anime["title"])
        elif anime["type"] == "link":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("▶️ Ko‘rish", url=anime["link"]))
            bot.send_message(user_id, anime["title"], reply_markup=kb)

print("Bot ishga tushdi...")
bot.infinity_polling()
