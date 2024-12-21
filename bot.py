import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

# Токен из .env
TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Создание базы данных и таблицы
def init_db():
    conn = sqlite3.connect('school_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        grade TEXT
    )
    ''')
    conn.commit()
    conn.close()

# FSM для управления вводом пользователя
class StudentForm(StatesGroup):
    name = State()
    age = State()
    grade = State()

# Обработчик команды /start
@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await message.answer("Привет! Введите ваше имя:")
    await state.set_state(StudentForm.name)

# Получение имени
@dp.message(StudentForm.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите ваш возраст:")
    await state.set_state(StudentForm.age)

# Получение возраста
@dp.message(StudentForm.age)
async def get_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите возраст числом.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Введите ваш класс:")
    await state.set_state(StudentForm.grade)

# Получение класса и сохранение в базу данных
@dp.message(StudentForm.grade)
async def get_grade(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_data['grade'] = message.text

    # Сохранение в базу данных
    conn = sqlite3.connect('school_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO students (name, age, grade)
    VALUES (?, ?, ?)
    ''', (user_data['name'], user_data['age'], user_data['grade']))
    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Данные сохранены:\nИмя: {user_data['name']}\nВозраст: {user_data['age']}\nКласс: {user_data['grade']}")
    await state.clear()

# Команда /students - список учеников
@dp.message(Command("students"))
async def list_students(message: Message):
    conn = sqlite3.connect('school_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    conn.close()

    if not students:
        await message.answer("📭 Список учеников пуст.")
        return

    response = "📋 Список учеников:\n"
    for student in students:
        response += f"{student[0]}. {student[1]}, возраст: {student[2]}, класс: {student[3]}\n"

    await message.answer(response)

# Удаление ученика по ID
@dp.message(Command("delete"))
async def delete_student(message: Message):
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("⚠️ Использование: /delete [ID]")
        return

    student_id = int(args[1])

    conn = sqlite3.connect('school_data.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted:
        await message.answer(f"✅ Ученик с ID {student_id} удалён.")
    else:
        await message.answer(f"❌ Ученик с ID {student_id} не найден.")

# Установка команд для бота
async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Начать работу с ботом"),
        types.BotCommand(command="/students", description="Посмотреть список учеников"),
        types.BotCommand(command="/delete", description="Удалить ученика по ID")
    ]
    await bot.set_my_commands(commands)

# Запуск бота
async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

    import pandas as pd


    def export_to_excel():
        conn = sqlite3.connect('school_data.db')
        query = "SELECT * FROM students"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Сохраняем в Excel
        df.to_excel('students.xlsx', index=False)
        print("✅ Данные экспортированы в students.xlsx")


    if __name__ == "__main__":
        init_db()
        export_to_excel()  # Экспорт в Excel