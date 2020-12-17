import os
from telegram.ext import Updater
from dotenv import load_dotenv


load_dotenv()

# setting up telegram stuff
updater = Updater(token=os.getenv('TELEGRAM_TOKEN'))

def send_broadcast(args):
    updater.dispatcher.bot.send_message(chat_id=args[0], text=args[1])