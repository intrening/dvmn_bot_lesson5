import os
import json
import logging
import redis

from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from elasticpath import (
    fetch_products, get_product, get_image_url, add_to_cart, show_cart,
)

_database = None

def start(bot, update):
    """
    Хэндлер для состояния START.
    """
    reply_markup = get_menu_keyboard_markup()
    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_menu(bot, update):
    """
    Хэндлер для состояния HANDLE_MENU.
    """
    query = update.callback_query
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )
    if query.data == 'HANDLE_CART':
        keyboard = [
            [InlineKeyboardButton('В меню', callback_data='HANDLE_MENU')]
        ]
        bot.send_message(
            text=show_cart(chat_id=query.message.chat_id),
            chat_id=query.message.chat_id,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return 'HANDLE_CART'

    product = get_product(id=query.data)
    product_info = f"{product['name']}\n{product['description']}\nЦена {product['price'][0]['amount']/100} {product['price'][0]['currency']}\n"
    image_url = get_image_url(
        id=product['relationships']['main_image']['data']['id']
    )
    quantity_choises_list = [1, 5, 10]
    choise_keyboard = []
    for quantity in quantity_choises_list:
        choise_keyboard.append(
            InlineKeyboardButton(f'+{quantity} кг',
            callback_data=f'{query.data} {quantity}'),
        )
    keyboard = [
        choise_keyboard,
        [InlineKeyboardButton('Назад', callback_data='HANDLE_MENU')],
    ]
    bot.send_photo(
        chat_id=query.message.chat_id,
        photo=image_url,
        caption=product_info,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return 'HANDLE_DESCRIPTION'


def handle_description(bot, update):
    query = update.callback_query
    if query.data == 'HANDLE_MENU':
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        bot.send_message(
            text='Meню:',
            chat_id=query.message.chat_id,
            reply_markup=get_menu_keyboard_markup(),
        )
        return 'HANDLE_MENU'
    prod_id, quantity = query.data.split(' ')
    add_to_cart(
        prod_id=prod_id,
        quantity=quantity,
        chat_id=query.message.chat_id
    )
    return 'HANDLE_DESCRIPTION'

def handle_cart(bot, update):
    query = update.callback_query
    if query.data == 'HANDLE_MENU':
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        bot.send_message(
            text='Meню:',
            chat_id=query.message.chat_id,
            reply_markup=get_menu_keyboard_markup(),
        )
        return 'HANDLE_MENU'
    return 'HANDLE_CART'


def get_menu_keyboard_markup():
    keyboard = []
    for product in fetch_products():
        keyboard.append(
            [InlineKeyboardButton(product['name'], callback_data=product['id'])]
        )
    keyboard.append(
        [InlineKeyboardButton('Корзина', callback_data='HANDLE_CART')]
    )
    return InlineKeyboardMarkup(keyboard)


def handle_users_reply(bot, update):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.

    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")
    
    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(bot, update)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)

def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = os.getenv("DATABASE_PASSWORD")
        database_host = os.getenv("DATABASE_HOST")
        database_port = os.getenv("DATABASE_PORT")
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
