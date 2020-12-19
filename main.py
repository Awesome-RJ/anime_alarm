import os
from scraping import get_anime, get_anime_episodes, get_anime_episode_download_link
from faunadb.client import FaunaClient
from faunadb import query as q
from faunadb.objects import Ref, FaunaTime
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext, Job, JobQueue
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import json
from pyshorteners import Shortener
import datetime
from custom_logging import Logger
from telegram.error import TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError
from multiprocessing import Pool
from threading import Thread
from typing import Union
from my_workaround import send_broadcast

load_dotenv()

# setting up telegram stuff
updater = Updater(token=os.getenv('TELEGRAM_TOKEN'))
dispatcher = updater.dispatcher
job_queue = updater.job_queue
shorten = Shortener().tinyurl.short

# setting up fauna stuff
client = FaunaClient(secret=os.getenv('FAUNA_SERVER_SECRET'))
users = 'users'
animes = 'animes'
all_users_by_anime = 'all_users_by_anime'
anime_by_title = 'all_animes_by_title'
sort_anime_by_followers = 'sort_animes_by_followers'

# setting up config file
config = {}
with open('config.json', 'r') as f:
    config = json.load(f)

# setting up custom logger
logger = Logger(config['app_log_path'])
def log_error(error: Exception):
    logger.write('An error occurred: '+str(error))

def is_admin(chat_id: Union[str, int]) -> bool:
    if str(chat_id) == str(os.getenv('ADMIN_CHAT_ID')):
        return True
    return False

def run_cron():
    def check_for_update(context: CallbackContext):
        context.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text='About to run subscription check!')
        #get all anime
        all_animes = client.query(
            q.map_(
                q.lambda_('doc_ref', q.get(q.var('doc_ref'))),
                q.paginate(q.documents(q.collection(animes)))
            )   
        )

        for anime in all_animes['data']:
            print(anime)
            episodes = get_anime_episodes(anime['data']['link'])
            print(len(episodes))
            #if there are new episodes...
            if len(episodes) > anime['data']['episodes']:
                if episodes[0] != anime['data']['last_episode']:
                    subscribed_users = client.query(
                        q.map_(
                            q.lambda_('doc_ref', q.get(q.var('doc_ref'))),
                            q.paginate(q.match(q.index(all_users_by_anime), anime['ref']))
                        )
                    )

                    client.query(
                        q.update(
                            anime['ref'],
                            {
                                'data':{
                                    'episodes': len(episodes),
                                    'last_episode': episodes[0]
                                }
                            }
                        )
                    )

                    subscribed_users = subscribed_users['data']

                    #get download link for new anime
                    
                    download_link = shorten(get_anime_episode_download_link(episodes[0]['link']))

                    markup = [[InlineKeyboardButton(text='Download', url=download_link)]]
                    #send message to subscribed users
                    print(subscribed_users)
                    for user in subscribed_users:
                        print('sent to subscribed user')
                        text = "Here's the latest episode for {0}:\n\n{1}".format(anime['data']['title'],episodes[0]['title'])
                        
                        context.bot.send_message(chat_id=int(user['ref'].id()), text=text, reply_markup=InlineKeyboardMarkup(markup))
                    #send message to admin
                    context.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text=anime['data']['title']+' just got a new episode and was updated!')
            else:
                pass

        context.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text='Subscription check finished!')

    time_to_run = datetime.datetime.strptime('19/12/20 06:20:00','%d/%m/%y %H:%M:%S')
    time_to_run.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=1)))
    try:
        # run job every 4 hours
        # this automatically runs in a separate thread so no wahala
        job_queue.run_repeating(check_for_update, interval=14400, first=time_to_run)
    except Exception as err:
        log_error(err)



def plain_message(update: Update, context:CallbackContext):
    print(update.effective_message)
    bot_user = client.query(q.get(q.ref(q.collection('users'), update.effective_chat.id)))
    chat_id = int(bot_user['ref'].id())
    last_command = bot_user['data']['last_command']
    message = update.message.text

    print(last_command)

    if last_command == 'watch':
        try: 
            search_results = get_anime(message, limit=15)

            if len(search_results) == 0:
                context.bot.send_message(chat_id=chat_id, text='Sorry but no search results were available for this anime')
            else:
                context.bot.send_message(chat_id=chat_id, text='Here are the search results for '+message)
                for result in search_results:
                    markup = [[InlineKeyboardButton('Select', callback_data='watch='+shorten(result['link']))]]
                    context.bot.send_photo(chat_id=chat_id, photo=result['thumbnail'], caption=result['title'], timeout=5, reply_markup=InlineKeyboardMarkup(markup))
                    
            #update last command
            client.query(
                q.update(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'last_command': '',
                        }
                    }
                )
            )        
        except Exception as err:
            log_error(err)
    elif last_command == 'getlatest':
        try: 
            search_results = get_anime(message, limit=15)

            if len(search_results) == 0:
                context.bot.send_message(chat_id=chat_id, text='Sorry but no search results were available for this anime')
            else:
                context.bot.send_message(chat_id=chat_id, text='Here are the search results for '+message)
                for result in search_results:
                    print(result['link'])

                    
                    markup = [[InlineKeyboardButton('Select', callback_data='getlatest='+shorten(result['link']))]]
                    context.bot.send_photo(chat_id=chat_id, photo=result['thumbnail'], caption=result['title'], timeout=5, reply_markup=InlineKeyboardMarkup(markup))
                    
            #update last command
            client.query(
                q.update(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'last_command': ''
                        }
                    }
                )
            )        
        except Exception as err:
            log_error(err)
    elif last_command == 'broadcast':
        if is_admin(chat_id):
            print('is_admin')
            context.bot.send_message(chat_id=chat_id, text='Broadcasting message...')
            try: 
                results = client.query(
                    q.paginate(q.documents(q.collection(users)))
                )
                results = results['data']
                print(results[0].id())

                #spin 5 processes
                with Pool(5) as p:
                    p.map(send_broadcast, [[int(user_ref.id()), message] for user_ref in results])

                client.query(
                    q.update(
                        q.ref(q.collection(users), chat_id),
                        {
                            'last_command': ''
                        }
                    )
                )
            except Exception as err:
                log_error(err)
        else:
            pass
    else:
        pass

def callback_handler_func(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    print(update)
    callback_message = update.callback_query.message.reply_markup.inline_keyboard[0][0].callback_data
    
    
    [command, payload] = callback_message.split(sep='=')

    if command == 'watch':
        try:
            title = update.callback_query.message.caption
            print(title)
            if title == None:
                title = '.'.join(update.effective_message.text.split(sep='.')[1:]).strip()
            
            #create a new anime document
            
            episodes = get_anime_episodes(payload)
            anime = client.query(
                q.create(
                    q.collection(animes),
                    {
                        'data': {
                            'title': title,
                            'followers': 0,
                            'link': payload,
                            'episodes': len(episodes),
                            'last_episode':episodes[0] ,
                        }
                    }
                )
            )

        except Exception as err:
            anime = client.query(  
                q.get(q.match(q.index(anime_by_title), title))
            )
            print(anime)        
        #update user's watch list
        try:
            result = client.query(
                q.let(
                    {
                        'user_anime_list': q.select(
                            ['data', 'animes_watching'],
                            q.get(q.ref(q.collection(users), chat_id))
                        ) 
                    },

                    q.if_(
                        q.contains_value(anime['ref'], q.var('user_anime_list')),
                        'This anime is already on your watch list!',
                        q.do(
                            q.update(
                                q.ref(q.collection(users), chat_id),
                                {
                                    'data': {
                                        'animes_watching': q.append(q.var('user_anime_list'), [anime['ref']])
                                    }
                                }
                            ),
                            q.update(
                                anime['ref'],
                                {
                                    'data': {
                                        'followers': q.add(
                                            q.select(['data', 'followers'], q.get(anime['ref'])),
                                            1
                                        )
                                    }
                                }
                            )
                        )
                        
                    )

                )
            )

            if type(result) is str:
                context.bot.send_message(chat_id=chat_id, text=result)
            else:
                context.bot.send_message(chat_id=chat_id, text='You are now listening for updates on '+title)
        except Exception as err:
            log_error(err)

    elif command == 'unwatch':
        try:
            client.query(
                q.let(
                    {
                        'anime_ref': q.ref(q.collection(animes), payload),
                        'bot_user': q.ref(q.collection(users), chat_id),
                        'followers': q.select(['data', 'followers'], q.get(q.var('anime_ref'))),
                        
                    },
                    q.do(
                        q.update(
                            q.var('anime_ref'),
                            {
                                'data':{
                                    'followers': q.subtract(
                                        q.var('followers'),
                                        1
                                    )
                                }
                            }
                        ),
                        q.update(
                            q.var('bot_user'),
                            {
                                'data': {
                                    'animes_watching': q.filter_(
                                        q.lambda_('watched_anime_ref', q.not_(q.equals(q.var('watched_anime_ref'), q.var('anime_ref')))),
                                        q.select(['data', 'animes_watching'], q.get(q.var('bot_user')))
                                    )
                                }
                            }
                        ),
                        q.if_(
                            q.equals(q.var('followers'), 1),
                            q.delete(q.var('anime_ref')),
                            'successful!'
                        )
                    )
                )
            )

            context.bot.send_message(chat_id=chat_id, text='You have stopped following '+update.callback_query.message.text)
        except Exception as err:
            log_error(err)

    elif command == 'getlatest':
        try:
            episodes = get_anime_episodes(payload)
            latest_episode_download_link = shorten(get_anime_episode_download_link(episodes[0]['link']))
            markup = [[InlineKeyboardButton(text='Download', url=latest_episode_download_link)]]
            context.bot.send_message(chat_id=chat_id, text=episodes[0]['title'], reply_markup=InlineKeyboardMarkup(markup))
        except Exception as err:
            log_error(err) 
    else:
        pass

def watch(update, context):
    chat_id = update.effective_chat.id

    try:
        client.query(
            q.if_(
                q.exists(q.ref(q.collection(users), chat_id)),
                q.update(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'last_command': 'watch'
                        }
                    }
                ),
                q.create(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'name': update.message.chat.first_name,
                            'is_admin': False,
                            'last_command': 'watch',
                            'animes_watching': []
                        }
                    }
                )
            )
        )
        
        context.bot.send_message(chat_id=chat_id, text= 'Enter the anime you want to get notifications for!')
    except Exception as err:
        log_error(err)

def unwatch(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    try:
        animes_watched = client.query(
            q.let(
                {
                    'bot_user': q.ref(q.collection(users), chat_id)
                },
                q.if_(
                    q.exists(q.var('bot_user')),
                    q.map_(
                        q.lambda_('doc_ref', q.get(q.var('doc_ref'))),
                        q.select(['data', 'animes_watching'], q.get(q.var('bot_user')))
                    ),
                    'You are currently not subscribed to any anime'
                )
            )
            
        )

        if type(animes_watched) is str:
            context.bot.send_message(chat_id=chat_id,text=animes_watched)
        
        else:
            for anime in animes_watched:
                markup = [[InlineKeyboardButton('Unwatch', callback_data='unwatch='+anime['ref'].id())]]
                context.bot.send_message(chat_id=chat_id, text=anime['data']['title'], reply_markup=InlineKeyboardMarkup(markup))

            #update last command
            client.query(
                q.update(
                    q.ref(q.collection(users), chat_id),
                    {
                        'data': {
                            'last_command': ''
                        }
                    }
                )
            ) 

        if animes_watched == []:
            context.bot.send_message(chat_id=chat_id,text='You are currently not subscribed to any anime')
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
                            'animes_watching': []
                        }
                    }
                )
            )
        )
        context.bot.send_message(chat_id=chat_id, text='Enter the anime you want to get!')
    except Exception as err:
        log_error(err)

def help(update, context):
    message = ''
    if is_admin:
        message = config['message']['help_admin']
    else:
        message = config['message']['help']
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    try:
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
    
def error_handler(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text='An error occurred. Check app log file')
    try:
        raise context.error
    except Unauthorized as err:
        # user has blocked bot
        # set user active status to false
        log_error(err)
        client.query(
            q.update(
                q.ref(q.collection(animes), update.effective_chat.id),
                {
                    'data': {
                        'active': False
                    }
                }
            )
        )
    except BadRequest as err:
        # handle malformed requests - read more below!
        log_error(err)
    except TimedOut:
        # handle slow connection problems
        log_error(err)
    except NetworkError:
        # handle other connection problems
        log_error(err)
    except ChatMigrated as err:
        # the chat_id of a group has changed, use e.new_chat_id instead
        log_error(err)
    except TelegramError:
        # handle all other telegram related errors
        log_error(err)

def recommend(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    results = client.query(
        q.map_(
            q.lambda_(['followers','doc_ref'], q.get(q.var('doc_ref'))),
            q.paginate(q.match(q.index(sort_anime_by_followers)),size=5)
        )
    )

    context.bot.send_message(chat_id=chat_id, text='Here are the top animes people using Anime Alarm are watching')

    for anime in results['data']:
        link = ''
        if anime['data']['link'].startswith('https://tinyurl.com/'):
            link = anime['data']['link']
        else:
            link = shorten(anime['data']['link'])
        markup = [[InlineKeyboardButton('Watch', callback_data='watch='+link)]]
        context.bot.send_message(chat_id=chat_id, reply_markup=InlineKeyboardMarkup(markup),text=str(results['data'].index(anime)+1)+'. '+anime['data']['title'])

def number_of_users(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if is_admin(chat_id):
        result = client.query(
            q.count(
                q.paginate(
                    q.documents(
                        q.collection(users)
                    )
                )
            )
        )
        context.bot.send_message(chat_id=chat_id, text='Number of users: '+str(result['data'][0]))

def number_of_anime(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if is_admin(chat_id):
        result = client.query(
            q.count(
                q.paginate(
                    q.documents(
                        q.collection(animes)
                    )
                ) 
            )
        )
        context.bot.send_message(chat_id=chat_id, text='Number of anime: '+str(result['data'][0]))

def broadcast(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if is_admin(chat_id):
        context.bot.send_message(chat_id=chat_id, text='Enter the message you want to broadcast')
        client.query(
            q.update(
                q.ref(q.collection(users), chat_id),
                {
                    'data':{
                        'last_command': 'broadcast'
                    }
                }
            )
        )
    else:
        context.bot.send_message(chat_id=chat_id, text='Only admins can use this command!')
    


watch_handler = CommandHandler('watch', watch)
unwatch_handler = CommandHandler('unwatch', unwatch)
help_handler = CommandHandler(['help', 'start'], help)
donate_handler = CommandHandler('donate', donate)
message_handler = MessageHandler(Filters.text & (~Filters.command), plain_message)
callback_handler = CallbackQueryHandler(callback_handler_func)
get_latest_handler = CommandHandler('latest', get_latest)
recommend_handler = CommandHandler('recommend', recommend)
users_handler = CommandHandler('usercount', number_of_users)
anime_handler = CommandHandler('animecount', number_of_anime)
broadcast_handler = CommandHandler('broadcast', broadcast)

dispatcher.add_handler(watch_handler)
dispatcher.add_handler(unwatch_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(donate_handler)
dispatcher.add_handler(message_handler)
dispatcher.add_handler(callback_handler)
dispatcher.add_handler(get_latest_handler)
dispatcher.add_handler(recommend_handler)
dispatcher.add_handler(users_handler)
dispatcher.add_handler(anime_handler)
dispatcher.add_handler(broadcast_handler)

dispatcher.add_error_handler(error_handler)



if __name__ == '__main__':
    updater.start_polling()
    run_cron()

#todo:
#Broadcast feature
#make broadcast and run_cron functions run on a separate thread



