import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

load_dotenv()


def get_anime(anime:str, limit=10) -> list:
    anime = '+'.join(anime.split(sep=' '))
    URL = "https://kissanime.nz/Search/?s="+anime
    page = requests.get(URL)

    soup = BeautifulSoup(page.content, 'html.parser')

    results = soup.find(class_='listing')
    
    if results is None:
        return []

    anime_elems = results.find_all('div', class_='item_movies_in_cat', limit=limit)

    result_list = []
    for anime_elem in anime_elems:
        title_elem = anime_elem.find('a', class_='item_movies_link')
        #print(title_elem)
        title = title_elem.text
        
        link=title_elem["href"]
        thumbnail=anime_elem.find("a", class_="thumb_in_cat").find('img')['src']
        
        result_list.append({
            'title': title.strip(),
            'link': link.strip(),
            'thumbnail': thumbnail.strip()
        }) 

    return result_list


def get_anime_episodes(animelink,limit=None):
    page = requests.get(animelink)
    soup = BeautifulSoup(page.content, 'html.parser')

    results = soup.find('div', class_='listing')

    episode_elems = results.find_all('a',limit=limit)
    

    result_list = []
    for ep in episode_elems:
        result_list.append({
            'title': ep.text.strip(),
            'link': ep['href'].strip(),
        })

    return result_list

    


#print(get_anime('naruto shippuden')[0])
#a = get_anime_episodes('https://kissanime.nz/Anime/Naruto-Shippuuden.92501/')
#print(a[0])
#print(a[1])

def get_anime_episode_download_link(anime_link:str) -> str:
    cookies = {
        'uid': os.getenv('KA_UID'),
        'lcache': os.getenv('KA_LCACHE'),
        'uname': os.getenv('KA_USER_NAME'),
        'pwd': os.getenv('KA_PASSWORD'),
    }

    page = requests.get(anime_link,cookies=cookies)

    soup = BeautifulSoup(page.content, 'html.parser')

    try:

        result = soup.find(id='div_donoat_link')

        #get the link using beatiful soup


        durl = result.find('a')['href']
    except:
        raise Exception('This anime could not be downloaded')
    headers = {
        'scheme': 'https',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
        "Referer": anime_link, # "https://kissanime.nz/Anime/shingeki-no-kyojin-the-final-season.47665/Episode-060?id=166870",
        "Referrer-Policy": "unsafe-url",
        'authority': 'embed.streamx.me',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "accept-language": "en-US,en;q=0.9",
        'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
    }


    page = requests.get(durl,headers=headers, allow_redirects=False)
    download_link = page.headers['Location']
    return download_link





