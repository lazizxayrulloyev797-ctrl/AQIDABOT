import os
import telebot
from telebot import types

# ================== RAILWAY UCHUN ENV VARIABLES ==================
TOKEN = os.getenv('8583278824:AAGyTKKTBzJdihSVrrWpQPwacZ6r2-qwMoA')
ADMIN_ID = int(os.getenv('6590246089'))

if not TOKEN or not ADMIN_ID:
    print("❌ XATO: TOKEN yoki ADMIN_ID topilmadi!")
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

💳 To'lov uchun karta:
`5614 6816 2097 9942`

1. Ism va Familiyangizni to'liq yozing:"""
    
    bot.send_message(chat_id, text, parse_mode='Markdown')


# ================== MATNLI JAVOGLAR ==================
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
        bot.send_message(chat_id, "2. *Guruhizni to'liq ravishda kiriting*", parse_mode='Markdown')

    elif state == 'group':
        user_info[chat_id]['group'] = message.text.strip()
        user_states[chat_id] = 'contact'
        
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(types.KeyboardButton("📱 Kontaktni ulashish", request_contact=True))
        
        bot.send_message(chat_id, "3. *Kontakt ma'lumotingizni ulashing*", 
                        reply_markup=markup, parse_mode='Markdown')


# ================== KONTAKT ==================
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    if user_states.get(chat_id) != 'contact':
        return

    contact = message.contact
    user_info[chat_id]['phone'] = contact.phone_number

    bot.send_message(chat_id, "✅ Kontakt qabul qilindi.", reply_markup=types.ReplyKeyboardRemove())
    
    user_states[chat_id] = 'file'
    bot.send_message(chat_id, "4. *To'lov chekini yuboring* (rasm, PDF yoki boshqa fayl)", parse_mode='Markdown')


# ================== FILE (Chek) ==================
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

    markup = types.InlineKeyboardMarkup(row_width=3)
    for month in months:
        markup.add(types.InlineKeyboardButton(month, callback_data=f"month_{month}"))
    
    bot.send_message(chat_id, "5. *Qaysi oy uchun to'lov qilyapsiz?*", reply_markup=markup, parse_mode='Markdown')


# ================== OY TANLASH ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith("month_"))
def month_selected(call):
    chat_id = call.message.chat.id
    selected_month = call.data.split("_")[1]

    user_info[chat_id]['month'] = selected_month

    bot.answer_callback_query(call.id, f"{selected_month} tanlandi")
    bot.send_message(chat_id, "✅ *Qabul qilindi!* Tekshirilib javob yuboriladi.", parse_mode='Markdown')
    
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
    
    if data.get('username') and data['username'] != "yo'q":
        markup.add(types.InlineKeyboardButton(
            "💬 Foydalanuvchi bilan bog'lanish", 
            url=f"https://t.me/{data['username']}"
        ))
    else:
        caption += f"\n\n⚠️ Username yo'q. User ID: {data['user_id']}"

    if data.get('receipt_type') == "photo":
        bot.send_photo(ADMIN_ID, data['receipt'], caption=caption, parse_mode=None, reply_markup=markup)
    else:
        bot.send_document(ADMIN_ID, data['receipt'], caption=caption, parse_mode=None, reply_markup=markup)


# ================== ADMIN CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("approve_"):
        user_id = int(call.data.split("_")[1])
        bot.send_message(user_id, "🎉 *Tabriklaymiz!* Siz qabul qilindingiz.", parse_mode='Markdown')
        bot.answer_callback_query(call.id, "Qabul qilindi")

    elif call.data.startswith("reject_"):
        user_id = int(call.data.split("_")[1])
        bot.send_message(user_id, "❌ To'lov rad etildi.", parse_mode='Markdown')
        bot.answer_callback_query(call.id, "Rad etildi")


print("✅ Aqida Bot Railway da ishga tushdi...")
bot.infinity_polling()
