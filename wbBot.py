import telebot
from telebot import types
import requests
from io import BytesIO

TOKEN = 'API-TOKEN'
bot = telebot.TeleBot(TOKEN)

user_states = {}
user_language = {}

texts = {
    "welcome": {
        "ru": "Добро пожаловать! Выберите команду ниже:",
        "tj": "Хуш омадед! Лутфан фармонро интихоб кунед:"
    },
    "choose_language": "Выберите язык / Забонро интихоб кунед:",
    "main_menu": {
        "ru": "🏠 Главное меню",
        "tj": "🏠 Менюи асосӣ"
    },
    "help": {
        "ru": "📌 Команды:\n• Поиск товара 🔍\n• Проверка статуса заказа 📋\n• История заказов 📦\n• Текущие акции 🎁\n• Сменить язык 🌐",
        "tj": "📌 Фармонҳо:\n• Ҷустуҷӯи мол 🔍\n• Санҷиши ҳолати фармоиш 📋\n• Таърихи фармоиш 📦\n• Тахфифҳои ҷорӣ 🎁\n• Иваз кардани забон 🌐"
    },
    "enter_name": {
        "ru": "Введите название товара:",
        "tj": "Номи молро бо забони русси ворид кунед:"
    },
    "enter_price": {
        "ru": "На какую сумму рассчитываете? (укажите только число в ₽)",
        "tj": "Маблағи максимумро ворид кунед (танҳо рақам бо ₽):"
    },
    "not_number": {
        "ru": "Пожалуйста, введите число без лишних символов.",
        "tj": "Лутфан танҳо рақам ворид кунед, бе рамзҳои иловагӣ."
    },
    "no_results": {
        "ru": "❌ Не найдено товаров по заданным параметрам.",
        "tj": "❌ Мол мувофиқи шартҳо ёфт нашуд."
    },
    "enter_order": {
        "ru": "Введите номер заказа:",
        "tj": "Рақами фармоишро ворид кунед:"
    },
    "enter_user_id": {
        "ru": "Введите ID пользователя:",
        "tj": "ID-и истифодабарандаро ворид кунед:"
    },
    "no_orders": {
        "ru": "❌ Заказы не найдены.",
        "tj": "❌ Фармоиш ёфт нашуд."
    },
    "current_sales": {
        "ru": "🔔 Сейчас нет активных акций.",
        "tj": "🔔 Ҳоло тахфифҳои фаъол вуҷуд надоранд."
    }
}

@bot.message_handler(commands=["start"])
def handle_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Русский"), types.KeyboardButton("Тоҷикӣ"))
    bot.send_message(message.chat.id, texts["choose_language"], reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["Русский", "Тоҷикӣ"])
def set_language(msg):
    lang = "ru" if msg.text == "Русский" else "tj"
    user_language[msg.chat.id] = lang
    user_states[msg.chat.id] = {}
    bot.send_message(msg.chat.id, texts["welcome"][lang], reply_markup=get_main_menu(lang))

@bot.message_handler(func=lambda msg: msg.text.lower() in ["главное меню 🏠", "менюи асосӣ 🏠"])
def back_to_main(msg):
    lang = user_language.get(msg.chat.id, "ru")
    bot.send_message(msg.chat.id, texts["main_menu"][lang], reply_markup=get_main_menu(lang))

@bot.message_handler(func=lambda msg: msg.text.lower() in ["помощь ❓", "кӯмак ❓"])
def help_info(msg):
    lang = user_language.get(msg.chat.id, "ru")
    bot.send_message(msg.chat.id, texts["help"][lang], reply_markup=get_main_menu(lang))

@bot.message_handler(func=lambda msg: msg.text.lower() in ["сменить язык 🌐", "иваз кардани забон 🌐"])
def change_language(msg):
    handle_start(msg)

@bot.message_handler(func=lambda msg: msg.text.lower() in ["пункты выдачи 📍", "нуқтаҳои гирифтани мол 📍"])
def pickup_points(msg):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗺 Открыть карту/Харитаро кушоед🗺", url="https://www.wildberries.ru/services/besplatnaya-dostavka"))
    lang = user_language.get(msg.chat.id, "ru")
    text = "Нажмите, чтобы открыть карту пунктов выдачи:" if lang == "ru" else "Барои дидани нуқтаҳои гирифтани мол клик кунед:"
    bot.send_message(msg.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text.lower() in ["поиск товара 🔍", "ҷустуҷӯи мол 🔍"])
def search_product(msg):
    user_states[msg.chat.id] = {"step": "awaiting_query"}
    lang = user_language.get(msg.chat.id, "ru")
    bot.send_message(msg.chat.id, texts["enter_name"][lang], reply_markup=get_back_menu(lang))

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id, {}).get("step") == "awaiting_query")
def handle_product_name(msg):
    user_states[msg.chat.id]["query"] = msg.text
    user_states[msg.chat.id]["step"] = "awaiting_price"
    lang = user_language.get(msg.chat.id, "ru")
    bot.send_message(msg.chat.id, texts["enter_price"][lang])

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id, {}).get("step") == "awaiting_price")
def fetch_product(msg):
    lang = user_language.get(msg.chat.id, "ru")
    if not msg.text.replace(" ", "").isdigit():
        bot.send_message(msg.chat.id, texts["not_number"][lang])
        return

    max_price = int(msg.text.strip())
    query = user_states[msg.chat.id].get("query")
    user_states[msg.chat.id] = {}

    url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={query}&curr=rub&dest=-1257786&resultset=catalog"
    response = requests.get(url)

    if response.status_code != 200:
        bot.send_message(msg.chat.id, "❌ API error")
        return

    results = response.json().get("data", {}).get("products", [])
    filtered = [p for p in results if p.get("salePriceU", 99999999) / 100 <= max_price][:10]

    if not filtered:
        bot.send_message(msg.chat.id, texts["no_results"][lang])
        return

    for product in filtered:
        name = product.get("name", "Без названия")
        price = product.get("salePriceU", 0) / 100
        brand = product.get("brand", "Без бренда")
        product_url = f"https://www.wildberries.ru/catalog/{product['id']}/detail.aspx"
        img_url = f"https://basket-{product['id'] // 1000000:02d}.wb.ru/vol{product['id'] // 100000}/{product['id'] // 1000}/{product['id']}/images/big/1.jpg"

        caption = (
            f"🛍️ <b>{name}</b>\n"
            f"🏷 <b>Бренд:</b> {brand}\n"
            f"💰 <b>Цена:</b> {price} ₽\n"
            f"🔗 <a href='{product_url}'>Смотреть на Wildberries</a>"
        )

        try:
            img_data = requests.get(img_url)
            if img_data.status_code == 200:
                image = BytesIO(img_data.content)
                image.name = "product.jpg"
                bot.send_photo(msg.chat.id, image, caption=caption, parse_mode="HTML")
            else:
                bot.send_message(msg.chat.id, caption, parse_mode="HTML")
        except:
            bot.send_message(msg.chat.id, caption, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text.lower() in ["проверка статуса заказа 📋", "санҷиши ҳолати фармоиш 📋"])
def check_order_status(msg):
    user_states[msg.chat.id] = {"step": "awaiting_order"}
    lang = user_language.get(msg.chat.id, "ru")
    bot.send_message(msg.chat.id, texts["enter_order"][lang], reply_markup=get_back_menu(lang))

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id, {}).get("step") == "awaiting_order")
def handle_order_check(msg):
    user_states[msg.chat.id] = {}
    order_id = msg.text.strip()
    lang = user_language.get(msg.chat.id, "ru")

    mock_status = {
        "1001": "📦 Заказ №1001 — Получен",
        "1002": "🚚 Заказ №1002 — В пути",
        "1003": "📍 Заказ №1003 — В пункте выдачи"
    }

    status = mock_status.get(order_id, texts["no_orders"][lang])
    bot.send_message(msg.chat.id, status)

@bot.message_handler(func=lambda msg: msg.text.lower() in ["история заказов 📦", "таърихи фармоиш 📦"])
def order_history(msg):
    user_states[msg.chat.id] = {"step": "awaiting_user_id"}
    lang = user_language.get(msg.chat.id, "ru")
    bot.send_message(msg.chat.id, texts["enter_user_id"][lang], reply_markup=get_back_menu(lang))

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id, {}).get("step") == "awaiting_user_id")
def handle_history(msg):
    user_states[msg.chat.id] = {}
    lang = user_language.get(msg.chat.id, "ru")

    mock_data = {
        "user1": ["📦 Заказ №1001 — Получен", "📦 Заказ №1002 — В пути"]
    }

    orders = mock_data.get(msg.text.strip())
    if not orders:
        bot.send_message(msg.chat.id, texts["no_orders"][lang])
    else:
        bot.send_message(msg.chat.id, "\n".join(orders))

@bot.message_handler(func=lambda msg: msg.text.lower() in ["текущие акции 🎁", "тахфифҳои ҷорӣ 🎁"])
def current_sales(msg):
    lang = user_language.get(msg.chat.id, "ru")
    bot.send_message(msg.chat.id, texts["current_sales"][lang], reply_markup=get_back_menu(lang))

def get_main_menu(lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "ru":
        markup.add(
            types.KeyboardButton("Пункты выдачи 📍"),
            types.KeyboardButton("Поиск товара 🔍"),
            types.KeyboardButton("История заказов 📦"),
            types.KeyboardButton("Проверка статуса заказа 📋"),
            types.KeyboardButton("Текущие акции 🎁"),
            types.KeyboardButton("Помощь ❓"),
            types.KeyboardButton("Сменить язык 🌐")
        )
    else:
        markup.add(
            types.KeyboardButton("Нуқтаҳои гирифтани мол 📍"),
            types.KeyboardButton("Ҷустуҷӯи мол 🔍"),
            types.KeyboardButton("Таърихи фармоиш 📦"),
            types.KeyboardButton("Санҷиши ҳолати фармоиш 📋"),
            types.KeyboardButton("Тахфифҳои ҷорӣ 🎁"),
            types.KeyboardButton("Кӯмак ❓"),
            types.KeyboardButton("Иваз кардани забон 🌐")
        )
    return markup


def get_back_menu(lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    text = "Главное меню 🏠" if lang == "ru" else "Менюи асосӣ 🏠"
    markup.add(types.KeyboardButton(text))
    return markup

@bot.message_handler(commands=["start"])
def cmd_start(message):
    handle_start(message)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    help_info(message)

@bot.message_handler(commands=["pickup_points"])
def cmd_pickup_points(message):
    pickup_points(message)

@bot.message_handler(commands=["search_product"])
def cmd_search_product(message):
    search_product(message)

@bot.message_handler(commands=["check_order_status"])
def cmd_check_order_status(message):
    check_order_status(message)

@bot.message_handler(commands=["order_history"])
def cmd_order_history(message):
    order_history(message)

@bot.message_handler(commands=["current_sales"])
def cmd_current_sales(message):
    current_sales(message)

@bot.message_handler(commands=["back"])
def cmd_back(message):
    back_to_main(message)


bot.polling(none_stop=True)
