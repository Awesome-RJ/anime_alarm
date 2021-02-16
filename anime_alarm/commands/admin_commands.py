from faunadb import query as q
from anime_alarm.utils.decorators import *
from app_registry import maintenance_message, client, log_file_path, users, animes
from telegram import Update


__all__ = [
    'number_of_users',
    'number_of_anime',
    'broadcast',
    'app_log'
]


# @mark_inactive(message=maintenance_message)
@admin_only
def number_of_users(update: Update, context: CallbackContext):
    user = User(update.effective_chat.id)
    result = client.query(
        q.count(
            q.paginate(
                q.documents(
                    q.collection(users)
                ),
                size=100000

            ),

        )
    )
    context.bot.send_message(chat_id=user.chat_id, text='Number of users: ' + str(result['data'][0]))


# @mark_inactive(message=maintenance_message)
@admin_only
def number_of_anime(update: Update, context: CallbackContext):
    result = client.query(
        q.count(
            q.paginate(
                q.documents(
                    q.collection(animes)
                ),
                size=100000
            )
        )
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text='Number of anime: ' + str(result['data'][0]))


@mark_inactive(message=maintenance_message)
@admin_only
def broadcast(update: Update, context: CallbackContext):
    user = User(update.effective_chat.id)
    context.bot.send_message(chat_id=user.chat_id, text='Enter the message you want to broadcast')
    user.last_command = 'broadcast'


# @mark_inactive(message=maintenance_message)
@admin_only
def app_log(update: Update, context: CallbackContext):
    user = User(update.effective_chat.id)
    with open(log_file_path, 'r') as f:
        logs = f.readlines()
        context.bot.send_message(chat_id=user.chat_id, text=''.join(logs[-5:]))
