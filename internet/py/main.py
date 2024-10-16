import json
import aiohttp
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Инициализация бота и диспетчера с памятью
bot = Bot('6963877013:AAFUrMcy-J8K6syj4_KLoEZVuMbCZ2hFpt0')  # Используем переменную окружения
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Определение состояний формы
class Form(StatesGroup):
    name = State()
    location = State()
    manual_location = State()
    phone_number = State()
    manual_phone_number = State()

# Функция для отправки данных в группу Telegram
async def send_data_to_telegram(data):
    try:
        await bot.send_message(chat_id="-1002352220560", text=data)
        print("Данные успешно отправлены в группу.")  # Отладочный вывод
    except Exception as e:
        print("Ошибка при отправке сообщения в Telegram:", e)

# Функция для получения данных с сайта
async def fetch_data_from_website():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://script.google.com/macros/s/AKfycbxhJFzSdNm8O5bbH4MEEzahMn9LZJVZoLjKzGKlTms8VcnWOEkn7h61Dsqc7ETHgmBBKQ/exec') as response:
                if response.status != 200:
                    raise ValueError(f"Ошибка получения данных: {response.status}")
                data = await response.json()
                return data
    except Exception as e:
        print("Ошибка при получении данных с веб-сайта:", e)
        return None

# Стартовая команда
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    inline_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    inline_markup.add(KeyboardButton('Veb-sahifani oching', web_app=WebAppInfo(url='https://script.google.com/macros/s/AKfycbxhJFzSdNm8O5bbH4MEEzahMn9LZJVZoLjKzGKlTms8VcnWOEkn7h61Dsqc7ETHgmBBKQ/exec')))
    
    await message.answer("🎉 Muffins’ga xush kelibsiz! 🎂🍰\n"
                         "Bu yerda siz mazali tortlar, shirinliklar, ichimliklar va ajoyib desertlarni topasiz.\n"
                         "Shirin taomlar sarguzashtingizni hoziroq boshlang! 🍭🧁\n"
                         "Buyurtma berish uchun quyidagi tugmani bosing. 👇", reply_markup=inline_markup)

# Обработчик для данных с веб-приложения
@dp.message_handler(content_types=['web_app_data'])
async def web_app(message: types.Message, state: FSMContext):
    res = json.loads(message.web_app_data.data)

    async with state.proxy() as data:
        data['items'] = res  

    await message.answer("Iltimos, mahsulotni etkazib berish uchun malutni to'ldiring.\n"
                         "Ismingiz", reply_markup=ReplyKeyboardRemove())
    await Form.name.set()

# Запрос имени пользователя
@dp.message_handler(state=Form.name)
async def ask_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    location_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    location_markup.add(KeyboardButton('Geografik joylashuvni yuborish', request_location=True))
    location_markup.add(KeyboardButton('Qo\'lda kiriting'))
    await Form.location.set()
    await message.answer('Yetkazib berish joyini belgilang:', reply_markup=location_markup)

# Обработчик ручного ввода адреса
@dp.message_handler(lambda message: message.text == 'Qo\'lda kiriting', state=Form.location)
async def manual_location(message: types.Message):
    await Form.manual_location.set()
    await message.answer('Manzilni qo\'lda kiriting:', reply_markup=ReplyKeyboardRemove())

# Получение вручную введенного адреса
@dp.message_handler(state=Form.manual_location)
async def receive_manual_location(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['location'] = message.text
    await ask_phone_number(message, state)  # Передаем state

# Получение геопозиции
@dp.message_handler(content_types=['location'], state=Form.location)
async def receive_location(message: types.Message, state: FSMContext):
    latitude = message.location.latitude
    longitude = message.location.longitude
    async with state.proxy() as data:
        data['location'] = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
    await ask_phone_number(message, state)  # Передаем state

# Запрос номера телефона
async def ask_phone_number(message: types.Message, state: FSMContext):
    phone_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    phone_markup.add(KeyboardButton('Telefon raqamini yuboring', request_contact=True))
    phone_markup.add(KeyboardButton('Qo\'lda kiriting'))
    await Form.phone_number.set()
    await message.answer('Iltimos, telefon raqamingizni quyidagi manzilga yuboring:', reply_markup=phone_markup)

# Обработчик ручного ввода номера телефона
@dp.message_handler(lambda message: message.text == 'Qo\'lda kiriting', state=Form.phone_number)
async def manual_phone_number(message: types.Message):
    await Form.manual_phone_number.set()
    await message.answer('Telefon raqamingizni kiriting:', reply_markup=ReplyKeyboardRemove())

# Получение вручную введенного номера телефона
@dp.message_handler(state=Form.manual_phone_number)
async def receive_manual_phone_number(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone_number'] = message.text
    await send_summary(message, state)

# Получение номера телефона из контакта
@dp.message_handler(content_types=['contact'], state=Form.phone_number)
async def receive_phone_number(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone_number'] = message.contact.phone_number
    await send_summary(message, state)

# Подсчет общей суммы
def calculate_total_price(items):
    total = 0
    for item in items:
        price = item.get('price')
        quantity = item.get('quantity')

        try:
            if isinstance(price, str):
                price = price.replace('Narxi: ', '').strip()
                price = float(price)
            if isinstance(quantity, str):
                quantity = int(quantity)

            if isinstance(price, (int, float)) and isinstance(quantity, int) and quantity >= 0:
                total += price * quantity
            else:
                print(f"Ошибка: Неверные данные для товара {item}")
        except ValueError as e:
            print(f"Ошибка преобразования: {e} для товара {item}")
    return total

# Отправка итоговой информации и завершение состояния
async def send_summary(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # Проверка заполненности данных
        if not all(key in data for key in ['name', 'location', 'phone_number']):
            print("Ошибка: Не хватает данных для отправки.")
            await message.answer("Произошла ошибка, недостаточно данных.")
            await state.finish()
            return

        user_info = (
            f"Mijoz Ismi: {data['name']}\n"
            f"Yetkazib berish manzili: {data['location']}\n"
            f"Telefon: {data['phone_number']}\n\n"
            f"=========================\n"
            f"Buyurtma qilingan mahsulotlar:\n"
            f"=========================\n"
        )

        # Проверка на наличие товаров
        if not data.get('items'):
            await message.answer("Нет товаров для отправки.")
            await state.finish()
            return

        formatted_items = ""
        photo_messages = []

        for item in data.get('items', []):
            formatted_items += (
                f"Rasm: {item['imgSrc']}\n"
                f"{item['title']}\n"
                f"{item['price']}\n"
                f"Soni: {item['quantity']}\n"
                f"Hajmi: {item.get('size', 'N/A')}\n"  # Use .get() to avoid KeyError
                f"Rangi: {item.get('color', 'N/A')}\n"  # Also do this for other fields if needed
                f"=========================\n"
            )

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(item['imgSrc']) as response:
                        if response.status == 200:
                            photo_data = await response.read()
                            photo_messages.append((photo_data, item['title']))
                        else:
                            photo_messages.append((None, item['title']))
            except Exception as e:
                print(f"Ошибка загрузки изображения для {item['title']}: {e}")

        total_price = calculate_total_price(data.get('items', []))
        user_info += formatted_items
        user_info += f"Jami summa: {total_price}\n"

        # Отправка данных в группу
        await send_data_to_telegram(user_info)

    await message.answer("Buyurtmangiz qabul qilindi. Rahmat!", reply_markup=ReplyKeyboardRemove())
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
