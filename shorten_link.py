from pyshorteners import Shortener, exceptions
from dotenv import load_dotenv
import os

load_dotenv()

shortener = Shortener(api_key=os.getenv('BITLY_API_KEY'))

def shorten(link:str) -> str:
    shortened_link = ""
    if link.startswith('https://tinyurl.com/') or link.startswith('https://bit.ly/'):
        return link
    try:
        shortened_link = shortener.tinyurl.short(link)
    except exceptions.ShorteningErrorException:
        try:
            # shorten with bit.ly if tinyurl does not work
            shortened_link = shortener.bitly.short(link)
        except exceptions.BadAPIResponseException as err:
            raise Exception('This link cannot be shortened: '+str(err)) from err
        except exceptions.ShorteningErrorException as err:
            raise Exception('This link cannot be shortened: '+str(err)) from err
        else:
            return shortened_link
        
    except exceptions.BadAPIResponseException as err:
        raise Exception('This link cannot be shortened: '+str(err)) from err
    except exceptions.BadURLException as err:
        raise Exception('This link cannot be shortened: '+str(err)) from err
    else:
        return shortened_link
    


