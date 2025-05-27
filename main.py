import os
import sys
import logging
import smtplib
import requests
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime, timedelta
from openai import OpenAI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('main.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
from dotenv import load_dotenv
# 尝试加载.env文件，但不强制要求
load_dotenv()

# NewsAPI配置
class Config:
    NEWS_API_KEY: str = os.getenv('NEWS_API_KEY', '')
    NEWS_SOURCES: str = os.getenv('NEWS_SOURCES', '')
    PAGE_SIZE: int = int(os.getenv('PAGE_SIZE', '50'))
    NEWS_DAYS: int = int(os.getenv('NEWS_DAYS', '1'))

    # 邮件配置
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', '')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', 465))
    EMAIL_USER: str = os.getenv('EMAIL_USER', '')
    EMAIL_PASSWORD: str = os.getenv('EMAIL_PASSWORD', '')
    TO_EMAIL: str = os.getenv('TO_EMAIL', '')
    EMAIL_FROM_NAME: str = os.getenv('EMAIL_FROM_NAME', 'X-NEWS')  # 新增发件人显示名称配置

    # OpenAI配置
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')

    @classmethod
    def validate(cls) -> bool:
        """验证必要的配置是否存在"""
        required_fields = ['NEWS_API_KEY', 'SMTP_SERVER', 'EMAIL_USER', 'EMAIL_PASSWORD', 'TO_EMAIL']
        for field in required_fields:
            if not getattr(cls, field):
                logger.error(f"缺少必要的配置: {field}")
                return False
        return True

# OpenAI配置（可选）
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def get_news() -> List[Dict[str, Any]]:
    """从NewsAPI获取新闻"""
    url = 'https://newsapi.org/v2/top-headlines'
    # 设置时间范围
    days = Config.NEWS_DAYS
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    params = {
        'sources': Config.NEWS_SOURCES,  # top-headlines 只支持 sources 参数
        'pageSize': Config.PAGE_SIZE,
        'apiKey': Config.NEWS_API_KEY,
        'language': 'en',
        'from': from_date.strftime('%Y-%m-%d'),
        'to': to_date.strftime('%Y-%m-%d')
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        articles = response.json()['articles']
        logger.info(f"成功获取 {len(articles)} 条新闻，时间范围：{from_date.strftime('%Y-%m-%d')} 至 {to_date.strftime('%Y-%m-%d')}")
        return articles
    except requests.Timeout:
        logger.error("获取新闻超时")
        raise
    except requests.RequestException as e:
        logger.error(f"获取新闻失败: {str(e)}")
        raise

def generate_summary(text: str) -> Optional[str]:
    """使用OpenAI生成摘要"""
    if not Config.OPENAI_API_KEY:
        return None

    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"请用中文生成一行新闻摘要（不超过30字）：{text[:1000]}"
            }],
            temperature=0.7,
            max_tokens=60
        )
        summary = response.choices[0].message.content.strip()
        logger.debug(f"生成摘要: {summary}")
        return summary
    except Exception as e:
        logger.error(f"生成摘要失败: {str(e)}")
        return None

def create_email_content(articles: List[Dict[str, Any]]) -> str:
    """生成HTML邮件内容"""
    html_content = (
        f'<html>'
        f'<head>'
        f'<meta charset="UTF-8">'
        f'<style type="text/css">'
        f'.container {{ max-width: 800px; margin: 0 auto; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}'
        f'.title {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; text-align: center; }}'
        f'.article {{ background: #f9f9f9; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}'
        f'.article h3 {{ margin: 0 0 15px 0; font-size: 1.4em; }}'
        f'.article a {{ color: #3498db; text-decoration: none; }}'
        f'.article a:hover {{ text-decoration: underline; }}'
        f'.article-meta {{ display: flex; gap: 15px; margin-bottom: 15px; align-items: center; color: #7f8c8d; font-size: 0.9em; }}'
        f'.article-image {{ width: 100%; max-height: 300px; object-fit: cover; margin: 10px 0; border-radius: 5px; }}'
        f'.summary {{ color: #34495e; margin: 15px 0; line-height: 1.6; }}'
        f'.source {{ color: #7f8c8d; font-size: 0.9em; }}'
        f'</style>'
        f'</head>'
        f'<body>'
        f'<div class="container">'
        f'<h2 class="title">TOP{len(articles)} 新闻摘要</h2>'
    )

    for article in articles:
        # 处理发布时间
        published_at = datetime.fromisoformat(article.get('publishedAt', '').replace('Z', '+00:00'))
        formatted_date = published_at.strftime('%Y-%m-%d %H:%M')

        # 获取摘要
        summary = generate_summary(article.get('content', '')) or article.get('description', '暂无描述')

        # 构建文章HTML
        html_content += (
            f'<div class="article">'
            f'<h3><a href="{article["url"]}" target="_blank">{article["title"]}</a></h3>'
            f'<div class="article-meta">'
            f'<span>📅 {formatted_date}</span>'
        )

        if article.get('author'):
            html_content += f'<span>✍️ {article["author"]}</span>'

        html_content += f'<span>🗞️ {article["source"]["name"]}</span>'
        html_content += f'</div>'

        # 如果有图片则显示
        if article.get('urlToImage'):
            html_content += f'<img class="article-image" src="{article["urlToImage"]}" alt="{article["title"]}">'

        html_content += (
            f'<p class="summary">{summary}</p>'
            f'</div>'
        )

    html_content += '</div></body></html>'
    return html_content

def send_email(content: str) -> None:
    """通过SMTP发送邮件"""
    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = f"每日新闻简报 {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = formataddr((Config.EMAIL_FROM_NAME, Config.EMAIL_USER))  # 使用 formataddr 设置发件人
    msg['To'] = Config.TO_EMAIL

    try:
        with smtplib.SMTP_SSL(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10) as server:
            server.login(Config.EMAIL_USER, Config.EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info("邮件发送成功")
    except smtplib.SMTPException as e:
        logger.error(f"邮件发送失败: {str(e)}")
        raise

def main() -> None:
    """主函数"""
    try:
        if not Config.validate():
            raise SystemExit(1)

        articles = get_news()
        if not articles:
            logger.info("未获取到新闻，跳过发送邮件")
            return

        email_content = create_email_content(articles)
        send_email(email_content)
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()