"""
This module is simple a workaround a 'bug' in the multiprocessing package
"""

from dotenv import load_dotenv
from telegram.error import Unauthorized
from faunadb import query as q, errors
from app_config import client, users, logger, log_error, updater


def send_broadcast(args):
    print(args)
    try:
        updater.bot.send_message(chat_id=args[0], text=args[1])
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
        logger.info("a user has been deleted from user list")
        return ''
    except Exception as err:
        log_error(err)
        return ''
    else:
        return 'success'
