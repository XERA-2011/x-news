import os
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from openai import OpenAI  # 可选

from dotenv import load_dotenv
load_dotenv()


# NewsAPI配置
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWS_SOURCES = 'bbc-news,reuters'
PAGE_SIZE = 5

# 邮件配置
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv('SMTP_PORT')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
TO_EMAIL = os.getenv('TO_EMAIL')

# OpenAI配置（可选）
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def get_news():
    """从NewsAPI获取新闻"""
    url = 'https://newsapi.org/v2/top-headlines'
    params = {
        'sources': NEWS_SOURCES,
        'pageSize': PAGE_SIZE,
        'apiKey': NEWS_API_KEY,
        'sortBy': 'publishedAt'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()['articles']
    except Exception as e:
        print(f"获取新闻失败: {str(e)}")
        raise

def generate_summary(text):  # 可选功能
    """使用OpenAI生成摘要"""
    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"请用中文生成一行新闻摘要（不超过30字）：{text[:1000]}"
            }]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成摘要失败: {str(e)}")
        return None

def create_email_content(articles):
    """生成HTML邮件内容"""
    html_content = """
    <html>
        <body>
            <h2>每日新闻摘要 ({date})</h2>
    """.format(date=datetime.now().strftime('%Y-%m-%d'))

    for article in articles:
        summary = generate_summary(article['content']) if OPENAI_API_KEY else article['description']
        html_content += f"""
            <div style="margin-bottom: 20px;">
                <h3><a href="{article['url']}">{article['title']}</a></h3>
                <p>{summary}</p>
                <small>来源：{article['source']['name']}</small>
            </div>
        """

    html_content += "</body></html>"
    return html_content

def send_email(content):
    """通过SMTP发送邮件"""
    msg = MIMEText(content, 'html')
    msg['Subject'] = f"每日新闻简报 {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_USER
    msg['To'] = TO_EMAIL

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        articles = get_news()
        email_content = create_email_content(articles)
        send_email(email_content)
    except Exception as e:
        print(f"执行失败: {str(e)}")
        raise SystemExit(1)