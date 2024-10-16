const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

// Инициализация бота
const bot = new TelegramBot('6963877013:AAFUrMcy-J8K6syj4_KLoEZVuMbCZ2hFpt0', { polling: true });

// Хранение данных пользователя (упрощенная замена FSM)
let userData = {};

// Функция для отправки данных в Telegram группу
async function sendDataToTelegram(data) {
    try {
        await bot.sendMessage("-1002352220560", data);
        console.log("Данные успешно отправлены в группу.");
    } catch (error) {
        console.error("Ошибка при отправке сообщения в Telegram:", error);
    }
}

// Функция для получения данных с сайта
async function fetchDataFromWebsite() {
    try {
        const response = await axios.get('https://script.google.com/macros/s/AKfycbxhJFzSdNm8O5bbH4MEEzahMn9LZJVZoLjKzGKlTms8VcnWOEkn7h61Dsqc7ETHgmBBKQ/exec');
        return response.data;
    } catch (error) {
        console.error("Ошибка при получении данных с веб-сайта:", error);
        return null;
    }
}

// Стартовая команда
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;

    const webAppButton = {
        text: 'Veb-sahifani oching',
        web_app: { url: 'https://script.google.com/macros/s/AKfycbxhJFzSdNm8O5bbH4MEEzahMn9LZJVZoLjKzGKlTms8VcnWOEkn7h61Dsqc7ETHgmBBKQ/exec' }
    };

    const options = {
        reply_markup: {
            keyboard: [[webAppButton]],
            resize_keyboard: true
        }
    };

    bot.sendMessage(chatId, "🎉 Muffins’ga xush kelibsiz! 🎂🍰\nBuyurtma berish uchun quyidagi tugmani bosing.", options);
});

// Обработчик данных с веб-приложения
bot.on('message', (msg) => {
    if (msg.web_app_data) {
        const chatId = msg.chat.id;
        const data = JSON.parse(msg.web_app_data.data);
        userData[chatId] = { items: data };

        bot.sendMessage(chatId, "Iltimos, ismingizni kiriting:");
    }
});

// Запрос имени пользователя
bot.on('message', (msg) => {
    const chatId = msg.chat.id;

    if (!userData[chatId]?.name && msg.text) {
        userData[chatId].name = msg.text;
        bot.sendMessage(chatId, "Yetkazib berish manzilini kiriting:");
    } else if (userData[chatId]?.name && !userData[chatId].location && msg.text) {
        userData[chatId].location = msg.text;
        bot.sendMessage(chatId, "Telefon raqamingizni kiriting:");
    } else if (userData[chatId]?.location && !userData[chatId].phone_number && msg.text) {
        userData[chatId].phone_number = msg.text;
        sendSummary(chatId);
    }
});

// Подсчет общей суммы
function calculateTotalPrice(items) {
    let total = 0;
    items.forEach(item => {
        let price = parseFloat(item.price.replace('Narxi: ', '').trim());
        let quantity = parseInt(item.quantity);
        total += price * quantity;
    });
    return total;
}

// Отправка итоговой информации
async function sendSummary(chatId) {
    const data = userData[chatId];
    if (!data || !data.items || !data.name || !data.location || !data.phone_number) {
        bot.sendMessage(chatId, "Произошла ошибка, недостаточно данных.");
        return;
    }

    let summary = `Mijoz Ismi: ${data.name}\nYetkazib berish manzili: ${data.location}\nTelefon: ${data.phone_number}\n\n=========================\nBuyurtma qilingan mahsulotlar:\n=========================\n`;

    data.items.forEach(item => {
        summary += `Rasm: ${item.imgSrc}\n${item.title}\n${item.price}\nSoni: ${item.quantity}\n=========================\n`;
    });

    const totalPrice = calculateTotalPrice(data.items);
    summary += `Jami summa: ${totalPrice}\n`;

    await sendDataToTelegram(summary);
    bot.sendMessage(chatId, "Buyurtmangiz qabul qilindi. Rahmat!");
}
