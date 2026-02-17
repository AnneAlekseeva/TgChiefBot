import telebot
from telebot import types
import json
import requests
import pandas as pd
from io import StringIO
import random

# Токен бота для доступа к API Telegram
token = "your token"
bot = telebot.TeleBot(token, threaded=False)
# URL для загрузки CSV данных с рецептами
url = "https://storage.yandexcloud.net/img-tg-bot/tg-bot-chief/rec_1000.csv"


# Загружает CSV файл с указанного URL и возвращает данные в виде DataFrame.
# Если загрузка или парсинг не удались, возвращает None.
def load_csv_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        csv_content = response.content.decode('utf-8')
        data = pd.read_csv(StringIO(csv_content))
        return data
    except requests.RequestException as error:
        print(f"Ошибка при загрузке данных: {error}")
        return None
    except pd.errors.ParserError as parse_error:
        print(f"Ошибка при парсинге CSV: {parse_error}")
        return None


data = load_csv_data(url)
if data is None:
    raise ValueError("Не удалось загрузить данные. Пожалуйста, проверьте URL и повторите попытку.")


# Ищет рецепты, содержащие указанные ингредиенты.
# Возвращает список найденных рецептов, отсортированный по количеству совпадений ингредиентов.
def search_recipes(ing_new):
    ing_new = set(ingredient.strip().lower() for ingredient in ing_new.split(','))
    recipes_found = []
    for index, row in data.iterrows():
        recipe_ingredients = set(x.strip().lower() for x in row['ing_new'].strip("[]").replace("'", "").split(','))
        match_count = len(ing_new & recipe_ingredients)
        if match_count > 0:  # проверка на пересечение множеств
            recipes_found.append(
                (row['name'], row['ingredients'], row['recipe'], row['photo'], row['energy'], match_count))
    # Сортировка по количеству совпадений
    recipes_found.sort(key=lambda x: x[5], reverse=True)
    # Находим максимальное количество совпадений
    max_matches = recipes_found[0][5] if recipes_found else 0
    # Отбираем все рецепты с наибольшим количеством совпадений
    top_recipes = [recipe for recipe in recipes_found if recipe[5] == max_matches]
    # Перемешивание списка топ-рецептов
    random.shuffle(top_recipes)
    top_recipes = [(name, ingredients, recipe, photo, energy) for name, ingredients, recipe, photo, energy, _ in
                   top_recipes]
    return top_recipes


# Общая функция для поиска рецептов по заданному пределу нутриента
def search_by_nutrient(nutrient, max_value):
    """
    Ищет рецепты, у которых значение указанного нутриента не превышает max_value.
    Возвращает список из всех подходящих рецептов, перемешанных в случайном порядке.
    """
    recipes_found = data[data[nutrient] <= max_value]
    recipes_list = list(
        recipes_found[['name', 'ingredients', 'recipe', 'photo', 'energy']].itertuples(index=False, name=None))
    random.shuffle(recipes_list)
    return recipes_list


# Обрабатывает входящие вебхуки от Telegram и передает обновления боту.
# Возвращает HTTP-ответ с результатом обработки.
def handler(event, context):
    try:
        body = json.loads(event['body'])
        update = telebot.types.Update.de_json(body)
        bot.process_new_updates([update])
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"message": "Update processed"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"error": str(e)})
        }


# Обрабатывает команду /start. Отправляет приветственное сообщение с кнопками для выбора.
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton('🥦Ингредиенты', callback_data='ing')
    btn2 = types.InlineKeyboardButton('🍏Энергетическая ценность', callback_data='energy')
    btn3 = types.InlineKeyboardButton('⁉️Помощь', callback_data='help')
    btn4 = types.InlineKeyboardButton('🤍Info', callback_data='info')
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id,
                     'Привет! Если ты мучаешься с выбором блюда, я помогу тебе определиться. И обещаю, что ты сойдешь с ума от моих идей 🤪\nВыбери, что ты хочешь посмотреть',
                     reply_markup=markup)


# Обрабатывает нажатия на инлайн-кнопки в приветственном сообщении.
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    bot.answer_callback_query(call.id)
    if call.data == 'ing':
        msg = bot.send_message(call.message.chat.id,
                               'Просто вводи свои ингредиенты через запятую, а я скину тебе крутую и вкусную подборку🫶')
        bot.register_next_step_handler(msg, handle_ingredients)
    elif call.data == 'help':
        bot.send_message(call.message.chat.id,
                         "Я твой бот-помощник, спасу тебя от мук выбора что сегодня приготовить. Выбери пункт «ингредиенты» и просто напиши мне, какие продукты у тебя есть.")
    elif call.data == 'info':
        bot.send_message(call.message.chat.id,
                         "Напиши /start, и мы начнем готовить!\nОтправь сердечко 🫶🏻 моим создателям @Chupchip90 @anyaalekkseeva")
    elif call.data == 'energy':
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_calories = types.InlineKeyboardButton('⛹🏻‍♀️Калории', callback_data='calories')
        btn_proteins = types.InlineKeyboardButton('🥩Белки', callback_data='proteins')
        btn_fats = types.InlineKeyboardButton('🥘Жиры', callback_data='fats')
        btn_carbs = types.InlineKeyboardButton('🍕Углеводы', callback_data='carbs')
        markup.add(btn_calories, btn_proteins, btn_fats, btn_carbs)
        bot.send_message(call.message.chat.id, "Выбирай, по какому критерию отбирать твои рецепты👇🏻",
                         reply_markup=markup)
    elif call.data == 'calories':
        msg = bot.send_message(call.message.chat.id, 'Введите предел калорий:')
        bot.register_next_step_handler(msg, handle_calories)
    elif call.data == 'proteins':
        msg = bot.send_message(call.message.chat.id, 'Введите предел белков:')
        bot.register_next_step_handler(msg, handle_proteins)
    elif call.data == 'fats':
        msg = bot.send_message(call.message.chat.id, 'Введите предел жиров:')
        bot.register_next_step_handler(msg, handle_fats)
    elif call.data == 'carbs':
        msg = bot.send_message(call.message.chat.id, 'Введите предел углеводов:')
        bot.register_next_step_handler(msg, handle_carbs)


user_data = {}


# Обрабатывает сообщение с ингредиентами от пользователя.
# Сохраняет данные о пользователе и найденных рецептах, затем отправляет рецепты.
def handle_ingredients(message):
    chat_id = message.chat.id
    user_data[chat_id] = {
        'ing_new': message.text,
        'recipes': search_recipes(message.text),
        'current_index': 0
    }
    send_recipes(chat_id)


def handle_calories(message):
    try:
        max_calories = int(message.text)
        chat_id = message.chat.id
        recipes = search_by_nutrient('Calories', max_calories)
        user_data[chat_id] = {
            'recipes': recipes,
            'current_index': 0
        }
        send_recipes(chat_id)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число.")
        msg = bot.send_message(message.chat.id, 'Введите предел калорий:')
        bot.register_next_step_handler(msg, handle_calories)


def handle_proteins(message):
    try:
        max_proteins = int(message.text)
        chat_id = message.chat.id
        recipes = search_by_nutrient('Proteins', max_proteins)
        user_data[chat_id] = {
            'recipes': recipes,
            'current_index': 0
        }
        send_recipes(chat_id)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число.")
        msg = bot.send_message(message.chat.id, 'Введите предел белков:')
        bot.register_next_step_handler(msg, handle_proteins)


def handle_fats(message):
    try:
        max_fats = int(message.text)
        chat_id = message.chat.id
        recipes = search_by_nutrient('Fats', max_fats)
        user_data[chat_id] = {
            'recipes': recipes,
            'current_index': 0
        }
        send_recipes(chat_id)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число.")
        msg = bot.send_message(message.chat.id, 'Введите предел жиров:')
        bot.register_next_step_handler(msg, handle_fats)


def handle_carbs(message):
    try:
        max_carbs = int(message.text)
        chat_id = message.chat.id
        recipes = search_by_nutrient('Carbohydrates', max_carbs)
        user_data[chat_id] = {
            'recipes': recipes,
            'current_index': 0
        }
        send_recipes(chat_id)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число.")
        msg = bot.send_message(message.chat.id, 'Введите предел углеводов:')
        bot.register_next_step_handler(msg, handle_carbs)


# Отправляет пользователю найденные рецепты.
# Показывает до 5 рецептов за раз
def send_recipes(chat_id):
    recipes = user_data[chat_id]['recipes']
    if not recipes:
        msg = bot.send_message(chat_id, "Я ничего не нашел для тебя 😔 Попробуй другие ингредиенты.")
        bot.register_next_step_handler(msg, handle_ingredients)
        return

    index = user_data[chat_id]['current_index']
    # return

    response = "Рецепты, которые я нашел для тебя:\n\nЧто хочешь из этого приготовить?😋Пиши цифру👇🏻\n"
    for i in range(index, min(index + 5, len(recipes))):
        response += f"{i + 1}. {recipes[i][0]}\n"

    markup = types.InlineKeyboardMarkup()
    if index + 5 < len(recipes):
        markup.add(types.InlineKeyboardButton('Пиши цифру 👇🏻', callback_data='more'))
    if index > 0:
        markup.add(types.InlineKeyboardButton('Назад', callback_data='back'))

    msg = bot.send_message(chat_id, response, )
    bot.register_next_step_handler(msg, handle_recipe_selection)


# Обрабатывает выбор рецепта пользователем.
# Отправляет подробную информацию о выбранном рецепте и его изображение.
def handle_recipe_selection(message):
    try:
        recipe_index = int(message.text) - 1
        chat_id = message.chat.id
        recipes = user_data[chat_id]['recipes']
        if 0 <= recipe_index < len(recipes):
            selected_recipe = recipes[recipe_index]
            bot.send_message(chat_id,
                             f"Рецепт 🧑🏻‍🍳 {selected_recipe[0]}:\n\n🥂Необходимые ингредиенты:\n{selected_recipe[1]}\n\n🍏Энергетическая ценность\n{selected_recipe[4]}\n\n🥄Рецепт приготовления:\n{selected_recipe[2]} 🍽")
            bot.send_photo(chat_id, selected_recipe[3])
        else:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "эй, введи правильную цифру, или переходи в меню😑")
        send_recipes(message.chat.id)


# Обрабатывает навигацию по списку рецептов.
# Показывает следующие или предыдущие 5 рецептов.
@bot.callback_query_handler(func=lambda call: call.data in ['more', 'back'])
def handle_pagination(call):
    chat_id = call.message.chat.id
    if call.data == 'more':
        user_data[chat_id]['current_index'] += 5
    elif call.data == 'back':
        user_data[chat_id]['current_index'] -= 5
    send_recipes(chat_id)

