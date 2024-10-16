import logging 
import uuid
import os
import gspread
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from oauth2client.service_account import ServiceAccountCredentials

API_TOKEN = '7913746569:AAGY3NkLTlGadzKhDFJ9t1TwzU-v8Ak1yZc'
SPREADSHEET_ID = '19ON_2opSuF8pMwiqkCnXaTgPTxAobROY1FN3VPYbWiM'
SHEET_NAME = 'form data'

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера с FSM
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Определяем состояния для FSM
class OrderForm(StatesGroup):
    product_name = State()
    price = State()
    size = State()  # Добавили size
    color = State()  # Добавили color
    photo = State()
    comment = State()

# Функция записи данных в Google Sheets
def update_google_sheet(data):
    """Updates Google Sheets with the provided data."""
    try:
        # Настройка доступа к Google Sheets API
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('internet/service_account.json', scope)
        client = gspread.authorize(creds)

        # Открываем таблицу
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

        # Подготавливаем данные для записи
        product_id = data['product_id']
        product_name = data['product_name']
        price = data['price']
        sizes = ', '.join(data['sizes'])
        colors = ', '.join(data['colors'])
        comment = data['comment']
        photo = data['photo']

        # Записываем строку в таблицу
        sheet.append_row([product_id, product_name, price, sizes, colors, comment, photo])

        logging.info("Данные успешно обновлены в Google Sheets.")
    except Exception as e:
        logging.error(f"Ошибка при записи данных в Google Sheets: {e}")

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Welcomes the user and prompts for product name."""
    await message.answer("Assalomu alaykum! Tovar nomini kiriting:")
    await OrderForm.product_name.set()

# Обрабатываем ввод товара
@dp.message_handler(state=OrderForm.product_name)
async def process_product_name(message: types.Message, state: FSMContext):
    """Processes the product name input."""
    await state.update_data(product_name=message.text)
    
    # Генерируем уникальный ID
    product_id = str(uuid.uuid4())
    await state.update_data(product_id=product_id)
    
    await message.answer("Narxini kiriting:")
    await OrderForm.next()

# Обрабатываем ввод цены
@dp.message_handler(state=OrderForm.price)
async def process_price(message: types.Message, state: FSMContext):
    """Processes the price input."""
    if not message.text.isdigit():
        await message.answer("Narx raqam bo'lishi kerak. Iltimos, qaytadan kiriting.")
        return
    await state.update_data(price=message.text)
    
    await message.answer("Razmerlarni kiriting (masalan, S, M, L):")  # Запрашиваем размер
    await OrderForm.size.set()

# Обрабатываем ввод размеров
@dp.message_handler(state=OrderForm.size)
async def process_size(message: types.Message, state: FSMContext):
    sizes = message.text.split(',')  # Разделяем введённые размеры по запятой
    sizes = [size.strip() for size in sizes]  # Убираем лишние пробелы
    
    await state.update_data(sizes=sizes)  # Сохраняем размеры в состоянии
    await message.answer(f"Tanlangan razmlar: {', '.join(sizes)}.")
    await message.answer("Ranglarni kiriting (masalan, Qora, Oq, Sariq):")
    await OrderForm.color.set()  # Переходим к вводу цветов

# Обрабатываем ввод цветов
@dp.message_handler(state=OrderForm.color)
async def process_color(message: types.Message, state: FSMContext):
    colors = message.text.split(',')  # Разделяем введённые цвета по запятой
    colors = [color.strip() for color in colors]  # Убираем лишние пробелы
    
    await state.update_data(colors=colors)  # Сохраняем цвета в состоянии
    await message.answer(f"Tanlangan ranglar: {', '.join(colors)}.")
    await message.answer("Tovar rasmini yuboring:", reply_markup=types.ReplyKeyboardRemove())
    await OrderForm.photo.set()  # Переходим к вводу фото

# Обрабатываем фото товара
@dp.message_handler(content_types=['photo'], state=OrderForm.photo)
async def process_photo(message: types.Message, state: FSMContext):
    """Processes the product photo upload."""
    photos_folder = r'internet\photos'
    if not os.path.exists(photos_folder):
        os.makedirs(photos_folder)

    # Сохраняем фото локально
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    
    file_name = os.path.join(photos_folder, f"{uuid.uuid4()}.jpg")
    with open(file_name, 'wb') as new_file:
        new_file.write(downloaded_file.getvalue())
    
    # Сохраняем путь к фото в состоянии
    await state.update_data(photo=file_name)
    
    await message.answer("Izoh yozing (ixtiyoriy):")
    await OrderForm.comment.set()

# Обрабатываем ввод комментария
@dp.message_handler(state=OrderForm.comment)
async def process_comment(message: types.Message, state: FSMContext):
    """Processes the optional comment input."""
    await state.update_data(comment=message.text)
    
    data = await state.get_data()
    update_google_sheet(data)  # Записываем данные в Google Sheets
    await message.answer("Ma'lumotlar muvaffaqiyatli saqlandi! Rahmat!")
    
    await state.finish()  # Завершаем состояние

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
