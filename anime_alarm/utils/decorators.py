"""
This module contains decorators used throughout the anime alarm codebase
"""

from telegram import Update
from telegram.ext import CallbackContext
from anime_alarm.models import User
import functools


def admin_only(func):
    """
    This decorator wraps a telegram callback function and checks if the user is an admin
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for arg in args:
            if not isinstance(arg, Update):
                continue
            user = User(arg.effective_chat.id)
            if user.is_admin():
                func(*args, *kwargs)
            else:
                for arg2 in args:
                    if isinstance(arg2, CallbackContext):
                        arg2.bot.send_message(chat_id=user.chat_id, text='Only admins can use this command!')
                        break
            break
    return wrapper


def mark_inactive(message='This command has been disabled temporarily'):
    """
    This decorator marks a telegram callback function as inactive. Should only be used on telegram callback functions
    """
    def decorator_mark_inactive(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for arg in args:
                if not isinstance(arg, Update):
                    continue
                user = User(arg.effective_chat.id)
                for arg2 in args:
                    if isinstance(arg2, CallbackContext):
                        arg2.bot.send_message(chat_id=user.chat_id, text=message)
                        break
                break
        return wrapper
    return decorator_mark_inactive


