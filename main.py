import os
import random
import telebot
from telebot import types
from dotenv import load_dotenv

from coffee_repository import CoffeeRepository
from coffees import coffees

load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

repo = CoffeeRepository()
repo.initialize()

def create_main_menu() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('📋 Меню')
    btn2 = types.KeyboardButton('🎲 Випадкова кава')
    btn3 = types.KeyboardButton('🛒 Кошик')
    btn4 = types.KeyboardButton('❌ Очистити кошик')
    markup.add(btn1, btn2, btn3, btn4)
    return markup

def create_coffee_list_markup(coffees) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for coffee in coffees:
        btn = types.InlineKeyboardButton(
            f"{coffee['name']} - ${coffee['price']:.2f}", 
            callback_data=f"coffee_{coffee['id']}"
        )
        markup.add(btn)
    return markup

def create_coffee_detail_markup(coffee_id) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("Додати в кошик", callback_data=f"add_{coffee_id}_1")
    btn3 = types.InlineKeyboardButton("Додати 3 в кошик", callback_data=f"add_{coffee_id}_3")
    markup.add(btn1, btn3)
    
    return markup

def format_coffee_details(coffee) -> str:
    return f"*{coffee['name']}*\n\n{coffee['description']}\n\n*Ціна:* ${coffee['price']:.2f}"

def format_cart_item(item) -> str:
    return f"• {item['name']} - {item['count']} x ${item['price']:.2f} = ${item['total_price']:.2f}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Ласкаво просимо до Coffee Shop Bot!\n\n"
        "Ось що ви можете зробити:\n"
        "📋 Перегляньте наш вибір кави\n"
        "🎲 Отримайте випадкову рекомендацію кави\n"
        "🛒 Переглянути кошик\n"
        "❌ Очистіть кошик\n\n"
        "Використовуйте кнопки нижче для навігації."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_menu())

@bot.message_handler(func=lambda message: message.text == '📋 Меню')
def list_coffees(message):
    coffees = repo.list_coffee()
    if not coffees:
        bot.send_message(message.chat.id, "На жаль у нас зараз немає жодної кави")
        return
    
    bot.send_message(
        message.chat.id, 
        "Наше меню кави (настиність, щоб отримати більше інформації):",
        reply_markup=create_coffee_list_markup(coffees)
    )

@bot.message_handler(func=lambda message: message.text == '🎲 Випадкова кава')
def recommend_coffee(message):
    coffees = repo.list_coffee()
    if not coffees:
        bot.send_message(message.chat.id, "На жаль, у нас зараз немає жодної кави")
        return
    
    coffee = random.choice(coffees)

    show_coffee_details(message.chat.id, coffee["id"])

@bot.message_handler(func=lambda message: message.text == '🛒 Кошик')
def view_cart(message):
    user_id = message.from_user.id
    cart_items = repo.get_cart_items(user_id)
    
    if not cart_items:
        bot.send_message(message.chat.id, "Ваш кошик порожній")
        return
    
    cart_text = "🛒 *Ваш кошик*\n\n"
    total_price = 0
    
    for item in cart_items:
        cart_text += format_cart_item(item) + "\n"
        total_price += item['total_price']
    
    cart_text += f"\n*Усього: ${total_price:.2f}*"
    
    markup = types.InlineKeyboardMarkup()
    checkout_btn = types.InlineKeyboardButton("Оформити замовлення", callback_data="checkout")
    markup.add(checkout_btn)
    
    bot.send_message(message.chat.id, cart_text, reply_markup=markup, parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text == '❌ Очистити кошик')
def clear_cart(message):
    user_id = message.from_user.id
    repo.clear_cart(user_id)
    bot.send_message(message.chat.id, "Кошик очищено")

@bot.callback_query_handler(func=lambda call: call.data == "list_coffee")
def callback_list_coffee(call):
    coffees = repo.list_coffee()
    if not coffees:
        bot.edit_message_text(
            "На жаль у нас зараз намає кави", 
            call.message.chat.id, 
            call.message.message_id
        )
        return
    
    bot.edit_message_text(
        call.message.chat.id, 
        call.message.message_id,
        reply_markup=create_coffee_list_markup(coffees)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("coffee_"))
def callback_coffee_details(call):
    coffee_id = int(call.data.split('_')[1])
    show_coffee_details(call.message.chat.id, coffee_id, call.message.message_id)



@bot.callback_query_handler(func=lambda call: call.data.startswith("add_"))
def callback_add_to_cart(call):
    parts = call.data.split('_')
    coffee_id = int(parts[1])
    count = int(parts[2])
    user_id = call.from_user.id
    
    success = repo.add_to_cart(user_id, coffee_id, count)
    
    if success:
        coffee_name = repo.list_coffee(coffee_id)[0]["name"]
        bot.answer_callback_query(call.id, f"Додано {count} {coffee_name} до кошика!")
    else:
        bot.answer_callback_query(call.id, "Виникла помилка, спробуйте будь-ласка пізніше")

@bot.callback_query_handler(func=lambda call: call.data == "checkout")
def callback_checkout(call):
    repo.clear_cart()
    bot.edit_message_text(
        "Наш менеджер зв'яжеться з вами для оформлення замовлення",
        call.message.chat.id,
        call.message.message_id
    )

def show_coffee_details(chat_id, coffee_id, message_id=None):
    coffees = repo.list_coffee(coffee_id)
    if not coffees:
        text = "Кава не знайдена!"
        bot.send_message(chat_id, text)
        return
    
    coffee = coffees[0]
    
    text = format_coffee_details(coffee)
    markup = create_coffee_detail_markup(coffee_id)
    
    if coffee['picture_url'] and coffee['picture_url'].strip():
        bot.send_photo(
            chat_id,
            coffee['picture_url'],
            caption=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id,
            text,
            reply_markup=markup,
            parse_mode="Markdown"
        )

if __name__ == "__main__":
    print("Starting Coffee Shop Bot...")
    try:
        if not repo.list_coffee():
            for coffee in coffees:
                coffee_id = repo.add_coffee(
                    name=coffee["name"],
                    description=coffee["description"],
                    picture_url=coffee["picture_url"],
                    price=coffee["price"]
                )
            print("Added sample coffees to the database.")
            
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error: {e}")