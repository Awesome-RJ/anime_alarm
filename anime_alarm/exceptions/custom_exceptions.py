"""
This module contains custom exception classes that can be raised by Anime Alarm
"""

__all__ = [
    'CannotDownloadAnimeException',
    'CannotGetAnimeInfoException',
    'UserNotFoundException'
]

class CannotDownloadAnimeException(Exception):
    def __init__(self, anime, base_err: Exception):
        self.anime = anime
        self.base_err = base_err
        super().__init__(anime + ' could not be downloaded')

    def __str__(self):
        return self.anime + ' could not be downloaded: ' + str(self.base_err)


class CannotGetAnimeInfoException(Exception):
    def __init__(self, anime, base_err: Exception):
        self.anime = anime
        self.base_err = base_err
        super().__init__(anime + " info could not be retrieved")

    def __str__(self):
        return self.anime + " info could not be retrieved: " + str(self.base_err)


class UserNotFoundException(Exception):
    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        super().__init__('User with chat id,' + chat_id + ', was not found')
