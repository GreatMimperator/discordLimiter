import asyncio
from datetime import datetime, timedelta
from string import Template

import discord
import configparser

# Чтение конфигурации
config = configparser.ConfigParser()
config.read('config.ini')

TOKEN = config['auth']['token']
USER_ID = None # определяется при старте
GUILD_NAMES = [name.strip() for name in config['auth']['guild_names'].split(',')]

# Чтение параметров из секции limits
MESSAGE_DELETE_INTERVAL_SIZE = int(config['limits']['message_delete_interval_size'])
MESSAGE_ALARM_INTERVAL_SIZE = int(config['limits']['message_alarm_interval_size'])
MESSAGE_INTERVAL_SIZE_DAYS = int(config['limits']['message_interval_size_days'])

STATUS_MESSAGE_LIFETIME_SECONDS = int(config['timing']['status_message_lifetime_seconds'])

alarm_text_template = (
    Template(
        f"Внимание! "
        f"Это $count-е сообщение. "
        f"Если количество сообщений достигнет {MESSAGE_DELETE_INTERVAL_SIZE}, они будут удалены."
    )
)
status_message_lifetime_template = (
    Template(f"У вас осталось $messages_left_count сообщений (интервал - {MESSAGE_INTERVAL_SIZE_DAYS} дней)")
)
NO_MESSAGES_LEFT_MESSAGE = f"У вас не осталось больше сообщений (интервал - {MESSAGE_INTERVAL_SIZE_DAYS} дней)"
limit_replacer_text = f"[Лимит сообщений превышен! (Максимум {MESSAGE_DELETE_INTERVAL_SIZE} сообщений)]"

client = discord.Client()

@client.event
async def on_ready():
    global USER_ID
    USER_ID = client.user.id
    print(f'Logged in as {client.user}')

message_write_time_list = []

@client.event
async def on_message(message):
    if message.author != client.user:
        return
    global message_write_time_list
    naive_created_at = message.created_at.replace(tzinfo=None)
    message_write_time_list.append(naive_created_at)

    # Ищем первое сообщение, которое старше недели
    cutoff_time = datetime.now() - timedelta(days=MESSAGE_INTERVAL_SIZE_DAYS)
    # Находим индекс первого сообщения, которое старше недели
    oldest_message_in_interval_index = 0
    while (oldest_message_in_interval_index < len(message_write_time_list)
           and message_write_time_list[oldest_message_in_interval_index] <= cutoff_time
    ):
        oldest_message_in_interval_index += 1
    # Обрезаем список от этого индекса
    message_write_time_list = message_write_time_list[oldest_message_in_interval_index:]

    message_count_before_the_message = len(message_write_time_list) - 1

    if message.content in ["статус", "status"]:
        if message_count_before_the_message < MESSAGE_DELETE_INTERVAL_SIZE:
            await message.edit(
                status_message_lifetime_template.substitute(
                    messages_left_count=MESSAGE_DELETE_INTERVAL_SIZE - message_count_before_the_message
                )
            )
        else:
            await message.edit(NO_MESSAGES_LEFT_MESSAGE)
        await asyncio.sleep(STATUS_MESSAGE_LIFETIME_SECONDS)
        message_write_time_list = message_write_time_list[:-1]
        await message.delete()
        return


    if len(message_write_time_list) > MESSAGE_DELETE_INTERVAL_SIZE:
        message_write_time_list = message_write_time_list[:-1]
        await message.edit(content=limit_replacer_text)
        return
    if len(message_write_time_list) % MESSAGE_ALARM_INTERVAL_SIZE == 0:
        new_content = message.content + f" \n\n{alarm_text_template.substitute(count=len(message_write_time_list))}"
        await message.edit(content=new_content)
        return

client.run(TOKEN)