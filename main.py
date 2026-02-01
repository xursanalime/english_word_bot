
import telebot
import random
import json
import os

# ⚠️ YANGI TOKENNI BU YERGA QO'Y
TOKEN = "8571176898:AAEnH6ohjXaAXsSqIsAi8dnNaRDbWNb_QFk"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"

def reset_user(chat_id):

    user_state.pop(chat_id, None)
    current_unit.pop(chat_id, None)
    current_quiz.pop(chat_id, None)

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

    markup.add("➕ So'z qo‘shish")
    markup.add("📝 Quiz", "📊 Statistika")
    markup.add("❌ Clear All")

    return markup


# ============ START ============

@bot.message_handler(commands=["start"])
def start(message):

    reset_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "Salom! 📚 So‘z yodlash botiga xush kelibsan!\nHammasi yangidan boshlandi ✅",
        reply_markup=main_menu()
    )


# ============ ADD WORDS WITH UNIT ============

user_state = {}
current_unit = {}
quiz_unit = {}



@bot.message_handler(func=lambda m: m.text == "➕ So'z qo‘shish")
def add_words(message):

    user_state[message.chat.id] = "wait_unit"

    bot.send_message(
        message.chat.id,
        "Unit nomini yoz:\nMasalan: Unit1"
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "wait_unit")
def get_unit(message):

    unit = message.text.strip()

    if unit not in data["units"]:
        data["units"][unit] = {}

    current_unit[message.chat.id] = unit
    user_state[message.chat.id] = "wait_words"

    save_data(data)

    bot.send_message(
        message.chat.id,
        f"✅ {unit} tanlandi. Endi so‘zlarni yubor."
    )


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "wait_words")
def save_words(message):

    unit = current_unit.get(message.chat.id)

    if not unit:
        bot.send_message(message.chat.id, "❗ Avval unit tanla.")
        return

    lines = message.text.split("\n")
    count = 0

    for line in lines:
        if "=" in line:
            eng, uzb = line.split("=", 1)

            eng = eng.strip().lower()
            uzb = uzb.strip().lower()

            if eng and uzb:
                data["units"][unit][eng] = uzb
                count += 1

    save_data(data)

    user_state.pop(message.chat.id, None)
    current_unit.pop(message.chat.id, None)

    bot.send_message(
        message.chat.id,
        f"✅ {unit} ga {count} ta so‘z saqlandi!",
        reply_markup=main_menu()
    )


# ============ QUIZ ============

# ============ QUIZ ============

current_quiz = {}


@bot.message_handler(func=lambda m: m.text == "📝 Quiz")
def start_quiz(message):

    if not data["units"]:
        bot.send_message(message.chat.id, "❗ Hali unit yo‘q.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    for unit in data["units"].keys():
        markup.add(unit)

    markup.add("📚 All", "🔙 Orqaga")

    bot.send_message(
        message.chat.id,
        "Qaysi unitdan test qilamiz?",
        reply_markup=markup
    )

    user_state[message.chat.id] = "choose_quiz_unit"


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "choose_quiz_unit")
def choose_quiz_unit(message):

    text = message.text
    all_words = {}

    if text == "📚 All":
        for u in data["units"].values():
            all_words.update(u)

    elif text in data["units"]:
        all_words = data["units"][text]

    else:
        bot.send_message(message.chat.id, "❗ Noto‘g‘ri tanlov.")
        return

    if not all_words:
        bot.send_message(message.chat.id, "❗ Bu unitda so‘z yo‘q.")
        return

    user_state.pop(message.chat.id, None)

    start_real_quiz(message, all_words)


def start_real_quiz(message, words):

    eng, uzb = random.choice(list(words.items()))

    # 0 yoki 1 random tanlaymiz
    direction = random.choice([0, 1])

    # 0 = ENG -> UZB
    # 1 = UZB -> ENG

    if direction == 0:
        question = f"🇬🇧 {eng} → ?"
        correct = uzb
        options_pool = list(words.values())

    else:
        question = f"🇺🇿 {uzb} → ?"
        correct = eng
        options_pool = list(words.keys())

    variants = [correct]

    while len(variants) < 4:
        v = random.choice(options_pool)
        if v not in variants:
            variants.append(v)

    random.shuffle(variants)

    current_quiz[message.chat.id] = {
        "answer": correct,
        "words": words
    }

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    for v in variants:
        markup.add(v)

    bot.send_message(
        message.chat.id,
        question,
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.chat.id in current_quiz)
def check_answer(message):

    quiz_data = current_quiz[message.chat.id]
    answer = quiz_data["answer"]
    words = quiz_data["words"]

    data["stats"]["tests"] += 1

    if message.text == answer:
        data["stats"]["correct"] += 1
        bot.send_message(message.chat.id, "✅ To‘g‘ri!")
    else:
        data["stats"]["wrong"] += 1
        bot.send_message(message.chat.id, f"❌ Xato! Javob: {answer}")

    save_data(data)

    current_quiz.pop(message.chat.id)

    # Yana shu unitdan davom etadi
    start_real_quiz(message, words)

# ============ STAT ============

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stat(message):
    reset_user(message.chat.id)

    s = data["stats"]

    text = f"""
📊 Statistika:

Testlar: {s['tests']}
To‘g‘ri: {s['correct']}
Xato: {s['wrong']}
"""

    bot.send_message(message.chat.id, text)


# ============ CLEAR ALL ============

@bot.message_handler(commands=["clearall"])
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
        "🗑 Hammasi tozalandi!",
        reply_markup=main_menu()
    )


# ============ RUN ============

bot.infinity_polling()
