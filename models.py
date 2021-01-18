from app_config import updater, scraper, client, users, animes, anime_by_id, log_error, logger
from faunadb import query as q, errors
from custom_exceptions import UserNotFoundException

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

    
    def subscribe_to_anime(self, anime_link:str):
        try:
            #create a new anime document
            anime_info = scraper.get_anime_info(anime_link)
            anime = client.query(
                q.create(
                    q.collection(animes),
                    {
                        'data': {
                            'title': anime_info['title'],
                            'followers': 0,
                            'link': anime_link,
                            'anime_id': anime_info['anime_id'],
                            'anime_alias': anime_info['anime_alias'],
                            'episodes': anime_info['number_of_episodes'],
                            'last_episode':{
                                'link': anime_info['latest_episode_link'],
                                'title': anime_info['latest_episode_title'],
                            },
                        }
                    }
                )
            )

        except errors.BadRequest as err:
            if str(err) == "document is not unique.":
                anime = client.query(  
                    q.get(q.match(q.index(anime_by_id), anime_info['anime_id']))
                )
                print(anime) 

        #update user's watch list
        try:
            result = client.query(
                q.let(
                    {
                        'user_anime_list': q.select(
                            ['data', 'animes_watching'],
                            q.get(q.ref(q.collection(users), self.chat_id))
                        ) 
                    },

                    q.if_(
                        q.contains_value(anime['ref'], q.var('user_anime_list')),
                        'This anime is already on your watch list!',
                        q.do(
                            q.update(
                                q.ref(q.collection(users), self.chat_id),
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
                updater.bot.send_message(chat_id=self.chat_id, text=result)
            else:
                updater.bot.send_message(chat_id=self.chat_id, text='You are now listening for updates on '+anime['data']['title'])
        except Exception as err:
            log_error(err)


    def unsubscribe_from_anime(self, anime_doc_id:str):
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

            updater.bot.send_message(chat_id=self.chat_id, text='You have stopped following '+anime['data']['title'])
        except errors.NotFound:
            logger.write('Somehow, a user {0} almost unsubscribed from an anime that did not exist'.format(self.chat_id))
        except Exception as err:
            log_error(err)


    def update_last_command(self, new_last_command:str):
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



