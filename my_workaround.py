import os
from telegram.ext import Updater
from dotenv import load_dotenv
from telegram.error import Unauthorized
from faunadb import query as q, errors
from app_config import client, users, logger

load_dotenv()

# setting up telegram stuff
updater = Updater(token=os.getenv('TELEGRAM_TOKEN'))


def send_broadcast(args):
    try:
        updater.bot.send_message(chat_id=args[0], text=args[1])
        return 'success'
    except Unauthorized:
        # user blocked bot so delete user from list
        user = client.query(
            q.get(q.ref(q.collection(users), args[0]))
        )
        client.query(
            q.delete(
                user['ref'],
            )
        )
        logger.write("a user has been deleted from user list")
        return ''
