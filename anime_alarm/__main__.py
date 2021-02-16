from app_registry import updater
from anime_alarm import run_cron
import os

if __name__ == '__main__':
    print('started')
    updater.start_webhook(
        listen='0.0.0.0',
        key='./private.key',
        cert='./cert.pem',
        url_path=os.getenv('TELEGRAM_TOKEN'),
        webhook_url=os.getenv('TELEGRAM_BOT_URL') + os.getenv('TELEGRAM_TOKEN')
    )
    # updater.bot.setWebhook(os.getenv('TELEGRAM_BOT_URL') + os.getenv('TELEGRAM_TOKEN'))
    run_cron()
