from dotenv import load_dotenv
from telegram.ext import Updater
from faunadb.client import FaunaClient
from scraping import GGAScraper
from custom_logging import Logger
import os

load_dotenv()

config = {
    "message": {
        "help": "Hi, I'm Anime Alarm!\nI'm capable of bringing the latest anime episodes straight to your DMs for download and many more.\nHere's how to take advantage of my greatness:\n\n/subscribe - subscribe to any anime and get updates for new episodes\n/unsubscribe - stop receiving updates for an anime\n/latest - download the last episode of any anime instantly\n/help - get help and learn about Anime Alarm\n/donate - donate to help this project\n/recommend - get anime recommendations based on what other people using Anime Alarm are watching",
        "help_admin": "Hi, I'm Anime Alarm!\nI'm capable of bringing the latest anime episodes straight to your DMs for download and many more.\nHere's how to take advantage of my greatness:\n\n/subscribe - subscribe to any anime and get updates for new episodes\n/unsubscribe - stop receiving updates for an anime\n/latest - download the last episode of any anime instantly\n/help - get help and learn about Anime Alarm\n/donate - donate to help this project\n/recommend - get anime recommendations based on what other people using Anime Alarm are watching\n/usercount - get number of users\n/animecount - get number of anime\n/broadcast - broadcast messages to all users",
        "donate": [
            "You can donate in Bitcoin and Ethereum to help the development of this project.",
            "Bitcoin address:",
            "1LjtBTjaormXaUbARHWh97gJwBCQ8ioov",
            "Ethereum address:",
            "0xe57a812d0185eddffda0097b6d5ba38f240325fa"
        ]
    },
    "app_log_path": "./app.log"
}

client = FaunaClient(secret=os.getenv('FAUNA_SERVER_SECRET'))
updater = Updater(token=os.getenv('TELEGRAM_TOKEN'))

# setting up fauna stuff
users = 'users'
animes = 'animes'
all_users_by_anime = 'all_users_by_anime'
anime_by_title = 'all_animes_by_title'
sort_anime_by_followers = 'sort_animes_by_followers'
anime_by_id = 'all_anime_by_anime_id'

scraper = GGAScraper()

# setting up custom logger
logger = Logger(config['app_log_path'])

def log_error(error: Exception, log_to_admin_telegram=True):
    error_message = 'An error occurred: '+str(error)
    logger.write(error_message)
    if log_to_admin_telegram:
        updater.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text=error_message)
    else:
        pass


