import telebot
import random
import os
import psycopg2
from psycopg2 import pool
from telebot import types
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisiga (environment variable) kiritilmagan!")
bot = telebot.TeleBot(TOKEN)

# Railway provides DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL muhit o'zgaruvchisiga kiritilmagan!")

# Initialize Connection Pool
try:
    db_pool = pool.ThreadedConnectionPool(1, 20, DATABASE_URL)
except Exception as e:
    print(f"PostgreSQL ulanishida xatolik: {e}")
    exit(1)

# Database Helper Function
def execute_query(query, params=None, fetch=None, commit=False):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if commit:
                conn.commit()
            if fetch == "all":
                return cursor.fetchall()
            elif fetch == "one":
                return cursor.fetchone()
    except Exception as e:
        print(f"DB Error: {e}")
        if commit:
            conn.rollback()
    finally:
        db_pool.putconn(conn)

# ================= DATABASE =================

def init_db():
    execute_query("""
    CREATE TABLE IF NOT EXISTS words(
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        unit TEXT,
        eng TEXT,
        uzb TEXT
    )
    """, commit=True)
    
    execute_query("""
    CREATE TABLE IF NOT EXISTS stats(
        user_id BIGINT PRIMARY KEY,
        tests INTEGER,
        correct INTEGER,
        wrong INTEGER
    )
    """, commit=True)

init_db()

# ================= VARIABLES =================

user_state = {}
current_unit = {}
quiz_sessions = {}

# ================= MENUS =================

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ So'z qo‘shish", "📝 Test Quiz")
    markup.row("✍️ Writing Quiz", "📊 Statistika")
    markup.row("❌ Clear All")
    return markup

def back_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Orqaga")
    return markup

def reset_user(chat_id):
    user_state.pop(chat_id, None)

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):
    execute_query(
        "INSERT INTO stats(user_id,tests,correct,wrong) VALUES(%s,%s,%s,%s) ON CONFLICT (user_id) DO NOTHING",
        (message.chat.id, 0, 0, 0),
        commit=True
    )

    reset_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👋 Salom!\n\nBu bot orqali inglizcha so‘zlarni unit bo‘yicha o‘rganishingiz mumkin.",
        reply_markup=main_menu()
    )

# ================= ADD WORD =================

@bot.message_handler(func=lambda m: m.text == "➕ So'z qo‘shish")
def add_words(message):
    user_state[message.chat.id] = "wait_unit"
    bot.send_message(
        message.chat.id,
        "📂 Iltimos unit nomini kiriting.\nMasalan: Unit 1, Travel, Food",
        reply_markup=back_menu()
    )

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "wait_unit")
def get_unit(message):
    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Bosh sahifa", reply_markup=main_menu())
        return

    current_unit[message.chat.id] = message.text.strip()
    user_state[message.chat.id] = "wait_words"

    bot.send_message(
        message.chat.id,
        "So‘zlarni quyidagi formatda yuboring:\n\nenglish = uzbek\n\nMasalan:\napple = olma\nbook = kitob",
        reply_markup=back_menu()
    )

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "wait_words")
def save_words(message):
    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Bosh sahifa", reply_markup=main_menu())
        return

    unit = current_unit.get(message.chat.id, "Default Unit")
    lines = message.text.split("\n")
    count = 0
    
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            for line in lines:
                if "=" not in line:
                    continue
                parts = line.split("=", 1)
                eng = parts[0].strip().lower()
                uzb = parts[1].strip().lower()
                
                if eng and uzb:
                    cursor.execute(
                        "INSERT INTO words(user_id,unit,eng,uzb) VALUES(%s,%s,%s,%s)",
                        (message.chat.id, unit, eng, uzb)
                    )
                    count += 1
            conn.commit()
    except Exception as e:
        print(f"Error saving words: {e}")
        conn.rollback()
    finally:
        db_pool.putconn(conn)

    reset_user(message.chat.id)
    bot.send_message(
        message.chat.id,
        f"✅ {count} ta so‘z '{unit}' unitiga saqlandi.",
        reply_markup=main_menu()
    )

# ================= UNIT SELECT =================

def choose_unit(message, mode):
    units = execute_query("SELECT DISTINCT unit FROM words WHERE user_id=%s", (message.chat.id,), fetch="all")

    if not units:
        bot.send_message(message.chat.id, "❗ Avval so‘z qo‘shing.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for u in units:
        markup.add(u[0])

    markup.add("📚 All")
    markup.add("🔙 Orqaga")

    user_state[message.chat.id] = f"choose_{mode}"
    bot.send_message(
        message.chat.id,
        "📚 Qaysi unit bo‘yicha mashq qilmoqchisiz?",
        reply_markup=markup
    )

# ================= WRITING QUIZ =================

@bot.message_handler(func=lambda m: m.text == "✍️ Writing Quiz")
def start_write(message):
    choose_unit(message, "write")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "choose_write")
def process_choose_write(message):
    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Bosh sahifa", reply_markup=main_menu())
        return

    if message.text == "📚 All":
        rows = execute_query("SELECT eng, uzb FROM words WHERE user_id=%s", (message.chat.id,), fetch="all")
    else:
        rows = execute_query("SELECT eng, uzb FROM words WHERE user_id=%s AND unit=%s", (message.chat.id, message.text), fetch="all")

    if not rows:
        bot.send_message(message.chat.id, "❗ Bu unitda so‘z yo‘q.")
        return

    random.shuffle(rows)
    quiz_sessions[message.chat.id] = {
        "words": rows,
        "index": 0,
        "correct": 0,
        "wrong": 0,
        "mode": "write"
    }

    user_state.pop(message.chat.id, None)
    ask_question(message.chat.id)

# ================= TEST QUIZ =================

@bot.message_handler(func=lambda m: m.text == "📝 Test Quiz")
def start_test(message):
    choose_unit(message, "test")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "choose_test")
def process_choose_test(message):
    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Bosh sahifa", reply_markup=main_menu())
        return

    if message.text == "📚 All":
        rows = execute_query("SELECT eng, uzb FROM words WHERE user_id=%s", (message.chat.id,), fetch="all")
    else:
        rows = execute_query("SELECT eng, uzb FROM words WHERE user_id=%s AND unit=%s", (message.chat.id, message.text), fetch="all")

    if not rows:
        bot.send_message(message.chat.id, "❗ Bu unitda so‘z yo‘q.")
        return

    random.shuffle(rows)
    quiz_sessions[message.chat.id] = {
        "words": rows,
        "index": 0,
        "correct": 0,
        "wrong": 0,
        "mode": "test"
    }

    user_state.pop(message.chat.id, None)
    ask_question(message.chat.id)

# ================= ASK QUESTION =================

def ask_question(chat_id):
    session = quiz_sessions.get(chat_id)
    if not session:
        return

    if session["index"] >= len(session["words"]):
        total = len(session["words"])
        correct = session["correct"]
        wrong = session["wrong"]
        percent = int((correct / total) * 100) if total > 0 else 0

        bot.send_message(
            chat_id,
            f"📊 Natija\n\nJami: {total}\n✅ To‘g‘ri: {correct}\n❌ Xato: {wrong}\nFoiz: {percent}%",
            reply_markup=main_menu()
        )
        quiz_sessions.pop(chat_id, None)
        return

    eng, uzb = session["words"][session["index"]]
    session["answer"] = eng

    if session["mode"] == "write":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔙 Orqaga")
        bot.send_message(
            chat_id,
            f"🇺🇿 {uzb}\n\n✍️ Inglizchasini yozing:",
            reply_markup=markup
        )
    else:
        options = [eng]
        pool = [w[0] for w in session["words"] if w[0] != eng]
        options.extend(random.sample(pool, min(3, len(pool))))
        random.shuffle(options)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for o in options:
            markup.add(o)
        markup.add("🔙 Orqaga")

        bot.send_message(
            chat_id,
            f"🇺🇿 {uzb}\n\n🔍 To'g'ri variantni tanlang:",
            reply_markup=markup
        )

# ================= ANSWER =================

@bot.message_handler(func=lambda m: m.chat.id in quiz_sessions)
def check_answer(message):
    session = quiz_sessions.get(message.chat.id)

    if message.text == "🔙 Orqaga":
        quiz_sessions.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "Bosh sahifa", reply_markup=main_menu())
        return

    answer = session["answer"]

    execute_query("UPDATE stats SET tests = tests + 1 WHERE user_id=%s", (message.chat.id,), commit=True)
    
    if message.text.lower().strip() == answer:
        session["correct"] += 1
        execute_query("UPDATE stats SET correct = correct + 1 WHERE user_id=%s", (message.chat.id,), commit=True)
        bot.send_message(message.chat.id, "✅ To‘g‘ri")
    else:
        session["wrong"] += 1
        execute_query("UPDATE stats SET wrong = wrong + 1 WHERE user_id=%s", (message.chat.id,), commit=True)
        bot.send_message(message.chat.id, f"❌ Xato\nTo‘g‘ri javob: {answer}")

    session["index"] += 1
    ask_question(message.chat.id)

# ================= STAT =================

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stat(message):
    row = execute_query("SELECT tests, correct, wrong FROM stats WHERE user_id=%s", (message.chat.id,), fetch="one")

    if row is None:
        tests, correct, wrong = 0, 0, 0
    else:
        tests, correct, wrong = row

    bot.send_message(
        message.chat.id,
        f"📊 Sizning umumiy statistikangiz:\n\n📝 Jami ishlangan testlar: {tests}\n✅ To‘g‘ri javoblar: {correct}\n❌ Xato javoblar: {wrong}",
        reply_markup=main_menu()
    )

# ================= CLEAR =================

@bot.message_handler(func=lambda m: m.text == "❌ Clear All")
def clear_all(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Ha, o'chirish", "Yo'q, bekor qilish")
    
    user_state[message.chat.id] = "confirm_clear"
    
    bot.send_message(
        message.chat.id,
        "⚠️ Rostan ham barcha so'zlarni va statistikani o'chirib yubormoqchimisiz?",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "confirm_clear")
def confirm_clear(message):
    if message.text == "Ha, o'chirish":
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM words WHERE user_id=%s", (message.chat.id,))
                cursor.execute("UPDATE stats SET tests=0, correct=0, wrong=0 WHERE user_id=%s", (message.chat.id,))
                conn.commit()
        except Exception as e:
            print(f"Error clearing: {e}")
            conn.rollback()
        finally:
            db_pool.putconn(conn)

        quiz_sessions.pop(message.chat.id, None)
        reset_user(message.chat.id)
        
        bot.send_message(
            message.chat.id,
            "🗑 Barcha so‘zlar va statistika o‘chirildi.",
            reply_markup=main_menu()
        )
    else:
        reset_user(message.chat.id)
        bot.send_message(
            message.chat.id,
            "Bekor qilindi.",
            reply_markup=main_menu()
        )

# ================= FALLBACK =================

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(
        message.chat.id,
        "Noma'lum buyruq. Iltimos, menyudan foydalaning.",
        reply_markup=main_menu()
    )

# ================= RUN =================

if __name__ == "__main__":
    print("Bot ishga tushmoqda...")
    bot.infinity_polling(skip_pending=True)
