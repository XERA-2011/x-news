# test_run.py
import os
from dotenv import load_dotenv

load_dotenv()

def test_newsapi():
    import requests
    response = requests.get(
        f"https://newsapi.org/v2/top-headlines?sources=bbc-news&apiKey={os.getenv('NEWS_API_KEY')}"
    )
    print(f"NewsAPI 响应状态码: {response.status_code}")
    print(f"获取到 {len(response.json()['articles'])} 条新闻")

def test_newsapi_sources():
    import requests
    response = requests.get(
        f"https://newsapi.org/v2/top-headlines/sources?apiKey={os.getenv('NEWS_API_KEY')}"
    )
    print(f"NewsAPI Sources 响应状态码: {response.status_code}")
    sources = response.json()['sources']
    print(f"获取到 {len(sources)} 个新闻源")
    print("\n可用的新闻源:")
    for source in sources:
        print(f"- {source['id']}: {source['name']} ({source['language']}/{source['country']})")

def test_smtp():
    import smtplib
    server = smtplib.SMTP_SSL(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
    server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASSWORD'))
    print("SMTP 登录成功")
    server.quit()

if __name__ == "__main__":
    test_newsapi()
    # test_newsapi_sources()
    test_smtp()