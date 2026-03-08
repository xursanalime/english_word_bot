import telebot
import sqlite3
import random
from telebot import types

TOKEN = "8571176898:AAFivZY2rz2g50rEa6RSwwbchUfc6NvZCOA"

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================

conn = sqlite3.connect("words.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS words(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
unit TEXT,
eng TEXT,
uzb TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats(
user_id INTEGER PRIMARY KEY,
tests INTEGER,
correct INTEGER,
wrong INTEGER
)
""")

conn.commit()

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

    cursor.execute(
        "INSERT OR IGNORE INTO stats(user_id,tests,correct,wrong) VALUES(?,?,?,?)",
        (message.chat.id, 0, 0, 0)
    )
    conn.commit()

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
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    current_unit[message.chat.id] = message.text.strip()

    user_state[message.chat.id] = "wait_words"

    bot.send_message(
        message.chat.id,
        "So‘zlarni quyidagi formatda yuboring:\n\nenglish = uzbek",
        reply_markup=back_menu()
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "wait_words")
def save_words(message):

    unit = current_unit.get(message.chat.id)

    lines = message.text.split("\n")

    count = 0

    for line in lines:

        if "=" not in line:
            continue

        eng, uzb = line.split("=", 1)

        cursor.execute(
            "INSERT INTO words(user_id,unit,eng,uzb) VALUES(?,?,?,?)",
            (
                message.chat.id,
                unit,
                eng.strip().lower(),
                uzb.strip().lower()
            )
        )

        count += 1

    conn.commit()

    reset_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        f"✅ {count} ta so‘z saqlandi.",
        reply_markup=main_menu()
    )


# ================= UNIT SELECT =================

def choose_unit(message, mode):

    cursor.execute(
        "SELECT DISTINCT unit FROM words WHERE user_id=?",
        (message.chat.id,)
    )

    units = cursor.fetchall()

    if not units:
        bot.send_message(
            message.chat.id,
            "❗ Avval so‘z qo‘shing."
        )
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
def choose_write(message):

    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    if message.text == "📚 All":

        cursor.execute(
            "SELECT eng,uzb FROM words WHERE user_id=?",
            (message.chat.id,)
        )

    else:

        cursor.execute(
            "SELECT eng,uzb FROM words WHERE user_id=? AND unit=?",
            (message.chat.id, message.text)
        )

    rows = cursor.fetchall()

    if not rows:

        bot.send_message(
            message.chat.id,
            "❗ Bu unitda so‘z yo‘q."
        )
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
def choose_test(message):

    if message.text == "📚 All":

        cursor.execute(
            "SELECT eng,uzb FROM words WHERE user_id=?",
            (message.chat.id,)
        )

    else:

        cursor.execute(
            "SELECT eng,uzb FROM words WHERE user_id=? AND unit=?",
            (message.chat.id, message.text)
        )

    rows = cursor.fetchall()

    if not rows:

        bot.send_message(
            message.chat.id,
            "❗ Bu unitda so‘z yo‘q."
        )
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

        percent = int((correct / total) * 100)

        bot.send_message(
            chat_id,
            f"📊 Natija\n\nJami: {total}\n✅ To‘g‘ri: {correct}\n❌ Xato: {wrong}\nNatija: {percent}%",
            reply_markup=main_menu()
        )

        quiz_sessions.pop(chat_id)

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

        pool = [w[0] for w in session["words"]]

        while len(options) < 4 and len(pool) > 3:
            r = random.choice(pool)
            if r not in options:
                options.append(r)

        random.shuffle(options)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        for o in options:
            markup.add(o)

        markup.add("🔙 Orqaga")

        bot.send_message(
            chat_id,
            f"🇺🇿 {uzb}",
            reply_markup=markup
        )


# ================= ANSWER =================

@bot.message_handler(func=lambda m: m.chat.id in quiz_sessions)
def check_answer(message):

    session = quiz_sessions.get(message.chat.id)

    if message.text == "🔙 Orqaga":

        quiz_sessions.pop(message.chat.id, None)

        bot.send_message(
            message.chat.id,
            "Menu",
            reply_markup=main_menu()
        )
        return

    answer = session["answer"]

    cursor.execute(
        "UPDATE stats SET tests = tests + 1 WHERE user_id=?",
        (message.chat.id,)
    )

    if message.text.lower().strip() == answer:

        session["correct"] += 1

        cursor.execute(
            "UPDATE stats SET correct = correct + 1 WHERE user_id=?",
            (message.chat.id,)
        )

        bot.send_message(message.chat.id, "✅ To‘g‘ri")

    else:

        session["wrong"] += 1

        cursor.execute(
            "UPDATE stats SET wrong = wrong + 1 WHERE user_id=?",
            (message.chat.id,)
        )

        bot.send_message(
            message.chat.id,
            f"❌ Xato\nTo‘g‘ri javob: {answer}"
        )

    conn.commit()

    session["index"] += 1

    ask_question(message.chat.id)


# ================= STAT =================

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stat(message):

    cursor.execute(
        "SELECT tests,correct,wrong FROM stats WHERE user_id=?",
        (message.chat.id,)
    )

    tests, correct, wrong = cursor.fetchone()

    bot.send_message(
        message.chat.id,
        f"📊 Statistika\n\nTestlar: {tests}\nTo‘g‘ri: {correct}\nXato: {wrong}",
        reply_markup=main_menu()
    )


# ================= CLEAR =================

@bot.message_handler(func=lambda m: m.text == "❌ Clear All")
def clear_all(message):

    cursor.execute(
        "DELETE FROM words WHERE user_id=?",
        (message.chat.id,)
    )

    cursor.execute(
        "UPDATE stats SET tests=0,correct=0,wrong=0 WHERE user_id=?",
        (message.chat.id,)
    )

    conn.commit()

    quiz_sessions.pop(message.chat.id, None)

    bot.send_message(
        message.chat.id,
        "🗑 Barcha so‘zlar o‘chirildi.",
        reply_markup=main_menu()
    )


# ================= RUN =================

bot.infinity_polling(skip_pending=True)
