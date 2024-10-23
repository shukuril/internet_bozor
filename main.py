import os
import cv2
import hashlib
import sqlite3
import logging
import asyncio
from io import BytesIO
from datetime import datetime, timedelta
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram import exceptions

# Токен бота и ID группы
API_TOKEN = '7604436096:AAGTe3EfSOY2E3GS1JNfIP99xrrsTc7eD38'  # Ваш токен бота
GROUP_ID = -1002329576670  # Ваш ID группы

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Логирование
logging.basicConfig(level=logging.INFO)

# Подключение к БД
def get_db_connection():
    return sqlite3.connect('reports.db')

# Создание таблиц для хранения данных
def create_tables():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY,
            branch_name TEXT,
            image_hash TEXT,
            image_path TEXT,
            date TIMESTAMP
        )
        ''')
        cur.execute('''
        CREATE TABLE IF NOT EXISTS branches (
            user_id INTEGER PRIMARY KEY,
            branch_name TEXT
        )
        ''')
        conn.commit()

create_tables()

# Словарь для временного хранения филиалов пользователей
user_branch_cache = {}

# Команда /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT branch_name FROM branches WHERE user_id = ?", (user_id,))
        result = cur.fetchone()

    if result:
        await message.answer(f"Привет! Вы уже зарегистрированы как филиал: {result[0]}.")
    else:
        await message.answer("Привет! Пожалуйста, укажите название вашего филиала.")
        user_branch_cache[user_id] = None

# Обработчик текста для сохранения названия филиала
@dp.message_handler(lambda message: message.text and message.from_user.id in user_branch_cache)
async def set_branch_name(message: types.Message):
    user_id = message.from_user.id
    branch_name = message.text.strip()

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO branches (user_id, branch_name) VALUES (?, ?)", (user_id, branch_name))
        conn.commit()

    del user_branch_cache[user_id]
    await message.answer(f"Филиал {branch_name} успешно сохранён! Загрузите фото отчет.")

# Функция для хеширования изображения
def hash_image(image_path):
    """Создает хеш изображения для быстрой проверки дубликатов."""
    with open(image_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

# Функция для сравнения изображений с помощью SSIM
def is_duplicate_image(image_path1, image_path2, threshold=0.9):
    image1 = cv2.imread(image_path1)
    image2 = cv2.imread(image_path2)

    # Приведение изображений к одному размеру
    image1 = cv2.resize(image1, (300, 300))
    image2 = cv2.resize(image2, (300, 300))

    # Конвертация в градации серого
    gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

    # Вычисление SSIM
    similarity_index, _ = ssim(gray1, gray2, full=True)

    return similarity_index >= threshold

# Функция для вычисления гистограммы цвета изображения
def get_color_histogram(image_path):
    image = cv2.imread(image_path)
    image = cv2.resize(image, (300, 300))
    hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()

# Функция для сравнения гистограмм
def is_histogram_similar(hist1, hist2, threshold=0.9):
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return similarity >= threshold

# Обработка фотографий
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT branch_name FROM branches WHERE user_id = ?", (user_id,))
        branch_result = cur.fetchone()

    if not branch_result:
        await message.answer("Пожалуйста, сначала укажите название вашего филиала с помощью команды /start.")
        return

    branch_name = branch_result[0]

    # Скачиваем фото
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file_by_id(photo.file_id)
    except exceptions.BotBlocked:
        await message.answer("Не могу получить фото. Проверьте доступ боту.")
        return
    except Exception as e:
        await message.answer(f"Ошибка при скачивании фото: {e}")
        logging.error(f"Ошибка при скачивании фото: {e}")
        return

    # Сохранение фото локально
    photo_dir = f"photos/{branch_name}"
    os.makedirs(photo_dir, exist_ok=True)
    photo_path = os.path.join(photo_dir, f"{datetime.now().timestamp()}.jpg")

    try:
        with open(photo_path, 'wb') as new_file:
            new_file.write(downloaded_file)
    except Exception as e:
        await message.answer(f"Ошибка при сохранении фото: {e}")
        logging.error(f"Ошибка при сохранении фото: {e}")
        return

    # Проверка на дубликаты по хешу
    new_image_hash = hash_image(photo_path)
    new_image_hist = get_color_histogram(photo_path)

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT image_hash, image_path FROM reports WHERE branch_name = ?", (branch_name,))
        existing_images = cur.fetchall()

    is_duplicate = False

    for (existing_image_hash, existing_image_path) in existing_images:
        if new_image_hash == existing_image_hash:
            is_duplicate = True
            break
        elif is_duplicate_image(photo_path, existing_image_path):
            is_duplicate = True
            break
        else:
            existing_image_hist = get_color_histogram(existing_image_path)
            if is_histogram_similar(new_image_hist, existing_image_hist):
                is_duplicate = True
                break

    if not is_duplicate:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO reports (branch_name, image_hash, image_path, date) VALUES (?, ?, ?, ?)",
                            (branch_name, new_image_hash, photo_path, datetime.now()))
                conn.commit()
                logging.info(f"Отчет сохранен: {branch_name}, {new_image_hash}, {photo_path}")  # Логируем успешное добавление
            await message.answer("Фото успешно загружено.")
        except Exception as e:
            await message.answer(f"Ошибка при сохранении отчета в БД: {e}")
            logging.error(f"Ошибка при сохранении отчета в БД: {e}")
    else:
        os.remove(photo_path)  # Удаляем дубликат
        await message.answer("Фото является дубликатом и было удалено.")

# Функция для создания коллажа
def create_collage(images):
    collage_width = 800
    collage_height = 800
    collage = Image.new('RGB', (collage_width, collage_height))

    for index, image in enumerate(images):
        img = image.resize((collage_width // 2, collage_height // 2))
        x = (index % 2) * (collage_width // 2)
        y = (index // 2) * (collage_height // 2)
        collage.paste(img, (x, y))

    return collage

# Функция для отправки ежедневного отчета
async def send_daily_report():
    yesterday = datetime.now() - timedelta(days=1)

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT branch_name, image_path FROM reports WHERE date >= ?", (yesterday,))
        reports = cur.fetchall()

    daily_report_count = len(reports)

    if reports:
        branch_images = {}
        for branch_name, image_path in reports:
            if branch_name not in branch_images:
                branch_images[branch_name] = []
            branch_images[branch_name].append(image_path)

        for branch_name, image_paths in branch_images.items():
            for i in range(0, len(image_paths), 4):
                collage_images = [Image.open(path) for path in image_paths[i:i+4]]
                collage = create_collage(collage_images)

                collage_io = BytesIO()
                collage.save(collage_io, format='JPEG')
                collage_io.seek(0)

                # Изменено: передаем collage_io напрямую в InputFile
                await bot.send_photo(GROUP_ID, types.InputFile(collage_io, filename=f"report_{branch_name}.jpg"),
                                     caption=f"Ежедневный отчет филиала {branch_name} ({daily_report_count} отчетов за день)")

# Функция для отправки ежемесячного отчета
async def send_monthly_report():
    first_day_of_month = datetime.now().replace(day=1)
    last_day_of_last_month = first_day_of_month - timedelta(days=1)
    first_day_of_last_month = last_day_of_last_month.replace(day=1)

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT branch_name, image_path FROM reports WHERE date >= ? AND date < ?", 
                    (first_day_of_last_month, first_day_of_month))
        reports = cur.fetchall()

    monthly_report_count = len(reports)
    logging.info(f"Найдено {monthly_report_count} отчетов для месячного отчета")

    if reports:
        branch_images = {}
        for branch_name, image_path in reports:
            if branch_name not in branch_images:
                branch_images[branch_name] = []
            branch_images[branch_name].append(image_path)

        for branch_name, image_paths in branch_images.items():
            for i in range(0, len(image_paths), 4):
                collage_images = [Image.open(path) for path in image_paths[i:i+4]]
                collage = create_collage(collage_images)

                collage_io = BytesIO()
                collage.save(collage_io, format='JPEG')
                collage_io.seek(0)

                await bot.send_photo(GROUP_ID, types.InputFile(collage_io, f"monthly_report_{branch_name}.jpg"),
                                     caption=f"Ежемесячный отчет филиала {branch_name} ({monthly_report_count} отчетов за месяц)")
    else:
        logging.info("Нет отчетов для отправки в месячном отчете.")

# Настройка планировщика для ежедневного отчета
scheduler = AsyncIOScheduler()
scheduler.add_job(send_daily_report, 'cron', hour=12, minute=45)  # Ежедневно в 8:00

# Настройка планировщика для ежемесячного отчета
scheduler.add_job(send_monthly_report, 'cron', day=1, hour=8, minute=00)  # Каждый месяц в 8:00 первого числа

# Запуск планировщика
scheduler.start()

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
