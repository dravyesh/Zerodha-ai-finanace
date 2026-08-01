
import os
import requests
from dotenv import load_dotenv
load_dotenv()

API_key = os.getenv("News_API_key")

def get_stock_news(symbol):
    url = 'GET https://api.marketaux.com/v1/news/all'
    paramas = {'symbol': symbol,
              'conutries':'in',
              'language': 'en',
              'filter_entities':"true",
              'limit': 5,
              'api_token':API_key}
    try:
        response = requests.get(url,params=paramas)
        response.raise_for_status()
        data = response.json()
        articles = []
        for article in data.get("data",[]):
            articles.append({"Title": article.get("title"),
                            "Description": article.get("description"),
                            "source": article.get("source"),
                            "published":article.get("published_at"),
                            "url": article.get("url")})
            return articles
    except requests.exceptions.RequestException as e:
        print(f"api error: {e}")
    except Exception as e:
        print(f"unexpected error: {e}")
        return []