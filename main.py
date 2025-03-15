import os
import json
import logging
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()
TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# JSON fayldan lug‘atni yuklash
def load_dictionary():
    with open("dictionary.json", "r", encoding="utf-8") as file:
        return json.load(file)

dictionary = load_dictionary()

# Foydalanuvchi ID-larini saqlash uchun fayl
USER_IDS_FILE = "user_ids.json"

def load_user_ids():
    try:
        with open(USER_IDS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_user_id(user_id):
    user_ids = load_user_ids()
    if user_id not in user_ids:
        user_ids.append(user_id)
        with open(USER_IDS_FILE, "w", encoding="utf-8") as file:
            json.dump(user_ids, file)

# Klaviatura tugmalari
question_limit_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="5"), KeyboardButton(text="10"), KeyboardButton(text="15")],
        [KeyboardButton(text="✏ Raqam kiritish")]
    ],
    resize_keyboard=True
)

test_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏹ Tugatish")]
    ],
    resize_keyboard=True
)

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 Boshlash")]
    ],
    resize_keyboard=True
)

# Foydalanuvchi ma'lumotlari
user_data = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_data:
        await stop_quiz(message)  # Agar test davom etayotgan bo‘lsa, tugatish
    save_user_id(user_id)
    user_data[user_id] = {"total": 0, "attempts": 0, "question_limit": 0, "asked_words": set()}
    await message.answer(
        "👋 *Salom!* \n\n📖 Rus tilidagi so‘zlarni test qilish uchun *«🎯 Boshlash»* tugmasini bosing.",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "🎯 Boshlash")
async def ask_question_limit(message: types.Message):
    user_id = message.from_user.id
    await message.answer("📌 *Nechta savol ishlamoqchisiz? Tugmadan tanlang yoki ✏ Raqam kiritish tugmasini bosing.*", reply_markup=question_limit_keyboard)
    user_data[user_id] = {"total": 0, "attempts": 0, "question_limit": 0, "questions_asked": 0, "asked_words": set()}

@dp.message(lambda message: message.text in ["5", "10", "15"])
async def set_question_limit_predefined(message: types.Message):
    user_id = message.from_user.id
    question_limit = int(message.text)
    user_data[user_id]["question_limit"] = question_limit
    await message.answer("📌 *Test boshlandi!*", reply_markup=test_keyboard)
    await ask_question(message)

@dp.message(lambda message: message.text == "✏ Raqam kiritish")
async def ask_custom_question_limit(message: types.Message):
    await message.answer("📌 *Nechta savol ishlamoqchisiz? Raqam kiriting.*")

@dp.message(lambda message: message.text.isdigit())
async def set_question_limit_custom(message: types.Message):
    user_id = message.from_user.id
    question_limit = int(message.text)
    user_data[user_id]["question_limit"] = question_limit
    await message.answer("📌 *Test boshlandi!*", reply_markup=test_keyboard)
    await ask_question(message)

async def ask_question(message: types.Message):
    user_id = message.from_user.id
    if user_data[user_id]["questions_asked"] >= user_data[user_id]["question_limit"]:
        await stop_quiz(message)
        return
    
    available_words = list(set(dictionary.keys()) - user_data[user_id]["asked_words"])
    if not available_words:
        await stop_quiz(message)
        return
    
    word = random.choice(available_words)
    translation = dictionary[word]
    user_data[user_id]["current_word"] = word
    user_data[user_id]["correct_answer"] = translation
    user_data[user_id]["total"] += 1
    user_data[user_id]["questions_asked"] += 1
    user_data[user_id]["asked_words"].add(word)
    await message.answer(f"📌 *{word}* so‘zining ruscha tarjimasini yozing.")

@dp.message(lambda message: message.text == "⏹ Tugatish")
async def stop_quiz(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_data:
        stats = user_data[user_id]
        await message.answer(
            f"🛑 *Test tugatildi!*\n"
            f"📊 *Savollar soni:* {stats['total']}\n"
            f"📌 *Urinishlar soni:* {stats['attempts']}",
            reply_markup=main_keyboard
        )
        user_data.pop(user_id, None)

@dp.message()
async def check_answer(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data or "current_word" not in user_data[user_id]:
        await message.answer("⚠️ *Iltimos, avval testni boshlang!* «🎯 Boshlash» tugmasini bosing.")
        return
    
    correct_answer = user_data[user_id]["correct_answer"]
    user_data[user_id]["attempts"] += 1
    
    if message.text.lower().strip() == correct_answer.lower():
        await message.answer("🎉 *To‘g‘ri! Ajoyib!* ✅")
        await ask_question(message)
    else:
        await message.answer("❌ *Noto‘g‘ri! Yana urinib ko‘ring.*")

async def main():
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logging.info("Bot to‘xtatildi.")

if __name__ == "__main__":
    asyncio.run(main())
