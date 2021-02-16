from dotenv import load_dotenv
from telegram.ext import Updater
from faunadb.client import FaunaClient
import logging
from sentry_sdk import capture_exception
import os

load_dotenv()

maintenance_message = 'Bot is currently undergoing maintenance and upgrades'

config = {
    "message": {
        "help": "Hi, I'm Anime Alarm!\nI'm capable of bringing the latest anime episodes straight to your DMs for "
                "download and many more.\nHere's how to take advantage of my greatness:\n\n/subscribe - subscribe to "
                "any anime and get updates for new episodes\n\n/unsubscribe - stop receiving updates for an "
                "anime\n\n/latest - download the last episode of any anime instantly\n\n/help - get help and learn about "
                "Anime Alarm\n\n/donate - donate to help this project\n\n/recommend - get anime recommendations based on "
                "what other people using Anime Alarm are watching\n\n/resolution - change the resolution of the animes "
                "that will be sent to you. This resolution will be applied for both the /subscribe and /latest "
                "commands",
        "help_admin": "Hi, I'm Anime Alarm!\nI'm capable of bringing the latest anime episodes straight to your DMs "
                      "for download and many more.\nHere's how to take advantage of my greatness:\n\n/subscribe - "
                      "subscribe to any anime and get updates for new episodes\n\n/unsubscribe - stop receiving updates "
                      "for an anime\n\n/latest - download the last episode of any anime instantly\n\n/help - get help and "
                      "learn about Anime Alarm\n\n/donate - donate to help this project\n\n/recommend - get anime "
                      "recommendations based on what other people using Anime Alarm are watching\n\n/usercount - get "
                      "number of users\n\n/animecount - get number of anime\n\n/broadcast - broadcast messages to all "
                      "users\n\n/log - read app logs\n\n/resolution - change the resolution of the animes "
                      "that will be sent to you. This resolution will be applied for both the /subscribe and /latest "
                      "commands",
        "donate": [
            "You can donate in Bitcoin and Ethereum to help the development of this project.",
            "Bitcoin address:",
            "1LjtBTjaormXaUbARHWh97gJwBCQ8ioov",
            "Ethereum address:",
            "0xe57a812d0185eddffda0097b6d5ba38f240325fa"
        ]
    },
}

client = FaunaClient(secret=os.getenv('FAUNA_SERVER_SECRET'))
updater = Updater(token=os.getenv('TELEGRAM_TOKEN'), use_context=True)

# setting up fauna stuff
users = 'users'
animes = 'animes'
all_users_by_anime = 'all_users_by_anime'
anime_by_title = 'all_animes_by_title'
sort_anime_by_followers = 'sort_animes_by_followers'
anime_by_id = 'all_anime_by_anime_id'

# scraper = GGAScraper()

# setting up custom logger

log_file_path = os.getenv('APP_LOG_PATH')

f_handler = logging.FileHandler(log_file_path, mode='a+')
f_format = logging.Formatter(
    '[%(asctime)s] (%(levelname)s)  - %(message)s',
    datefmt='%d-%B-%Y %H:%M:%S'
)
f_handler.setFormatter(f_format)
logger = logging.getLogger('anime_alarm_logger')
logger.addHandler(f_handler)
logger.setLevel(logging.DEBUG)


def log_error(error: Exception, log_to_admin_telegram=False) -> None:
    error_message = 'An error occurred: ' + str(error)
    capture_exception(error)
    logger.error(
        msg=error_message,
        exc_info=True
    )

    if log_to_admin_telegram is True:
        updater.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text=error_message)
    else:
        pass
