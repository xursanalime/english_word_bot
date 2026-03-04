import telebot
import random
import sqlite3

TOKEN = "8571176898:AAECTz6AQpIDW4b5JDJwm_RnTEHzsRHz0_Y"

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================

conn = sqlite3.connect("words.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS words(
id INTEGER PRIMARY KEY AUTOINCREMENT,
unit TEXT,
eng TEXT,
uzb TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats(
id INTEGER PRIMARY KEY,
tests INTEGER,
correct INTEGER,
wrong INTEGER
)
""")

cursor.execute("INSERT OR IGNORE INTO stats VALUES(1,0,0,0)")
conn.commit()

# ================= VARIABLES =================

user_state = {}
current_unit = {}
current_quiz = {}
writing_quiz = {}

# ================= MENU =================

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ So'z qo‘shish", "📝 Test Quiz")
    markup.row("✍️ Writing Quiz", "📊 Statistika")
    markup.row("❌ Clear All")
    return markup


def back_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Orqaga")
    return markup


def reset_user(chat_id):
    user_state.pop(chat_id, None)
    current_unit.pop(chat_id, None)
    current_quiz.pop(chat_id, None)
    writing_quiz.pop(chat_id, None)

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    reset_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "Salom! 📚 English Word Botga xush kelibsan!",
        reply_markup=main_menu()
    )

# ================= ADD WORDS =================

@bot.message_handler(func=lambda m: m.text == "➕ So'z qo‘shish")
def add_words(message):

    user_state[message.chat.id] = "wait_unit"

    bot.send_message(
        message.chat.id,
        "Unit nomini yoz:\nMasalan: Unit1",
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
        "So‘zlarni yubor:\nenglish=uzbek",
        reply_markup=back_menu()
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "wait_words")
def save_words(message):

    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    unit = current_unit.get(message.chat.id)

    lines = message.text.split("\n")
    count = 0

    for line in lines:

        line = line.strip()

        if "=" in line:
            eng, uzb = line.split("=", 1)

        elif "-" in line:
            eng, uzb = line.split("-", 1)

        else:
            continue

        eng = eng.strip().lower()
        uzb = uzb.strip().lower()

        cursor.execute(
            "INSERT INTO words(unit,eng,uzb) VALUES(?,?,?)",
            (unit, eng, uzb)
        )

        count += 1

    conn.commit()

    reset_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        f"✅ {count} ta so‘z saqlandi!",
        reply_markup=main_menu()
    )

# ================= TEST QUIZ =================

@bot.message_handler(func=lambda m: m.text == "📝 Test Quiz")
def start_test(message):

    cursor.execute("SELECT DISTINCT unit FROM words")
    units = cursor.fetchall()

    if not units:
        bot.send_message(message.chat.id, "❗ Unit yo‘q.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    for u in units:
        markup.add(u[0])

    markup.add("📚 All", "🔙 Orqaga")

    bot.send_message(message.chat.id, "Unit tanla:", reply_markup=markup)

    user_state[message.chat.id] = "choose_test_unit"


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "choose_test_unit")
def choose_test_unit(message):

    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    if message.text == "📚 All":
        cursor.execute("SELECT eng,uzb FROM words")
    else:
        cursor.execute("SELECT eng,uzb FROM words WHERE unit=?", (message.text,))

    rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "❗ Bu unitda so‘z yo‘q.")
        return

    words = {eng: uzb for eng, uzb in rows}

    user_state.pop(message.chat.id)

    start_test_real(message, words)


def start_test_real(message, words):

    eng, uzb = random.choice(list(words.items()))

    answer = eng

    pool = list(words.keys())
    variants = [answer]

    while len(variants) < 4 and len(pool) >= 4:
        v = random.choice(pool)
        if v not in variants:
            variants.append(v)

    random.shuffle(variants)

    current_quiz[message.chat.id] = {
        "answer": answer,
        "words": words
    }

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    for v in variants:
        markup.add(v)

    markup.add("🔙 Orqaga")

    bot.send_message(message.chat.id, f"🇺🇿 {uzb} → ?", reply_markup=markup)


@bot.message_handler(func=lambda m: m.chat.id in current_quiz)
def check_test(message):

    if message.text == "🔙 Orqaga":
        current_quiz.pop(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    quiz = current_quiz[message.chat.id]

    answer = quiz["answer"]
    words = quiz["words"]

    cursor.execute("UPDATE stats SET tests = tests + 1 WHERE id=1")

    if message.text == answer:

        cursor.execute("UPDATE stats SET correct = correct + 1 WHERE id=1")

        bot.send_message(message.chat.id, "✅ To‘g‘ri!")

    else:

        cursor.execute("UPDATE stats SET wrong = wrong + 1 WHERE id=1")

        bot.send_message(message.chat.id, f"❌ Xato! {answer}")

    conn.commit()

    start_test_real(message, words)

# ================= WRITING QUIZ =================

@bot.message_handler(func=lambda m: m.text == "✍️ Writing Quiz")
def start_writing(message):

    cursor.execute("SELECT DISTINCT unit FROM words")
    units = cursor.fetchall()

    if not units:
        bot.send_message(message.chat.id, "❗ Unit yo‘q.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    for u in units:
        markup.add(u[0])

    markup.add("📚 All", "🔙 Orqaga")

    bot.send_message(message.chat.id, "Unit tanla:", reply_markup=markup)

    user_state[message.chat.id] = "choose_write_unit"


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "choose_write_unit")
def choose_write_unit(message):

    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    if message.text == "📚 All":
        cursor.execute("SELECT eng,uzb FROM words")
    else:
        cursor.execute("SELECT eng,uzb FROM words WHERE unit=?", (message.text,))

    rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "❗ Bu unitda so‘z yo‘q.")
        return

    words = {eng: uzb for eng, uzb in rows}

    user_state.pop(message.chat.id)

    start_write_real(message, words)


def start_write_real(message, words):

    eng, uzb = random.choice(list(words.items()))

    writing_quiz[message.chat.id] = {
        "answer": eng,
        "words": words
    }

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Orqaga")

    bot.send_message(
        message.chat.id,
        f"🇺🇿 {uzb}\n\n✍️ Inglizchasini yoz:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.chat.id in writing_quiz)
def check_write(message):

    if message.text == "🔙 Orqaga":
        writing_quiz.pop(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    quiz = writing_quiz[message.chat.id]

    answer = quiz["answer"]
    words = quiz["words"]

    cursor.execute("UPDATE stats SET tests = tests + 1 WHERE id=1")

    if message.text.lower().strip() == answer:

        cursor.execute("UPDATE stats SET correct = correct + 1 WHERE id=1")

        bot.send_message(message.chat.id, "✅ To‘g‘ri!")

    else:

        cursor.execute("UPDATE stats SET wrong = wrong + 1 WHERE id=1")

        bot.send_message(message.chat.id, f"❌ Xato! {answer}")

    conn.commit()

    start_write_real(message, words)

# ================= STAT =================

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stat(message):

    cursor.execute("SELECT tests,correct,wrong FROM stats WHERE id=1")

    tests, correct, wrong = cursor.fetchone()

    text = f"""
📊 Statistika

📝 Testlar: {tests}
✅ To‘g‘ri: {correct}
❌ Xato: {wrong}
"""

    bot.send_message(message.chat.id, text, reply_markup=main_menu())

# ================= CLEAR =================

@bot.message_handler(func=lambda m: m.text == "❌ Clear All")
def clear_all(message):

    cursor.execute("DELETE FROM words")
    cursor.execute("UPDATE stats SET tests=0,correct=0,wrong=0 WHERE id=1")
    conn.commit()

    bot.send_message(message.chat.id, "🗑 Tozalandi!", reply_markup=main_menu())

# ================= RUN =================

bot.infinity_polling(skip_pending=True)