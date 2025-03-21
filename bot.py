import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

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

# --- Задание 1: Простое меню с кнопками /start ---
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

# --- Задание 2: Кнопки с URL-ссылками /links ---
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

# --- Задание 3: Динамическое изменение клавиатуры /dynamic ---
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

# --- Добавление ученика через команду /add ---
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

# --- Просмотр всех учеников /students ---
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

# --- Установка команд для бота ---
async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Простое меню с кнопками"),
        types.BotCommand(command="/links", description="Кнопки с URL-ссылками"),
        types.BotCommand(command="/dynamic", description="Динамическое меню"),
        types.BotCommand(command="/add", description="Добавить ученика"),
        types.BotCommand(command="/students", description="Список учеников")
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