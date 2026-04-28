import os
import logging
import telebot
from telebot import types, util

# ==================== SOZLAMALAR ====================
try:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    ADMIN_ID = int(os.environ["ADMIN_ID"])
except KeyError as e:
    print(f"❌ Xatolik: {e} topilmadi!")
    print("Railway Variables qismida BOT_TOKEN va ADMIN_ID ni kiriting!")
    exit(1)
except ValueError:
    print("❌ ADMIN_ID faqat raqam bo'lishi kerak!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ==================== KOMANDALAR ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
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

# ==================== KONTAKT ====================

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    cid = message.chat.id
    if user_data.get(cid, {}).get('step') != 'contact':
        return
    
    user_data[cid]['phone'] = message.contact.phone_number
    user_data[cid]['username'] = message.from_user.username
    user_data[cid]['first_name'] = message.from_user.first_name or ""
    user_data[cid]['step'] = 'name'
    
    bot.send_message(
        cid,
        "✅ Kontakt qabul qilindi.\n\n1️⃣ Ism familiyangizni to'liq kiriting:",
        reply_markup=types.ReplyKeyboardRemove()
    )

# ==================== ISM FAMILIYA ====================

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'name')
def handle_name(message):
    cid = message.chat.id
    text = message.text.strip()
    
    if len(text.split()) < 2:
        bot.reply_to(message, "⚠️ Iltimos, ism va familiyani to'liq yozing!\n\nMasalan: Ali Valiyev")
        return
    
    user_data[cid]['name'] = text
    user_data[cid]['step'] = 'group'
    bot.reply_to(message, "2️⃣ Guruhingizni to'liq ravishda kiriting:")

# ==================== GURUH ====================

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'group')
def handle_group(message):
    cid = message.chat.id
    user_data[cid]['group'] = message.text.strip()
    user_data[cid]['step'] = 'receipt'
    bot.reply_to(message, "3️⃣ To'lov chekini yuboring (rasm, PDF yoki boshqa fayl):")

# ==================== CHEK ====================

@bot.message_handler(content_types=['photo', 'document'], func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'receipt')
def handle_receipt(message):
    cid = message.chat.id
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    elif message.document:
        file_id = message.document.file_id
        file_type = 'document'
    else:
        bot.reply_to(message, "⚠️ Iltimos, rasm yoki fayl yuboring!")
        return
    
    user_data[cid]['receipt_id'] = file_id
    user_data[cid]['receipt_type'] = file_type
    user_data[cid]['step'] = 'month'
    
    # 12 oy tugmalari
    markup = types.InlineKeyboardMarkup(row_width=3)
    months = [
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
    ]
    buttons = [types.InlineKeyboardButton(m, callback_data=f"month_{m}") for m in months]
    markup.add(*buttons)
    
    bot.send_message(cid, "4️⃣ Qaysi oy uchun to'lov qilyapsiz?", reply_markup=markup)

# ==================== OY TANLASH ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("month_"))
def handle_month(call):
    cid = call.message.chat.id
    
    if cid not in user_data or user_data[cid].get('step') != 'month':
        bot.answer_callback_query(call.id, "⚠️ Eskirgan tugma. /start ni bosing.")
        return
    
    month = call.data.replace("month_", "")
    user_data[cid]['month'] = month
    user_data[cid]['step'] = 'waiting'
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "✅ Qabul qilindi. Tekshirilib, sizga javob yuboriladi.",
        cid,
        call.message.message_id
    )
    
    send_to_admin(cid)

# ==================== ADMINGA YUBORISH ====================

def send_to_admin(cid):
    data = user_data.get(cid)
    if not data:
        logging.error(f"User {cid} uchun ma'lumot topilmadi")
        return
    
    # HTML xavfsiz qilish
    safe_name = util.escape_html(data.get('name', 'N/A'))
    safe_group = util.escape_html(data.get('group', 'N/A'))
    safe_month = util.escape_html(data.get('month', 'N/A'))
    safe_phone = util.escape_html(data.get('phone', 'N/A'))
    username = data.get('username', '').strip()
    
    caption = (
        f"🔔 <b>Yangi to'lov so'rovi!</b>\n\n"
        f"👤 Ism familiya: {safe_name}\n"
        f"📞 Telefon: +{safe_phone}\n"
        f"📚 Guruh: {safe_group}\n"
        f"📅 To'lov oyi: {safe_month}\n"
        f"🆔 User ID: <code>{cid}</code>\n\n"
        f"Chekni tekshiring va javob bering."
    )
    
    # Tugmalar
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{cid}"),
        types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{cid}")
    )
    
    # Username tugmasi (faqat mavjud bo'lsa)
    if username and len(username) > 0:
        markup.add(
            types.InlineKeyboardButton("📞 Bog'lanish", url=f"https://t.me/{username}")
        )
    
    # Yuborish (xatoliklarga chidamli)
    try:
        if data['receipt_type'] == 'photo':
            bot.send_photo(ADMIN_ID, data['receipt_id'], caption=caption, parse_mode='HTML', reply_markup=markup)
        else:
            bot.send_document(ADMIN_ID, data['receipt_id'], caption=caption, parse_mode='HTML', reply_markup=markup)
        
        logging.info(f"✅ Admin {ADMIN_ID} ga xabar yuborildi (User: {cid})")
    
    except telebot.apihelper.ApiTelegramException as e:
        error_msg = str(e)
        logging.error(f"❌ Telegram API xatosi: {error_msg}")
        
        # Asosiy sabab: admin /start bosmagan
        if "bot can't initiate conversation" in error_msg.lower() or "forbidden" in error_msg.lower():
            bot.send_message(
                cid,
                "⚠️ Admin hali botga ulanmagan.\n"
                "Ma'lumotlaringiz saqlandi, tez orada javob beriladi."
            )
            logging.warning(f"🚨 Admin {ADMIN_ID} botga /start bosmagan!")
        
        # Username tugmasi muammosi
        elif "BUTTON_USER_PRIVACY_RESTRICTED" in error_msg or "BUTTON_URL_INVALID" in error_msg:
            # Tugmasiz qayta yuborish
            markup_safe = types.InlineKeyboardMarkup(row_width=2)
            markup_safe.add(
                types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{cid}"),
                types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{cid}")
            )
            try:
                if data['receipt_type'] == 'photo':
                    bot.send_photo(ADMIN_ID, data['receipt_id'], caption=caption, parse_mode='HTML', reply_markup=markup_safe)
                else:
                    bot.send_document(ADMIN_ID, data['receipt_id'], caption=caption, parse_mode='HTML', reply_markup=markup_safe)
                logging.info("✅ Tugmasiz xabar yuborildi")
            except Exception as retry_error:
                logging.error(f"❌ Qayta urinishda xato: {retry_error}")
                bot.send_message(cid, "⚠️ Texnik xatolik. Iltimos, keyinroq urinib ko'ring.")
        else:
            bot.send_message(cid, "⚠️ Xatolik yuz berdi. Admin bilan bog'laning.")
    
    except Exception as e:
        logging.error(f"❌ Kutilmagan xatolik: {e}")
        bot.send_message(cid, "⚠️ Texnik xatolik. /start dan qayta boshlang.")

# ==================== ADMIN JAVOBI ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_decision(call):
    # Faqat admin ruxsati
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Siz admin emassiz!", show_alert=True)
        return
    
    action, cid_str = call.data.split("_", 1)
    try:
        cid = int(cid_str)
    except:
        bot.answer_callback_query(call.id, "❌ Noto'g'ri ma'lumot")
        return
    
    if action == "approve":
        try:
            bot.send_message(cid, "🎉 Tabriklaymiz! Siz qabul qilindingiz.\n\nTo'lovingiz tasdiqlandi.")
            bot.edit_message_caption(
                caption=call.message.caption + "\n\n✅ <b>Tasdiqlandi</b>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='HTML'
            )
            bot.answer_callback_query(call.id, "✅ Foydalanuvchi tasdiqlandi!")
            logging.info(f"✅ User {cid} tasdiqlandi")
        except Exception as e:
            logging.error(f"Tasdiqlashda xato: {e}")
            bot.answer_callback_query(call.id, "⚠️ Xatolik yuz berdi")
    
    elif action == "reject":
        try:
            bot.send_message(
                cid,
                "❌ To'lovingiz rad etildi.\n\n"
                "Ma'lumotlarni tekshirib qayta yuboring yoki admin bilan bog'laning."
            )
            bot.edit_message_caption(
                caption=call.message.caption + "\n\n❌ <b>Rad etildi</b>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='HTML'
            )
            bot.answer_callback_query(call.id, "❌ Foydalanuvchi rad etildi!")
            logging.info(f"❌ User {cid} rad etildi")
        except Exception as e:
            logging.error(f"Rad etishda xato: {e}")
            bot.answer_callback_query(call.id, "⚠️ Xatolik yuz berdi")
    
    # Xotirani tozalash
    if cid in user_data:
        del user_data[cid]

# ==================== ISHGA TUSHIRISH ====================

if __name__ == "__main__":
    print("=" * 50)
    print("✅ Bot ishga tushdi!")
    print(f"📊 Admin ID: {ADMIN_ID}")
    print("=" * 50)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logging.error(f"❌ Bot to'xtadi: {e}")
