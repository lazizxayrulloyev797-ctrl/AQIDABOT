import os
import telebot
from telebot import types

# ==================== ENVIRONMENT VARIABLES ====================
try:
    TOKEN = os.environ["BOT_TOKEN"]
    ADMIN_ID = int(os.environ["ADMIN_ID"])
except KeyError as e:
    print(f"❌ Xatolik: {e} topilmadi!")
    print("Railway Variables qismida BOT_TOKEN va ADMIN_ID ni kiriting!")
    exit(1)
except ValueError:
    print("❌ ADMIN_ID faqat raqam bo'lishi kerak!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

user_states = {}
user_info = {}

months = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", 
          "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_states[chat_id] = 'name'
    
    text = """👋 *Assalomu alaykum!*

*Aqida* guruhiga xush kelibsiz.

💳 *To'lov uchun kartalar:*

1️⃣ Uzcard:
    Ashur.A
    `5614 6816 2097 9942`

2️⃣ Visa:
    Hayitova X
    `4067 0700 0383 2248`

Quyidagi tartibda ma'lumot bering:

1️⃣ Ism va Familiyangizni to'liq yozing:"""
    
    bot.send_message(chat_id, text, parse_mode='Markdown')


# ================== MATNLI JAVOBLAR ==================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        return

    state = user_states[chat_id]

    if state == 'name':
        if len(message.text.strip().split()) < 2:
            bot.send_message(chat_id, "❗ *Iltimos, Ism va Familiyangizni to'liq yozing!*", parse_mode='Markdown')
            return
        user_info[chat_id] = {
            'full_name': message.text.strip(),
            'user_id': message.from_user.id,
            'username': message.from_user.username or "yo'q"
        }
        user_states[chat_id] = 'group'
        bot.send_message(chat_id, "2️⃣ *Qaysi guruhga qo'shilmoqchisiz?*", parse_mode='Markdown')

    elif state == 'group':
        user_info[chat_id]['group'] = message.text.strip()
        user_states[chat_id] = 'contact'
        
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(types.KeyboardButton("📱 Kontaktni ulashish", request_contact=True))
        
        bot.send_message(chat_id, "3️⃣ *Kontakt ma'lumotingizni ulashing* (telefon raqamingiz bilan)", 
                        reply_markup=markup, parse_mode='Markdown')


# ================== KONTAKT QABUL QILISH ==================
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    
    if chat_id not in user_states or user_states[chat_id] != 'contact':
        return

    contact = message.contact
    user_info[chat_id]['phone'] = contact.phone_number
    user_info[chat_id]['contact_name'] = contact.first_name

    # Kontakt tugmasini yashiramiz
    bot.send_message(chat_id, "✅ Kontakt qabul qilindi.", reply_markup=types.ReplyKeyboardRemove())
    
    user_states[chat_id] = 'file'
    bot.send_message(chat_id, "4️⃣ *To'lov chekini yuboring* (rasm, PDF yoki boshqa fayl)", parse_mode='Markdown')


# ================== FILE (Chek) ==================
@bot.message_handler(content_types=['photo', 'document'])
def handle_file(message):
    chat_id = message.chat.id
    
    if chat_id not in user_states or user_states[chat_id] != 'file':
        return

    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    file_type = "photo" if message.photo else "document"

    user_info[chat_id]['receipt'] = file_id
    user_info[chat_id]['receipt_type'] = file_type

    user_states[chat_id] = 'month'

    # 12 ta oy tugmalari
    markup = types.InlineKeyboardMarkup(row_width=3)
    for month in months:
        markup.add(types.InlineKeyboardButton(month, callback_data=f"month_{month}"))
    
    bot.send_message(chat_id, "5️⃣ *Qaysi oy uchun to'lov qilyapsiz?*", reply_markup=markup, parse_mode='Markdown')


# ================== OY TANLASH ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith("month_"))
def month_selected(call):
    chat_id = call.message.chat.id
    selected_month = call.data.split("_")[1]

    user_info[chat_id]['month'] = selected_month

    bot.answer_callback_query(call.id, f"{selected_month} tanlandi")
    bot.send_message(chat_id, "✅ *Qabul qilindi!* Tekshirilib sizga javob yuboriladi.", parse_mode='Markdown')
    
    send_to_admin(chat_id)
    user_states.pop(chat_id, None)


# ================== ADMINGA YUBORISH ==================
def send_to_admin(user_chat_id):
    data = user_info[user_chat_id]
    
    caption = f"""🔔 YANGI TO'LOV SO'ROVI

👤 Foydalanuvchi: {data['full_name']}
🔗 Username: @{data['username']}
📱 Telefon: {data.get('phone', 'Berilmagan')}
👥 Guruh: {data['group']}
📅 Oy: {data['month']}
🆔 User ID: {data['user_id']}"""

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"approve_{user_chat_id}"))
    markup.add(types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{user_chat_id}"))
    
    # Foydalanuvchi bilan bog'lanish tugmasi (xatoliklarga chidamli)
    if data.get('username') and data['username'] != "yo'q":
        try:
            markup.add(types.InlineKeyboardButton(
                "💬 Foydalanuvchi bilan bog'lanish", 
                url=f"https://t.me/{data['username']}"
            ))
        except:
            # Agar username xato bo'lsa, tugma qo'shilmaydi
            caption += f"\n\n⚠️ Username xato. User ID: {data['user_id']}"
    else:
        caption += f"\n\n⚠️ Foydalanuvchida username yo'q.\nU bilan bog'lanish uchun yuqoridagi User ID dan foydalaning."

    # Faylni yuborish (xatoliklarga chidamli)
    try:
        if data.get('receipt_type') == "photo":
            bot.send_photo(ADMIN_ID, data['receipt'], caption=caption, parse_mode=None, reply_markup=markup)
        else:
            bot.send_document(ADMIN_ID, data['receipt'], caption=caption, parse_mode=None, reply_markup=markup)
        print(f"✅ Admin {ADMIN_ID} ga xabar yuborildi (User: {user_chat_id})")
    
    except telebot.apihelper.ApiTelegramException as e:
        error_msg = str(e)
        print(f"❌ Telegram API xatosi: {error_msg}")
        
        # Asosiy muammo: admin /start bosmagan
        if "bot can't initiate conversation" in error_msg.lower() or "forbidden" in error_msg.lower():
            bot.send_message(
                user_chat_id,
                "⚠️ Admin hali botga ulanmagan.\n"
                "Ma'lumotlaringiz saqlandi, tez orada javob beriladi."
            )
            print(f"🚨 DIQQAT: Admin {ADMIN_ID} botga /start bosmagan!")
        
        # Username tugmasi muammosi
        elif "BUTTON_USER_PRIVACY_RESTRICTED" in error_msg or "BUTTON_URL_INVALID" in error_msg:
            # Tugmasiz qayta yuborish
            markup_safe = types.InlineKeyboardMarkup(row_width=1)
            markup_safe.add(types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"approve_{user_chat_id}"))
            markup_safe.add(types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{user_chat_id}"))
            
            try:
                if data.get('receipt_type') == "photo":
                    bot.send_photo(ADMIN_ID, data['receipt'], caption=caption, parse_mode=None, reply_markup=markup_safe)
                else:
                    bot.send_document(ADMIN_ID, data['receipt'], caption=caption, parse_mode=None, reply_markup=markup_safe)
                print("✅ Tugmasiz xabar yuborildi")
            except Exception as retry_error:
                print(f"❌ Qayta urinishda ham xatolik: {retry_error}")
                bot.send_message(user_chat_id, "⚠️ Texnik xatolik. Admin bilan bog'laning.")
        else:
            bot.send_message(user_chat_id, "⚠️ Xatolik yuz berdi. Keyinroq urinib ko'ring.")
    
    except Exception as e:
        print(f"❌ Kutilmagan xatolik: {e}")
        bot.send_message(user_chat_id, "⚠️ Texnik xatolik. /start dan qayta boshlang.")


# ================== ADMIN CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # Faqat admin ruxsati
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Siz admin emassiz!", show_alert=True)
        return
    
    if call.data.startswith("approve_"):
        user_id = int(call.data.split("_")[1])
        try:
            bot.send_message(user_id, "🎉 *Tabriklaymiz!* Siz qabul qilindingiz.", parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Qabul qilindi")
            # Caption yangilash
            try:
                bot.edit_message_caption(
                    caption=call.message.caption + "\n\n✅ QABUL QILINDI",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
            except:
                pass
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Xatolik: {e}")

    elif call.data.startswith("reject_"):
        user_id = int(call.data.split("_")[1])
        try:
            bot.send_message(user_id, "❌ To'lov rad etildi. Iltimos, ma'lumotlarni tekshirib qayta yuboring.", parse_mode='Markdown')
            bot.answer_callback_query(call.id, "❌ Rad etildi")
            # Caption yangilash
            try:
                bot.edit_message_caption(
                    caption=call.message.caption + "\n\n❌ RAD ETILDI",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
            except:
                pass
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Xatolik: {e}")


# ================== ISHGA TUSHIRISH ====================
if __name__ == "__main__":
    print("=" * 50)
    print("✅ Bot ishga tushdi!")
    print(f"📊 Admin ID: {ADMIN_ID}")
    print("=" * 50)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("\n⛔ Bot to'xtatildi")
    except Exception as e:
        print(f"❌ Xatolik: {e}")
