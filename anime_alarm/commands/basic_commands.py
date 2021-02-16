from faunadb import query as q
from anime_alarm.utils.decorators import *
from anime_alarm.utils.shorten_link import shorten
from anime_alarm.enums import resolutions, Resolution
from app_registry import maintenance_message, log_error, client, config, users, sort_anime_by_followers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import os

__all__ = [
    'help_user',
    'donate',
    'get_latest',
    'recommend',
    'resolution'
]


def help_user(update, context):
    user = User(update.effective_chat.id)
    if str(user.chat_id) == str(os.getenv('ADMIN_CHAT_ID')):
        message = config['message']['help_admin']
    else:
        message = config['message']['help']
    context.bot.send_message(chat_id=user.chat_id, text=message)
    try:
        client.query(
            q.let(
                {
                    'user': q.ref(q.collection(users), user.chat_id)
                },
                q.if_(
                    q.exists(q.var('user')),
                    q.update(
                        q.var('user'),
                        {
                            'data': {
                                'last_command': '',
                            }
                        }
                    ),
                    'Success!'
                )
            )
        )
    except Exception as err:
        log_error(err)


def donate(update, context):
    try:
        for message in config['message']['donate']:
            context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        client.query(
            q.let(
                {
                    'user': q.ref(q.collection(users), update.effective_chat.id)
                },
                q.if_(
                    q.exists(q.var('user')),
                    q.update(
                        q.var('user'),
                        {
                            'data': {
                                'last_command': '',
                            }
                        }
                    ),
                    'Success!'
                )
            )
        )
    except Exception as err:
        log_error(err)


def get_latest(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    try:
        client.query(
            q.if_(
                q.exists(q.ref(q.collection(users), chat_id)),
                q.update(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'last_command': 'getlatest'
                        }
                    }
                ),
                q.create(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'name': update.message.chat.first_name,
                            'last_command': 'getlatest',
                            'animes_watching': [],
                            'config': {
                                'resolution': Resolution.MEDIUM.value
                            }
                        }
                    }
                )
            )
        )
        context.bot.send_message(chat_id=chat_id, text='Enter the anime you want to get!')
    except Exception as err:
        log_error(err)


def recommend(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    results = client.query(
        q.map_(
            q.lambda_(['followers', 'doc_ref'], q.get(q.var('doc_ref'))),
            q.paginate(q.match(q.index(sort_anime_by_followers)), size=5)
        )
    )

    context.bot.send_message(chat_id=chat_id, text='Here are the top animes people using Anime Alarm are watching')

    for anime in results['data']:
        if anime['data']['link'].startswith('https://tinyurl.com/') or anime['data']['link'].startswith(
                'https://bit.ly/'):
            link = anime['data']['link']
        else:
            link = shorten(anime['data']['link'])
        markup = [[InlineKeyboardButton('Subscribe', callback_data='subscribe=' + link)]]
        context.bot.send_message(chat_id=chat_id, reply_markup=InlineKeyboardMarkup(markup),
                                 text=str(results['data'].index(anime) + 1) + '. ' + anime['data']['title'])


def resolution(update: Update, context: CallbackContext):
    user = User(update.effective_chat.id)

    context.bot.send_message(chat_id=user.chat_id, text='Choose your desired resolution!')
    for res in resolutions:
        markup = [[InlineKeyboardButton(text='Select',
                                        callback_data='set_resolution=' + res.value)]]
        context.bot.send_message(text=str(res.value).capitalize() + ' - ' + resolutions[res], chat_id=user.chat_id,
                                 reply_markup=InlineKeyboardMarkup(markup))
