import telebot
import random
import json
import os

# ⚠️ TOKENNI O'ZGARTIR
TOKEN = "8571176898:AAEnH6ohjXaAXsSqIsAi8dnNaRDbWNb_QFk"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"


# ============ USER RESET ============

def reset_user(chat_id):
    user_state.pop(chat_id, None)
    current_unit.pop(chat_id, None)
    current_quiz.pop(chat_id, None)
    writing_quiz.pop(chat_id, None)


# ============ LOAD / SAVE ============

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "units": {},
            "stats": {
                "tests": 0,
                "correct": 0,
                "wrong": 0
            }
        }

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


data = load_data()


# ============ MENU ============

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


# ============ START ============

@bot.message_handler(commands=["start"])
def start(message):

    reset_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "Salom! 📚 English Word Botga xush kelibsan!",
        reply_markup=main_menu()
    )


# ============ VARIABLES ============

user_state = {}
current_unit = {}
current_quiz = {}
writing_quiz = {}


# ============ ADD WORDS ============

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

    unit = message.text.strip()

    if unit not in data["units"]:
        data["units"][unit] = {}

    current_unit[message.chat.id] = unit
    user_state[message.chat.id] = "wait_words"

    save_data(data)

    bot.send_message(
        message.chat.id,
        f"✅ {unit} tanlandi.\nSo‘zlarni yubor:\nenglish=uzbek",
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

        if eng and uzb:
            data["units"][unit][eng] = uzb
            count += 1

    save_data(data)

    reset_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        f"✅ {count} ta so‘z saqlandi!",
        reply_markup=main_menu()
    )


# ============ TEST QUIZ ============

@bot.message_handler(func=lambda m: m.text == "📝 Test Quiz")
def start_test_quiz(message):

    if not data["units"]:
        bot.send_message(message.chat.id, "❗ Unit yo‘q.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    for unit in data["units"]:
        markup.add(unit)

    markup.add("📚 All", "🔙 Orqaga")

    bot.send_message(
        message.chat.id,
        "Unit tanla:",
        reply_markup=markup
    )

    user_state[message.chat.id] = "choose_test_unit"


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "choose_test_unit")
def choose_test_unit(message):

    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    text = message.text
    words = {}

    if text == "📚 All":
        for u in data["units"].values():
            words.update(u)

    elif text in data["units"]:
        words = data["units"][text]

    else:
        bot.send_message(message.chat.id, "❗ Xato tanlov")
        return

    if not words:
        bot.send_message(message.chat.id, "❗ Bu unitda so‘z yo‘q.")
        return

    user_state.pop(message.chat.id)

    start_test_real(message, words)


def start_test_real(message, words):

    if not words:
        return

    eng, uzb = random.choice(list(words.items()))

    direction = random.choice([0, 1])

    if direction == 0:
        question = f"🇬🇧 {eng} → ?"
        answer = uzb
        pool = list(words.values())
    else:
        question = f"🇺🇿 {uzb} → ?"
        answer = eng
        pool = list(words.keys())

    variants = [answer]

    while len(variants) < 4:
        v = random.choice(pool)
        if v not in variants:
            variants.append(v)

    random.shuffle(variants)

    current_quiz[message.chat.id] = {
        "answer": answer,
        "words": words
    }

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    for v in variants:
        markup.add(v)

    markup.add("🔙 Orqaga")

    bot.send_message(message.chat.id, question, reply_markup=markup)


@bot.message_handler(func=lambda m: m.chat.id in current_quiz)
def check_test_answer(message):

    if message.text == "🔙 Orqaga":
        current_quiz.pop(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    quiz = current_quiz[message.chat.id]

    answer = quiz["answer"]
    words = quiz["words"]

    data["stats"]["tests"] += 1

    if message.text == answer:
        data["stats"]["correct"] += 1
        bot.send_message(message.chat.id, "✅ To‘g‘ri!")
    else:
        data["stats"]["wrong"] += 1
        bot.send_message(message.chat.id, f"❌ Xato! {answer}")

    save_data(data)

    start_test_real(message, words)


# ============ WRITING QUIZ ============

@bot.message_handler(func=lambda m: m.text == "✍️ Writing Quiz")
def start_writing_quiz(message):

    if not data["units"]:
        bot.send_message(message.chat.id, "❗ Unit yo‘q.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    for unit in data["units"]:
        markup.add(unit)

    markup.add("📚 All", "🔙 Orqaga")

    bot.send_message(
        message.chat.id,
        "Unit tanla:",
        reply_markup=markup
    )

    user_state[message.chat.id] = "choose_write_unit"


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "choose_write_unit")
def choose_write_unit(message):

    if message.text == "🔙 Orqaga":
        reset_user(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    text = message.text
    words = {}

    if text == "📚 All":
        for u in data["units"].values():
            words.update(u)

    elif text in data["units"]:
        words = data["units"][text]

    else:
        bot.send_message(message.chat.id, "❗ Xato tanlov")
        return

    if not words:
        bot.send_message(message.chat.id, "❗ Bu unitda so‘z yo‘q.")
        return

    user_state.pop(message.chat.id)

    start_write_real(message, words)


def start_write_real(message, words):

    if not words:
        return

    eng, uzb = random.choice(list(words.items()))

    writing_quiz[message.chat.id] = {
        "answer": eng.lower(),
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
def check_write_answer(message):

    if message.text == "🔙 Orqaga":
        writing_quiz.pop(message.chat.id)
        bot.send_message(message.chat.id, "Menu", reply_markup=main_menu())
        return

    quiz = writing_quiz[message.chat.id]

    answer = quiz["answer"]
    words = quiz["words"]

    user_answer = message.text.lower().strip()

    data["stats"]["tests"] += 1

    if user_answer == answer:
        data["stats"]["correct"] += 1
        bot.send_message(message.chat.id, "✅ To‘g‘ri!")
    else:
        data["stats"]["wrong"] += 1
        bot.send_message(message.chat.id, f"❌ Xato! {answer}")

    save_data(data)

    start_write_real(message, words)


# ============ STAT ============

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stat(message):

    s = data["stats"]

    text = f"""
📊 Statistika:

📝 Testlar: {s['tests']}
✅ To‘g‘ri: {s['correct']}
❌ Xato: {s['wrong']}
"""

    bot.send_message(message.chat.id, text, reply_markup=main_menu())


# ============ CLEAR ============

@bot.message_handler(func=lambda m: m.text == "❌ Clear All")
def clear_all(message):

    global data

    data = {
        "units": {},
        "stats": {
            "tests": 0,
            "correct": 0,
            "wrong": 0
        }
    }

    save_data(data)

    bot.send_message(
        message.chat.id,
        "🗑 Tozalandi!",
        reply_markup=main_menu()
    )


# ============ RUN ============

bot.infinity_polling()
