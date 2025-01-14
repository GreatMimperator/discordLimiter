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

alarm_text_template = (
    Template(
        f"Внимание! "
        f"Это $count-е сообщение. "
        f"Если количество сообщений достигнет {MESSAGE_DELETE_INTERVAL_SIZE}, они будут удалены."
    )
)
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

    if len(message_write_time_list) > MESSAGE_DELETE_INTERVAL_SIZE:
        await message.edit(content=limit_replacer_text)
        return
    if len(message_write_time_list) % MESSAGE_ALARM_INTERVAL_SIZE == 0:
        new_content = message.content + f" \n\n{alarm_text_template.substitute(count=len(message_write_time_list))}"
        await message.edit(content=new_content)
        return

client.run(TOKEN)