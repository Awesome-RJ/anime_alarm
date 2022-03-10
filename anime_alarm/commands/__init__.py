from faunadb import query as q, errors
from anime_alarm.utils import *
from anime_alarm.utils import shorten
from anime_alarm.enums import Resolution, resolutions
from anime_alarm.models import User
from anime_alarm.exceptions import CannotDownloadAnimeException
from app_registry import maintenance_message, log_error, client, users, logger, anime_by_id, \
    all_users_by_anime, animes, updater
from telegram.error import TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from multiprocessing import Pool
from anime_alarm.utils import send_broadcast
from anime_alarm.utils import GGAScraper
import os
from .subscribe import *
from .admin_commands import *
from .basic_commands import *
from typing import Union, Dict, Any

__all__ = [
    'error_handler',
    'send_update_to_subscribed_users',
    'plain_message',
    'callback_handler_func',
    'help_user',
    'donate',
    'get_latest',
    'recommend',
    'resolution',
    'subscribe',
    'unsubscribe',
    'number_of_users',
    'number_of_anime',
    'broadcast',
    'app_log'
]

# create a scraper
scraper = GGAScraper()


def get_subscribed_users_for_anime(anime_doc_id):
    """
    This function gets all the user subscribed to a particular anime
    """
    subscribed_users = client.query(
        q.map_(
            q.lambda_('doc_ref', q.get(q.var('doc_ref'))),
            q.paginate(q.match(q.index(all_users_by_anime), q.ref(q.collection(animes), str(anime_doc_id))),
                       size=100000)
        )
    )
    subscribed_users = subscribed_users['data']
    return subscribed_users


def send_update_to_subscribed_users(anime: Union[Dict[str, Any], str, int], download_links=None,
                                    anime_info: Dict = None):
    """
    This function sends updates to all users subscribed to a particular anime
    """

    # download_links is a dict of Resolution -> download_link
    if download_links is None:
        download_links = {}
    download_links = download_links
    if isinstance(anime, dict):
        pass
    elif isinstance(anime, (str, int)):
        anime = client.query(
            q.get(q.ref(q.collection(animes), str(anime)))
        )

    if anime_info is None:
        anime_info = scraper.get_anime_info(anime['data']['link'])

    # if there is a new episode...
    if (
        anime_info['number_of_episodes'] > anime['data']['episodes']
        and anime_info['latest_episode_link']
        != anime['data']['last_episode']['link']
    ):
        try:
            subscribed_users = get_subscribed_users_for_anime(anime['ref'].id())

            # send message to subscribed users
            for user in subscribed_users:
                try:
                    # if link for particular resolution has not been scraped yet...
                    user_resolution = Resolution(user['data']['config']['resolution'])
                    if user_resolution not in download_links:
                        download_links[user_resolution] = scraper.get_download_link(
                            anime_info['latest_episode_link'],
                            user_resolution)
                    markup = [[InlineKeyboardButton(text='Download', url=download_links[user_resolution])]]
                    text = "Here's the latest episode for {0}:\n\n{1}".format(anime['data']['title'],
                                                                                  anime_info['latest_episode_title'])
                    if anime['data']['anime_id'] == '9914':
                        text = "It's AOT Sunday!!\n\n"+text+"\n\nShinzou Wo Sasageyo!!"

                    updater.bot.send_message(chat_id=int(user['ref'].id()), text=text,
                                             reply_markup=InlineKeyboardMarkup(markup))

                except Unauthorized:
                    # user has blocked bot
                    # delete user from list
                    client.query(q.delete(user['ref']))
                    logger.info("A user has been deleted from user list")
            # send message to admin
            updater.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'),
                                     text=anime['data']['title'] + ' just got a new episode and was updated!')
            logger.info(
                str(len(subscribed_users)) + " users were notified of an update to " + anime['data']['title'])

        except CannotDownloadAnimeException as err:
            log_error(err)
            subscribed_users = get_subscribed_users_for_anime(anime['ref'].id())

            # tell subscribed user episode is available but can't download
            for user in subscribed_users:
                text = "A new episode for {0}: {1} is now out.\nSadly, I could not download it\U0001F622".format(
                    anime['data']['title'], anime_info['latest_episode_title'])
                updater.bot.send_message(chat_id=int(user['ref'].id()), text=text)
            # send message to admin
            updater.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text=anime['data'][
                                                                                  'title'] + ' just got a new '
                                                                                             'episode but could '
                                                                                             'not be downloaded')

        finally:
            # update anime in db after sending messages to users
            client.query(
                q.update(
                    anime['ref'],
                    {
                        'data': {
                            'episodes': anime_info['number_of_episodes'],
                            'last_episode': {
                                'title': anime_info['latest_episode_title'],
                                'link': anime_info['latest_episode_link']
                            }
                        }
                    }
                )
            )


def error_handler(update: Update, context: CallbackContext):
    try:
        raise context.error
    except BadRequest as err:
        # handle malformed requests
        log_error(err)
    except TimedOut as err:
        # handle slow connection problems
        log_error(err)
    except NetworkError as err:
        # handle other connection problems
        log_error(err)
    except ChatMigrated as err:
        # the chat_id of a group has changed, use e.new_chat_id instead
        log_error(err)
    except TelegramError as err:
        # handle all other telegram related errors
        log_error(err)
    except Exception as err:
        log_error(err)


def plain_message(update: Update, context: CallbackContext):
    print(update.effective_message)
    try:
        bot_user = client.query(q.get(q.ref(q.collection('users'), update.effective_chat.id)))
    except errors.NotFound:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Sorry, I do not understand what you mean.\nPlease use the /help command to '
                                      'discover what I can help you with.')
        return
    user = User(update.effective_chat.id)
    last_command = bot_user['data']['last_command']
    message = update.message.text

    print(last_command)

    if last_command == 'subscribe':
        try:
            search_results = scraper.get_anime(message, limit=15)
            if len(search_results) == 0:
                context.bot.send_message(chat_id=user.chat_id,
                                         text='Sorry but no search results were available for this anime')
            else:
                context.bot.send_message(chat_id=user.chat_id, text='Here are the search results for ' + message)
                for result in search_results:
                    markup = [[InlineKeyboardButton('Select', callback_data='subscribe=' + shorten(result['link']))]]
                    context.bot.send_photo(chat_id=user.chat_id, photo=result['thumbnail'], caption=result['title'],
                                           timeout=5, reply_markup=InlineKeyboardMarkup(markup))

            # update last command
            user.last_command = ''

        except Exception as err:
            log_error(err)

    elif last_command == 'getlatest':
        try:
            search_results = scraper.get_anime(message, limit=15)

            if len(search_results) == 0:
                context.bot.send_message(chat_id=user.chat_id,
                                         text='Sorry but no search results were available for this anime')
            else:
                context.bot.send_message(chat_id=user.chat_id, text='Here are the search results for ' + message)
                for result in search_results:
                    markup = [[InlineKeyboardButton('Select', callback_data='getlatest=' + shorten(result['link']))]]
                    context.bot.send_photo(chat_id=user.chat_id, photo=result['thumbnail'], caption=result['title'],
                                           timeout=5, reply_markup=InlineKeyboardMarkup(markup))
                    # update last command
            user.last_command = ''
        except Exception as err:
            log_error(err)

    elif last_command == 'broadcast':
        if user.is_admin():
            context.bot.send_message(chat_id=user.chat_id, text='Broadcasting message...')
            try:
                results = client.query(
                    q.paginate(q.documents(q.collection(users)), size=100000)
                )
                results = results['data']

                # spin 5 processes
                with Pool(5) as p:
                    res = p.map(send_broadcast, [[int(user_ref.id()), message] for user_ref in results])
                    successful_broadcast = [i for i in res if i == 'success']
                    logger.info('Message broadcast to ' + str(len(successful_broadcast)) + ' users')
                    print(res)
                # update user last command
                user.last_command = ''
            except Exception as err:
                log_error(err)
        else:
            context.bot.send_message(chat_id=user.chat_id, text="Only admins can use this command!")
    else:
        context.bot.send_message(chat_id=user.chat_id,
                                 text="Sorry, I do not understand what you mean.\nPlease use the /help command to "
                                      "discover what I can help you with.")


def callback_handler_func(update: Update, context: CallbackContext):
    user = User(update.effective_chat.id)
    callback_message = update.callback_query.message.reply_markup.inline_keyboard[0][0].callback_data

    [command, payload] = callback_message.split(sep='=')

    if command == 'subscribe':
        user.subscribe_to_anime(payload)
    elif command == 'unsubscribe':
        user.unsubscribe_from_anime(payload)
    elif command == 'getlatest':
        try:
            anime_info = scraper.get_anime_info(payload)

            latest_episode_download_link = shorten(scraper.get_download_link(anime_info['latest_episode_link'],
                                                                             resolution=user.resolution))
            markup = [[InlineKeyboardButton(text='Download', url=latest_episode_download_link)]]
            context.bot.send_message(chat_id=user.chat_id, text=anime_info['latest_episode_title'],
                                     reply_markup=InlineKeyboardMarkup(markup))
        except CannotDownloadAnimeException as err:
            log_error(err)
            context.bot.send_message(chat_id=user.chat_id, text="Sorry," + payload + "could not be downloaded at this "
                                                                                     "time!")
            context.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text='A user tried to download ' + payload +
                                                                              "but could not due to error: " + str(err))
            return
        except Exception as err:
            log_error(err)
            return
        else:
            # check if anime is in our anime registry
            try:
                anime_from_db = client.query(
                    q.if_(
                        q.exists(q.match(q.index(anime_by_id), anime_info['anime_id'])),
                        q.let(
                            {
                                'anime': q.get(q.match(q.index(anime_by_id), anime_info['anime_id']))
                            },
                            q.if_(
                                q.gt(anime_info['number_of_episodes'], q.select(['data', 'episodes'], q.var('anime'))),
                                q.var('anime'),
                                None
                            )
                        ),
                        None
                    )
                )
            except errors.NotFound:
                anime_from_db = None
            if anime_from_db is not None:
                send_update_to_subscribed_users(anime_from_db,
                                                download_links={user.resolution: latest_episode_download_link},
                                                anime_info=anime_info)
    elif command == 'set_resolution':
        try:
            new_res = Resolution(payload)
            user.resolution = new_res
            context.bot.send_message(chat_id=user.chat_id,
                                     text=f'Your desired resolution has been set to {new_res.value}({resolutions[new_res]}).\nThis resolution will be used for your future /subscribe and /latest commands.')
        except ValueError:
            context.bot.send_message(chat_id=user.chat_id, text='Unidentified resolution level!')
            context.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text='Unidentified resolution level!')
