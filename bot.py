import os
import telebot
from telebot import types

# ================== ENVIRONMENT VARIABLES ==================
TOKEN = os.getenv('8583278824:AAGyTKKTBzJdihSVrrWpQPwacZ6r2-qwMoA')
ADMIN_ID = os.getenv('6590246089')

if not TOKEN or not ADMIN_ID:
    raise ValueError("❌ ERROR: 'TOKEN' yoki 'ADMIN_ID' muhit o'zgaruvchilari topilmadi!")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("❌ ERROR: 'ADMIN_ID' raqam bo'lishi kerak!")

bot = telebot.TeleBot(TOKEN)

# Foydalanuvchi holatlari
user_states = {}
user_info = {}

# Oylar ro'yxati
months = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
          "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_states[chat_id] = 'name'

    text = """👋 *Assalomu alaykum!*

*Aqida* guruhiga xush kelibsiz.

💳 To'lov uchun karta:
`5614 6816 2097 9942`

Quyidagi tartibda ma'lumotlarni kiriting:

1️⃣ Ism va Familiyangizni to'liq yozing."""
    
    bot.send_message(chat_id, text, parse_mode='Markdown')


# ================== MATN JAVOBLAR ==================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        return

    state = user_states[chat_id]

    # 1. Ism va Familiya
    if state == 'name':
        name_parts = message.text.strip().split()
        if len(name_parts) < 2:
            bot.send_message(chat_id, "❗ Iltimos, *Ism va Familiyangizni to'liq yozing!*", parse_mode='Markdown')
            return
        
        user_info[chat_id] = {
            'full_name': message.text.strip(),
            'user_id': message.from_user.id,
            'username': message.from_user.username or "yo'q"
        }
        user_states[chat_id] = 'group'
        bot.send_message(chat_id, "2️⃣ *Guruhingizni to'liq kiriting:* (masalan: Yangi boshlovchilar)", parse_mode='Markdown')

    # 2. Guruh
    elif state == 'group':
        user_info[chat_id]['group'] = message.text.strip()
        user_states[chat_id] = 'contact'

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(types.KeyboardButton("📱 Kontaktni ulashish", request_contact=True))
        
        bot.send_message(chat_id, "3️⃣ *Telefon raqamingizni ulashing*", 
                         reply_markup=markup, parse_mode='Markdown')


# ================== KONTAKT QABUL QILISH ==================
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    if user_states.get(chat_id) != 'contact':
        return

    contact = message.contact
    user_info[chat_id]['phone'] = contact.phone_number

    bot.send_message(chat_id, "✅ Kontakt qabul qilindi.", reply_markup=types.ReplyKeyboardRemove())
    user_states[chat_id] = 'file'
    
    bot.send_message(chat_id, "4️⃣ *To'lov chekini yuboring* (rasm, PDF yoki hamma narsa)", parse_mode='Markdown')


# ================== CHEK QABUL QILISH ==================
@bot.message_handler(content_types=['photo', 'document'])
def handle_file(message):
    chat_id = message.chat.id
    if user_states.get(chat_id) != 'file':
        return

    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    file_type = "photo" if message.photo else "document"

    user_info[chat_id]['receipt'] = file_id
    user_info[chat_id]['receipt_type'] = file_type

    user_states[chat_id] = 'month'

    # Oy tanlash tugmalari
    markup = types.InlineKeyboardMarkup(row_width=3)
    for month in months:
        markup.add(types.InlineKeyboardButton(month, callback_data=f"month_{month}"))
    
    bot.send_message(chat_id, "5️⃣ *Qaysi oy uchun to'lov qildingiz?*", reply_markup=markup)


# ================== OY TANLASH ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith("month_"))
def month_selected(call):
    chat_id = call.message.chat.id
    selected_month = call.data.split("_", 1)[1]  # _dan keyin barcha matn

    user_info[chat_id]['month'] = selected_month
    bot.answer_callback_query(call.id, f"{selected_month} tanlandi")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="✅ Ma'lumotlaringiz qabul qilindi!\nTekshirilib javob beriladi."
    )
    
    send_to_admin(chat_id)
    user_states.pop(chat_id, None)


# ================== ADMINGA YUBORISH ==================
def send_to_admin(user_chat_id):
    data = user_info[user_chat_id]
    
    caption = f"""🔔 YANGI TO'LOV SO'ROVI

👤 Foydalanuvchi: {data['full_name']}
🔗 @: @{data['username']}
📱 Telefon: {data.get('phone', 'Ko‘rsatilmagan')}
👥 Guruh: {data['group']}
📅 Oy: {data['month']}
🆔 ID: {data['user_id']}"""

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"approve_{user_chat_id}"))
    markup.add(types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{user_chat_id}"))
    
    # Username bo'lsa - link, yo'qsa - faqat ID ko'rsatiladi
    if data['username'] and data['username'] != "yo'q":
        markup.add(types.InlineKeyboardButton(
            "💬 Foydalanuvchi bilan bog'lanish", 
            url=f"https://t.me/{data['username']}"
        ))
    else:
        caption += f"\n\n⚠️ Username mavjud emas. User ID: {data['user_id']}"

    try:
        if data['receipt_type'] == 'photo':
            bot.send_photo(ADMIN_ID, data['receipt'], caption=caption, reply_markup=markup)
        else:
            bot.send_document(ADMIN_ID, data['receipt'], caption=caption, reply_markup=markup)
    except Exception as e:
        bot.send_message(ADMIN_ID, f"XATO: Chek yuborilmadi. {str(e)}\nUser ID: {data['user_id']}")


# ================== ADMIN CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data.startswith("approve_"):
            user_id = int(call.data.split("_")[1])
            bot.send_message(user_id, "🎉 *Siz qabul qilindingiz!* Guruhga qo'shilishingiz mumkin.", parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Qabul qilindi")

        elif call.data.startswith("reject_"):
            user_id = int(call.data.split("_")[1])
            bot.send_message(user_id, "❌ Afsuski, to'lovingiz rad etildi. Qayta tekshiring va yuboring.", parse_mode='Markdown')
            bot.answer_callback_query(call.id, "❌ Rad etildi")
    except Exception as e:
        bot.answer_callback_query(call.id, "Xato yuz berdi!")
        print(f"Callback error: {e}")


print("🚀 Aqida Bot muvaffaqiyatli ishga tushdi...")
bot.infinity_polling()
