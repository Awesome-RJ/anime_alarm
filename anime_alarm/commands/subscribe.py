from faunadb import query as q
from anime_alarm.utils.decorators import *
from app_registry import maintenance_message, log_error, client, users
from anime_alarm.enums import Resolution
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

__all__ = [
    'subscribe',
    'unsubscribe'
]


def subscribe(update, context):
    chat_id = update.effective_chat.id

    try:
        client.query(
            q.if_(
                q.exists(q.ref(q.collection(users), chat_id)),
                q.update(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'last_command': 'subscribe'
                        }
                    }
                ),
                q.create(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'name': update.message.chat.first_name,
                            'is_admin': False,
                            'last_command': 'subscribe',
                            'animes_watching': [],
                            'config': {
                                'resolution': Resolution.MEDIUM.value
                            }
                        }
                    }
                )
            )
        )

        context.bot.send_message(chat_id=chat_id, text='Enter the anime you want to get notifications for!')
    except Exception as err:
        log_error(err)


def unsubscribe(update: Update, context: CallbackContext):
    user = User(update.effective_chat.id)
    try:
        animes_watched = client.query(
            q.let(
                {
                    'bot_user': q.ref(q.collection(users), user.chat_id)
                },
                q.if_(
                    q.exists(q.var('bot_user')),
                    q.map_(
                        q.lambda_('doc_ref', q.get(q.var('doc_ref'))),
                        q.select(['data', 'animes_watching'], q.get(q.var('bot_user')))
                    ),
                    []
                )
            )

        )

        for anime in animes_watched:
            markup = [[InlineKeyboardButton('Unsubscribe', callback_data='unsubscribe=' + anime['ref'].id())]]
            context.bot.send_message(chat_id=user.chat_id, text=anime['data']['title'],
                                     reply_markup=InlineKeyboardMarkup(markup))

        # update last command
        user.last_command = ''

        if not animes_watched:
            context.bot.send_message(chat_id=user.chat_id, text='You are currently not subscribed to any anime')
    except Exception as err:
        log_error(err)
