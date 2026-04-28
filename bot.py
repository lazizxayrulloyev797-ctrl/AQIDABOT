import os
import logging
import telebot
from telebot import types, util

# 🚨 Xatolikni oldini oluvchi o'zgaruvchilar
try:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    ADMIN_ID = int(os.environ["ADMIN_ID"])
except KeyError as e:
    raise SystemExit(f"❌ Environment variable topilmadi: {e}. Railway sozlamalarida BOT_TOKEN va ADMIN_ID ni kiriting!")
except ValueError:
    raise SystemExit("❌ ADMIN_ID faqat raqam bo'lishi kerak!")

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

# 🟢 /start buyrug'i
@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    user_data[cid] = {'step': 'contact'}
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("📞 Kontakt ulashish", request_contact=True))
    text = (
        "Iltimos avval shartlar bilan tanishib chiqing!\n\n"
        "💳 Karta raqam: 5614681620979942\n\n"
        "Boshlash uchun pastdagi tugma orqali kontaktingizni ulashing:"
    )
    bot.send_message(cid, text, reply_markup=markup)

# 0️⃣ Kontakt qabul qilish
@bot.message_handler(content_types=['contact'], func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'contact')
def get_contact(message):
    cid = message.chat.id
    user_data[cid]['phone'] = message.contact.phone_number
    user_data[cid]['username'] = message.from_user.username
    user_data[cid]['step'] = 'name'
    bot.send_message(cid, "✅ Kontakt qabul qilindi.\n1️⃣ Ism familiyangizni kiriting:", reply_markup=types.ReplyKeyboardRemove())

# 1️⃣ Ism familiya (tekshiruv bilan)
@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'name')
def get_name(message):
    text = message.text.strip()
    if len(text.split()) < 2:
        bot.reply_to(message, "⚠️ Iltimos, ism va familiyani to'liq yozing (masalan: Ali Valiyev).")
        return
    
    cid = message.chat.id
    user_data[cid]['name'] = text
    user_data[cid]['step'] = 'group'
    bot.reply_to(message, "2️⃣ Guruhingizni to'liq ravishda kiriting:")

# 2️⃣ Guruh
@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'group')
def get_group(message):
    cid = message.chat.id
    user_data[cid]['group'] = message.text.strip()
    user_data[cid]['step'] = 'receipt'
    bot.reply_to(message, "3️⃣ To'lov chekini yuboring (rasm, PDF yoki boshqa fayl ko'rinishida):")

# 3️⃣ Chek (istalgan fayl turi)
@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'receipt')
def get_receipt(message):
    cid = message.chat.id
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    else:
        file_id = message.document.file_id
        file_type = 'document'

    user_data[cid]['receipt_id'] = file_id
    user_data[cid]['receipt_type'] = file_type
    user_data[cid]['step'] = 'month'

    # 📅 12 oy tugmalari
    markup = types.InlineKeyboardMarkup(row_width=3)
    months = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
              "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]
    buttons = [types.InlineKeyboardButton(text=m, callback_data=f"month_{m}") for m in months]
    markup.add(*buttons)

    bot.send_message(cid, "4️⃣ Qaysi oy uchun to'lov?", reply_markup=markup)

# 📅 Oy tanlash
@bot.callback_query_handler(func=lambda call: call.data.startswith("month_"))
def handle_month(call):
    cid = call.message.chat.id
    if cid not in user_data or user_data[cid].get('step') != 'month':
        bot.answer_callback_query(call.id, "⚠️ Bu tugma eskirgan. /start ni bosing.")
        return

    month = call.data.split("_")[1]
    user_data[cid]['month'] = month
    user_data[cid]['step'] = 'waiting_admin'

    bot.answer_callback_query(call.id)
    bot.edit_message_text("✅ Qabul qilindi. Tekshirilib, sizga javob yuboriladi.", cid, call.message.message_id)

    send_to_admin(cid)

# 📤 Adminga yuborish (xatoliklarga chidamli)
def send_to_admin(cid):
    data = user_data[cid]
    safe_name = util.escape_html(data['name'])
    safe_group = util.escape_html(data['group'])
    safe_month = util.escape_html(data['month'])
    safe_phone = util.escape_html(data.get('phone', 'Noma\'lum'))
    username = data.get('username')

    caption = (
        f"🔔 <b>Yangi to'lov so'rovi!</b>\n\n"
        f"👤 Ism familiya: {safe_name}\n"
        f"📞 Telefon: {safe_phone}\n"
        f"📚 Guruh: {safe_group}\n"
        f"📅 To'lov oyi: {safe_month}\n"
        f"🆔 User ID: {cid}\n\n"
        f"Bot shu nomli foydalanuvchi to'lov qildi. Chekni tekshiring va unga ruxsat berishingizni kutmoqda."
    )

    # Asosiy tugmalar
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{cid}"),
        types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{cid}")
    )

    # Username borligini xavfsiz tekshirish
    if isinstance(username, str) and len(username.strip()) > 0 and username.strip().lower() not in ['none', 'null']:
        clean_username = username.strip().lstrip('@')
        try:
            markup.add(types.InlineKeyboardButton("📞 Foydalanuvchi bilan bog'lanish", url=f"https://t.me/{clean_username}"))
        except Exception:
            pass  # Tugma qo'shilmasa ham xabar yetkazilsin

    # Xabar yuborish (ikkita urinish)
    for attempt in range(2):
        try:
            if data['receipt_type'] == 'photo':
                bot.send_photo(ADMIN_ID, data['receipt_id'], caption=caption, parse_mode='HTML', reply_markup=markup)
            else:
                bot.send_document(ADMIN_ID, data['receipt_id'], caption=caption, parse_mode='HTML', reply_markup=markup)
            break
        except Exception as e:
            if "BUTTON_USER_PRIVACY_RESTRICTED" in str(e) or "BUTTON_URL_INVALID" in str(e):
                # Tugmani olib tashlab qayta urinish
                safe_markup = types.InlineKeyboardMarkup(row_width=2)
                safe_markup.add(
                    types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{cid}"),
                    types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{cid}")
                )
                caption += "\n🔗 Bog'lanish tugmasi Telegram siyosati tufayli bloklandi. Telefon/ID orqali bog'laning."
                if attempt == 0:
                    continue  # Qayta urinish
            logging.error(f"Admin xabar xatosi: {e}")
            bot.send_message(cid, "⚠️ Admin paneliga xabar yuborishda xatolik. Iltimos, admin bilan bog'laning.")
            break

# ✅❌ Admin tasdiqlash/rad etish
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_action(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Siz admin emassiz!", show_alert=True)
        return

    action, cid_str = call.data.split("_")
    try:
        cid = int(cid_str)
    except:
        bot.answer_callback_query(call.id, "❌ Noto'g'ri so'rov", show_alert=True)
        return

    if action == "approve":
        bot.send_message(cid, "🎉 Tabriklaymiz! Siz qabul qilindingiz. To'lovingiz tasdiqlandi.")
        try:
            bot.edit_message_caption(call.message.caption + "\n\n✅ Tasdiqlandi", call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
    else:
        bot.send_message(cid, "❌ To'lovingiz rad etildi. Ma'lumotlarni tekshirib qayta yuboring yoki admin bilan bog'laning.")
        try:
            bot.edit_message_caption(call.message.caption + "\n\n❌ Rad etildi", call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.answer_callback_query(call.id, "❌ Rad etildi!")

    # Xotirani tozalash
    if cid in user_data:
        del user_data[cid]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("✅ Bot ishga tushdi...")
    bot.infinity_polling()
