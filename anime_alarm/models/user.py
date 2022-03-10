"""
This module contains models for different entities in Anime Alarm
"""

from app_registry import updater, client, users, animes, anime_by_id, log_error, logger
from faunadb import query as q, errors
from anime_alarm.exceptions import UserNotFoundException
from anime_alarm.enums import Resolution
import anime_alarm.utils
import os

__all__ = [
    'User'
]


class User:
    def __init__(self, chat_id):
        self.chat_id = str(chat_id)

    def is_admin(self) -> bool:
        try:
            result = client.query(
                q.select(['data', 'is_admin'], q.get(q.ref(q.collection(users), self.chat_id)))
            )
        except errors.NotFound:
            raise UserNotFoundException(self.chat_id)
        return result

    def subscribe_to_anime(self, anime_link: str):
        try:
            # create a new anime document
            anime_info = anime_alarm.utils.GGAScraper().get_anime_info(anime_link)

            print(anime_info['anime_id'])

            result = client.query(
                q.let(
                    {
                        'user_anime_list': q.select(
                            ['data', 'animes_watching'],
                            q.get(q.ref(q.collection(users), self.chat_id))
                        ),
                    },
                    q.if_(
                        # check if this anime exists in the db
                        q.exists(q.match(q.index(anime_by_id), anime_info['anime_id'])),

                        # if it exists...
                        q.let(
                            {
                                'anime_ref': q.select('ref',
                                                      q.get(q.match(q.index(anime_by_id), anime_info['anime_id'])))
                            },
                            q.if_(
                                # check if user has subscribed to this anime already
                                q.contains_value(q.var('anime_ref'), q.var('user_anime_list')),
                                'This anime is already on your watch list!',
                                q.do(
                                    q.update(
                                        q.ref(q.collection(users), self.chat_id),
                                        {
                                            'data': {
                                                'animes_watching': q.append(q.var('user_anime_list'),
                                                                            [q.var('anime_ref')])
                                            }
                                        }
                                    ),
                                    q.update(
                                        q.var('anime_ref'),
                                        {
                                            'data': {
                                                'followers': q.add(
                                                    q.select(['data', 'followers'], q.get(q.var('anime_ref'))),
                                                    1
                                                )
                                            }
                                        }
                                    ),
                                )
                            )
                        ),
                        q.let(
                            {
                                'new_anime_id': q.new_id()
                            },
                            q.do(
                                # create new anime document
                                q.create(
                                    q.ref(q.collection(animes), q.var('new_anime_id')),
                                    {
                                        'data': {
                                            'title': anime_info['title'],
                                            'followers': 1,
                                            'link': anime_link,
                                            'anime_id': anime_info['anime_id'],
                                            'anime_alias': anime_info['anime_alias'],
                                            'episodes': anime_info['number_of_episodes'],
                                            'last_episode': {
                                                'link': anime_info['latest_episode_link'],
                                                'title': anime_info['latest_episode_title'],
                                            },
                                        }
                                    }
                                ),
                                # add to user's list of subscribed animes
                                q.update(
                                    q.ref(q.collection(users), self.chat_id),
                                    {
                                        'data': {
                                            'animes_watching': q.append(
                                                q.var('user_anime_list'),
                                                [q.ref(q.collection(animes), q.var('new_anime_id'))]
                                            )
                                        }
                                    }
                                ),
                            )
                        )
                    )
                )
            )

            if isinstance(result, str):
                updater.bot.send_message(chat_id=self.chat_id, text=result)
            else:
                updater.bot.send_message(chat_id=self.chat_id,
                                         text='You are now listening for updates on ' + anime_info['title'])
        except Exception as err:
            log_error(err)

    def unsubscribe_from_anime(self, anime_doc_id: str):
        try:
            anime = client.query(
                q.get(q.ref(q.collection(animes), anime_doc_id))
            )
            client.query(
                q.let(
                    {
                        'anime_ref': q.ref(q.collection(animes), anime_doc_id),
                        'bot_user': q.ref(q.collection(users), self.chat_id),
                        'followers': q.select(['data', 'followers'], q.get(q.var('anime_ref'))),

                    },
                    q.do(
                        q.update(
                            q.var('anime_ref'),
                            {
                                'data': {
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
                                        q.lambda_('watched_anime_ref',
                                                  q.not_(q.equals(q.var('watched_anime_ref'), q.var('anime_ref')))),
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

            updater.bot.send_message(chat_id=self.chat_id, text='You have stopped following ' + anime['data']['title'])
        except errors.NotFound:
            logger.info('Somehow, a user {0} almost unsubscribed from an anime that did not exist'.format(self.chat_id))
        except Exception as err:
            log_error(err)

    @property
    def last_command(self) -> str:
        return client.query(
            q.select(
                ['data', 'last_command'],
                q.get(q.ref(q.collection(users), self.chat_id)),
            )
        )

    @last_command.setter
    def last_command(self, new_last_command: str):
        client.query(
            q.update(
                q.ref(q.collection(users), self.chat_id),
                {
                    'data': {
                        'last_command': new_last_command
                    }
                }
            )
        )

    @property
    def resolution(self) -> Resolution:
        print('getting resolution')
        resolution = client.query(
            q.select(['data', 'config', 'resolution'], q.get(q.ref(q.collection(users), self.chat_id)))
        )
        return Resolution(resolution)

    @resolution.setter
    def resolution(self, resolution: Resolution):
        # update user's config in db
        client.query(
            q.update(
                q.ref(q.collection(users), self.chat_id),
                {
                    'data': {
                        'config': {
                            'resolution': resolution.value
                        }
                    }
                }
            )
        )


if __name__ == "__main__":
    user = User(os.getenv('ADMIN_CHAT_ID'))
    print(user.resolution)
    print(user.resolution)
