"""
This module is where the scraping part of Anime Alarm is done
"""

import requests
from anime_alarm.custom_exceptions import CannotDownloadAnimeException, CannotGetAnimeInfoException
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from shorten_link import shorten

load_dotenv()

site_home_link = 'https://gogoanime.so'


class GGAScraper:
    def __init__(self):
        pass

    @staticmethod
    def get_anime(anime: str, limit=10) -> list:
        url = "https://gogoanime.so//search.html?keyword=" + anime
        page = requests.get(url)

        soup = BeautifulSoup(page.content, 'html.parser')

        results = soup.select('.last_episodes .items')[0]
        if results is None:
            return []

        anime_elems = results.find_all('li', limit=limit)

        result_list = []
        for anime_elem in anime_elems:
            title = anime_elem.find('p', class_="name").text
            link = "https://gogoanime.so" + anime_elem.find('a')["href"]
            thumbnail = anime_elem.find('img')['src']

            result_list.append({
                'title': title.strip(),
                'link': link.strip(),
                'thumbnail': thumbnail.strip()
            })

        return result_list

    @staticmethod
    def get_anime_info(animelink):
        page = requests.get(animelink)
        soup = BeautifulSoup(page.content, 'html.parser')

        try:
            anime_ep_info = soup.find('div', class_='anime_video_body').find_all('a')[-1:][0]
            ep_start = anime_ep_info['ep_start']
            last_episode = anime_ep_info['ep_end']

            anime_info_elem = soup.find('div', class_='anime_info_episodes_next')
            alias = anime_info_elem.find('input', id='alias_anime')['value']
            anime_id = anime_info_elem.find('input', id='movie_id')['value']
            title = soup.find('h1').text.strip()

            final_url = "https://ajax.gogocdn.net/ajax/load-list-episode?ep_start={0}&ep_end={1}&id={2}&default_ep=0&alias={3}".format(
                ep_start, last_episode, anime_id, alias)

            results = BeautifulSoup(requests.get(final_url).content, 'html.parser')
            episodes_elem = results.find('ul', id='episode_related')
            if episodes_elem is None:
                return {
                    'title': title,
                    'number_of_episodes': 0,
                    'anime_id': anime_id,
                    'anime_alias': alias,
                    'latest_episode_title': '',
                    'latest_episode_link': '',
                }
            else:
                latest_episode_elem = episodes_elem.find_all('li', limit=1)[0]
                link = site_home_link + (latest_episode_elem.find('a')['href']).strip()
        except Exception as err:
            raise CannotGetAnimeInfoException(animelink, err)
        return {
            'title': title,
            'number_of_episodes': int(last_episode),
            'anime_id': anime_id,
            'anime_alias': alias,
            'latest_episode_title': title + ' ' + latest_episode_elem.find('div', class_='name').text.strip(),
            'latest_episode_link': link,
        }

    @staticmethod
    def get_download_link(anime_download_page_link):
        try:
            download_page_soup = BeautifulSoup(requests.get(anime_download_page_link).content, 'html.parser')
            download_options_soup = BeautifulSoup(
                requests.get(download_page_soup.find('li', class_='dowloads').find('a')['href']).content, 'html.parser')

            download_link = shorten(download_options_soup.find_all('div', class_="dowload")[0].find('a')['href'])
        except Exception as err:
            raise CannotDownloadAnimeException(anime_download_page_link, err)

        return download_link


class KAScraper:
    """ Deprecated: do not use. Use GGAScraper instead"""

    def __init__(self):
        pass

    def get_anime(self, anime: str, limit=10) -> list:
        anime = '+'.join(anime.split(sep=' '))
        url = "https://kissanime.nz/Search/?s=" + anime
        page = requests.get(url)

        soup = BeautifulSoup(page.content, 'html.parser')

        results = soup.find(class_='listing')

        if results is None:
            return []

        anime_elems = results.find_all('div', class_='item_movies_in_cat', limit=limit)

        result_list = []
        for anime_elem in anime_elems:
            title_elem = anime_elem.find('a', class_='item_movies_link')
            title = title_elem.text

            link = title_elem["href"]
            thumbnail = anime_elem.find("a", class_="thumb_in_cat").find('img')['src']

            result_list.append({
                'title': title.strip(),
                'link': link.strip(),
                'thumbnail': thumbnail.strip()
            })

        return result_list

    def get_anime_episodes(self, animelink, limit=None):
        page = requests.get(animelink)
        soup = BeautifulSoup(page.content, 'html.parser')

        results = soup.find('div', class_='listing')

        episode_elems = results.find_all('a', limit=limit)

        result_list = []
        for ep in episode_elems:
            result_list.append({
                'title': ep.text.strip(),
                'link': ep['href'].strip(),
            })

        return result_list

    def get_anime_episode_download_link(self, anime_link: str) -> str:
        cookies = {
            'uid': os.getenv('KA_UID'),
            'lcache': os.getenv('KA_LCACHE'),
            'uname': os.getenv('KA_USER_NAME'),
            'pwd': os.getenv('KA_PASSWORD'),
        }

        page = requests.get(anime_link, cookies=cookies)

        soup = BeautifulSoup(page.content, 'html.parser')

        try:

            result = soup.find(id='div_donoat_link')

            # get the link using beautiful soup

            durl = result.find('a')['href']
        except Exception as err:
            raise CannotDownloadAnimeException(anime_link, err)
        headers = {
            'scheme': 'https',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/87.0.4280.88 Safari/537.36',
            "Referer": anime_link,
            # "https://kissanime.nz/Anime/shingeki-no-kyojin-the-final-season.47665/Episode-060?id=166870",
            "Referrer-Policy": "unsafe-url",
            'authority': 'embed.streamx.me',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "accept-language": "en-US,en;q=0.9",
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8,application/signed-exchange;v=b3;q=0.9 '
        }

        page = requests.get(durl, headers=headers, allow_redirects=False)
        download_link = page.headers['Location']
        return download_link
