import sqlite3
import asyncio
import os
import requests
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
THE_CAT_API_KEY = os.getenv('THE_CAT_API_KEY')
NASA_API_KEY = os.getenv('NASA_API_KEY')

bot = Bot(token=TOKEN)
dp = Dispatcher()

def init_db():
    # Используем менеджер контекста для работы с базой данных
    with sqlite3.connect('school_data.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                age INTEGER,
                grade TEXT
            )
        ''')

# FSM для добавления ученика
class StudentForm(StatesGroup):
    name = State()
    age = State()
    grade = State()

# FSM для запроса информации о породе кошки
class CatForm(StatesGroup):
    breed = State()

# --- Существующий функционал ---

# Задание 1: Простое меню с кнопками /start
@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Привет"), KeyboardButton(text="Пока")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите действие:", reply_markup=keyboard)

@dp.message(lambda message: message.text in ["Привет", "Пока"])
async def handle_buttons(message: Message):
    if message.text == "Привет":
        await message.answer(f"Привет, {message.from_user.first_name}!")
    elif message.text == "Пока":
        await message.answer(f"До свидания, {message.from_user.first_name}!")

# Задание 2: Кнопки с URL-ссылками /links
@dp.message(Command("links"))
async def send_links(message: Message):
    links = {
        "Новости": "https://news.ycombinator.com/",
        "Музыка": "https://spotify.com",
        "Видео": "https://youtube.com"
    }
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, url=url)] for name, url in links.items()
    ])
    await message.answer("Выберите ссылку:", reply_markup=keyboard)

# Задание 3: Динамическое изменение клавиатуры /dynamic
@dp.message(Command("dynamic"))
async def dynamic_keyboard(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать больше", callback_data="show_more")]
    ])
    await message.answer("Нажмите кнопку ниже:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "show_more")
async def show_more_buttons(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Опция 1", callback_data="option_1")],
        [InlineKeyboardButton(text="Опция 2", callback_data="option_2")]
    ])
    await callback.message.edit_text("Выберите опцию:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data in ["option_1", "option_2"])
async def handle_option(callback: types.CallbackQuery):
    text = "Вы выбрали: Опция 1" if callback.data == "option_1" else "Вы выбрали: Опция 2"
    await callback.answer(text)
    await callback.message.edit_text(text)

# Добавление ученика через команду /add
@dp.message(Command("add"))
async def add_student_start(message: Message, state: FSMContext):
    await message.answer("Введите имя ученика:")
    await state.set_state(StudentForm.name)

@dp.message(StudentForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите возраст ученика (числом):")
    await state.set_state(StudentForm.age)

@dp.message(StudentForm.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Возраст должен быть числом. Попробуйте снова.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Введите класс ученика:")
    await state.set_state(StudentForm.grade)

@dp.message(StudentForm.grade)
async def process_grade(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_data['grade'] = message.text

    with sqlite3.connect('school_data.db') as conn:
        conn.execute('''
            INSERT INTO students (name, age, grade)
            VALUES (?, ?, ?)
        ''', (user_data['name'], user_data['age'], user_data['grade']))

    await message.answer(f"✅ Ученик добавлен:\nИмя: {user_data['name']}\nВозраст: {user_data['age']}\nКласс: {user_data['grade']}")
    await state.clear()

# Просмотр всех учеников /students
@dp.message(Command("students"))
async def list_students(message: Message):
    with sqlite3.connect('school_data.db') as conn:
        cursor = conn.execute("SELECT * FROM students")
        students = cursor.fetchall()

    if not students:
        await message.answer("📭 Список учеников пуст.")
        return

    response = "📋 Список учеников:\n"
    for student in students:
        response += f"{student[0]}. {student[1]}, возраст: {student[2]}, класс: {student[3]}\n"

    await message.answer(response)

# --- Новый функционал с использованием сторонних API ---

# Функции для работы с TheCatAPI
def get_cat_breeds():
    url = "https://api.thecatapi.com/v1/breeds"
    headers = {"x-api-key": THE_CAT_API_KEY}
    response = requests.get(url, headers=headers)
    return response.json()

def get_cat_image_by_breed(breed_id):
    url = f"https://api.thecatapi.com/v1/images/search?breed_ids={breed_id}"
    headers = {"x-api-key": THE_CAT_API_KEY}
    response = requests.get(url, headers=headers)
    data = response.json()
    if data:
        return data[0]['url']
    return None

def get_breed_info(breed_name):
    breeds = get_cat_breeds()
    for breed in breeds:
        if breed['name'].lower() == breed_name.lower():
            return breed
    return None

# Обработчик команды /cat для получения информации о породе кошки
@dp.message(Command("cat"))
async def cat_command(message: Message, state: FSMContext):
    await message.answer("Введите название породы кошки:")
    await state.set_state(CatForm.breed)

@dp.message(CatForm.breed)
async def process_cat_breed(message: Message, state: FSMContext):
    breed_name = message.text
    breed_info = get_breed_info(breed_name)
    if breed_info:
        cat_image_url = get_cat_image_by_breed(breed_info['id'])
        info = (
            f"Breed: {breed_info['name']}\n"
            f"Origin: {breed_info['origin']}\n"
            f"Description: {breed_info['description']}\n"
            f"Temperament: {breed_info['temperament']}\n"
            f"Life Span: {breed_info['life_span']} years"
        )
        if cat_image_url:
            await message.answer_photo(photo=cat_image_url, caption=info)
        else:
            await message.answer(info)
    else:
        await message.answer("Порода не найдена. Попробуйте еще раз.")
    await state.clear()

# Функция для получения случайного изображения от NASA (APOD)
def get_random_apod():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    random_date = start_date + (end_date - start_date) * random.random()
    date_str = random_date.strftime("%Y-%m-%d")
    url = f'https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&date={date_str}'
    response = requests.get(url)
    return response.json()

# Обработчик команды /random_apod для получения случайного фото от NASA
@dp.message(Command("random_apod"))
async def random_apod_handler(message: Message):
    apod = get_random_apod()
    if 'url' in apod and 'title' in apod:
        photo_url = apod['url']
        title = apod['title']
        await message.answer_photo(photo=photo_url, caption=f"{title}")
    else:
        await message.answer("Не удалось получить данные от NASA.")

# --- Установка команд для бота ---
async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Простое меню с кнопками"),
        types.BotCommand(command="/links", description="Кнопки с URL-ссылками"),
        types.BotCommand(command="/dynamic", description="Динамическое меню"),
        types.BotCommand(command="/add", description="Добавить ученика"),
        types.BotCommand(command="/students", description="Список учеников"),
        types.BotCommand(command="/cat", description="Информация о породе кошки"),
        types.BotCommand(command="/random_apod", description="Случайное фото от NASA")
    ]
    await bot.set_my_commands(commands)

# --- Запуск бота ---
async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())