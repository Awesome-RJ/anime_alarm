import os
from app_registry import client, updater, animes, log_error, logger
from faunadb import query as q
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from dotenv import load_dotenv
import datetime
import sentry_sdk
from anime_alarm.commands import *

# set up sentry
sentry_sdk.init(
    "https://bc6863c9bd174d5a8cd5f95f6d45f4b0@o462758.ingest.sentry.io/5595618",
    traces_sample_rate=1.0
)

# load environment variables
load_dotenv()

# setting up telegram stuff
dispatcher = updater.dispatcher
job_queue = updater.job_queue


def run_cron():
    print('running')

    def check_for_update(context: CallbackContext):
        logger.info("About to run subscription check")
        # get all anime
        all_animes = client.query(
            q.paginate(q.documents(q.collection(animes)), size=100000)
        )

        for anime in all_animes['data']:
            # get anime_info in the function send_update...
            # if there are new episodes...
            send_update_to_subscribed_users(anime.id())

        logger.info("Subscription check finished")

    try:
        # run job every 2 hours
        # this automatically runs in a separate thread so no problem
        job_queue.run_repeating(check_for_update, interval=7200,
                                first=datetime.datetime.now() + datetime.timedelta(seconds=5))
    except Exception as err:
        log_error(err)


watch_handler = CommandHandler('subscribe', subscribe, run_async=True)
unwatch_handler = CommandHandler('unsubscribe', unsubscribe, run_async=True)
help_handler = CommandHandler(['help', 'start'], help_user, run_async=True)
donate_handler = CommandHandler('donate', donate, run_async=True)
message_handler = MessageHandler(Filters.text & (~Filters.command), plain_message, run_async=True)
callback_handler = CallbackQueryHandler(callback_handler_func, run_async=True)
get_latest_handler = CommandHandler('latest', get_latest, run_async=True)
recommend_handler = CommandHandler('recommend', recommend, run_async=True)
users_handler = CommandHandler('usercount', number_of_users, run_async=True)
anime_handler = CommandHandler('animecount', number_of_anime, run_async=True)
broadcast_handler = CommandHandler('broadcast', broadcast, run_async=True)
resolution_handler = CommandHandler('resolution', resolution, run_async=True)
app_log_handler = CommandHandler('log', app_log, run_async=True)

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
dispatcher.add_handler(app_log_handler)
dispatcher.add_handler(resolution_handler)
dispatcher.add_error_handler(error_handler)

if __name__ == '__main__':
    print('started')
    updater.start_webhook(
        listen='0.0.0.0',
        port=80,
        url_path=os.getenv('TELEGRAM_TOKEN'),
        webhook_url=os.getenv('TELEGRAM_BOT_URL') + os.getenv('TELEGRAM_TOKEN')
    )
    updater.bot.setWebhook(os.getenv('TELEGRAM_BOT_URL') + os.getenv('TELEGRAM_TOKEN'))
    run_cron()
