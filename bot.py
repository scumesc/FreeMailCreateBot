import json
import random
import string
import asyncio
import requests

from datetime import datetime
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from config import token

API = 'https://www.1secmail.com/api/v1/'
domain_list = ["1secmail.com", "1secmail.org", "1secmail.net"]

processed_messages = {}
user_mail_mapping = {}
user_data = {}

bot = Bot(token=token)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


def generate_username():
    name = string.ascii_lowercase + string.digits
    username = ''.join(random.choice(name) for i in range(10))
    return username



async def check_mail_and_send(mail, bot, chat_id):
    req_link = f'{API}?action=getMessages&login={mail.split("@")[0]}&domain={mail.split("@")[1]}'
    r = requests.get(req_link).json()
    length = len(r)

    if length == 0:
        await bot.send_message(chat_id, 'На почте пока нет новых сообщений.')
    else:
        id_list = []

        for i in r:
            for k, v in i.items():
                if k == 'id':
                    id_list.append(v)

        new_ids = []
        for i in id_list:
            if i not in processed_messages.get(mail, []):
                new_ids.append(i)
                processed_messages.setdefault(mail, []).append(i)

        for i in new_ids:
            read_msg = f'{API}?action=readMessage&login={mail.split("@")[0]}&domain={mail.split("@")[1]}&id={i}'
            r = requests.get(read_msg).json()

            sender = r.get('from')
            subject = r.get('subject')
            date = r.get('date')
            content = r.get('textBody')

            await bot.send_message(chat_id, f'📩 Новое сообщение:\n'
                                            f'От: {sender}\n\n'
                                            f'Тема: {subject}\n'
                                            f'Содержимое: {content}\n\n'
                                            f'Дата: {date}')


async def periodic_checking():
    while True:
        for chat_id, user_mail in user_mail_mapping.items():
            req_link = f'{API}?action=getMessages&login={user_mail.split("@")[0]}&domain={user_mail.split("@")[1]}'
            r = requests.get(req_link).json()
            length = len(r)

            if length > 0:
                asyncio.create_task(check_mail_and_send(user_mail, bot, chat_id))

        await asyncio.sleep(3)


async def delete_mail(mail, bot, chat_id):
    url = 'https://www.1secmail.com/mailbox'

    data = {
        'action': 'deleteMailbox',
        'login': mail.split('@')[0],
        'domain': mail.split('@')[1]
    }

    r = requests.post(url, data=data)
    await bot.send_message(chat_id, f'Почтовый адрес 📩\n'
                                    f'{mail}\n'
                                    f'Удален успешно ✅')



@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Заполняем данные пользователя
    user_data[user_id] = {
        'id': user_id,
        'first_name': first_name,
        'last_name': last_name,
        'timestamp': timestamp
    }


    with open('user_data.json', 'w') as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

    await message.answer(f'👋 Здравствуйте, {first_name}\n'
                         f'вы можете создать временную\n'
                         f'почту по команде\n\n'
                         f'/create создать почту 📩\n'
                         f'/delete удалить почту 📌'
                         )


@dp.message_handler(commands=['create'])
async def on_start(message: types.Message):
    username = generate_username()
    global user_mail_mapping
    user_mail_mapping[message.chat.id] = f'{username}@{random.choice(domain_list)}'
    await message.reply(f'📨 Ваш почтовый адрес:\n'
                        f'{user_mail_mapping[message.chat.id]}\n\n'
                        f'сообщение из почты\n'
                        f'придут вам автоматический\n\n'
                        f'/delete для удаления адреса.')



@dp.message_handler(commands=['delete'])
async def on_delete(message: types.Message):
    user_mail = user_mail_mapping.get(message.chat.id)
    if user_mail:
        await delete_mail(user_mail, bot, message.chat.id)
        del user_mail_mapping[message.chat.id]
    else:
        await bot.send_message(message.chat.id, 'Вы не создали почту. Используйте команду /create')





if __name__ == '__main__':
    asyncio.ensure_future(periodic_checking())
    executor.start_polling(dp, skip_updates=True)
