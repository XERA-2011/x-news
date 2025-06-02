import os
import sys
import logging
import smtplib
import requests
from typing import List, Dict, Any
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime
from translate import Translator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler('main.log', encoding='utf-8'), 暂时无需生成日志文件
        logging.StreamHandler(sys.stdout)
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

    @classmethod
    def validate(cls) -> bool:
        """验证必要的配置是否存在"""
        required_fields = ['NEWS_API_KEY', 'SMTP_SERVER', 'EMAIL_USER', 'EMAIL_PASSWORD', 'TO_EMAIL']
        for field in required_fields:
            if not getattr(cls, field):
                logger.error(f"缺少必要的配置: {field}")
                return False
        return True

def get_news() -> List[Dict[str, Any]]:
    """从NewsAPI获取新闻"""
    url = 'https://newsapi.org/v2/top-headlines'
    # url = 'https://newsapi.org/v2/everything'  # 使用 everything 以支持时间范围查询
    # 设置时间范围
    # days = Config.NEWS_DAYS
    # to_date = datetime.now()
    # from_date = to_date - timedelta(days=days)

    params = {
        'sources': Config.NEWS_SOURCES,  # top-headlines 只支持 sources 参数
        'pageSize': Config.PAGE_SIZE,
        'apiKey': Config.NEWS_API_KEY,
        'language': 'en',
        # 'from': from_date.strftime('%Y-%m-%d'),
        # 'to': to_date.strftime('%Y-%m-%d')
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        articles = response.json()['articles']
        logger.info(f"成功获取 {len(articles)} 条新闻")
        return articles
    except requests.Timeout:
        logger.error("获取新闻超时")
        raise
    except requests.RequestException as e:
        logger.error(f"获取新闻失败: {str(e)}")
        raise


def create_email_content(articles: List[Dict[str, Any]]) -> str:
    """生成HTML邮件内容"""
    # 收集所有不重复的新闻来源
    sources = sorted(set(article['source']['name'] for article in articles))
    sources_text = '、'.join(sources)

    html_content = (
        f'<html>'
        f'<head>'
        f'<meta charset="UTF-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<style type="text/css">'
        f'* {{ box-sizing: border-box; }}'
        f'body {{ margin: 0; padding: 15px; background: #f5f5f5; }}'
        f'.container {{ max-width: 800px; margin: 0 auto; padding: 15px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}'
        f'.title {{ color: #2c3e50; border-bottom: none; padding-bottom: 20px; text-align: center; font-size: 24px; margin: 0; }}'
        f'.sources-wrapper {{ width: 100%; text-align: right; margin: 0 0 8px; }}'
        f'.sources-tag {{ display: inline-flex; align-items: center; gap: 8px; color: #7f8c8d; font-size: 14px; padding: 6px 16px; background: rgba(127,140,141,0.1); border-radius: 20px; }}'
        f'.sources-tag::before {{ content: "📰"; }}'
        f'.article {{ background: #ffffff; padding: 20px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}'
        f'.article h3 {{ margin: 0 0 15px 0; font-size: 18px; line-height: 1.4; }}'
        f'.article a {{ color: #2980b9; text-decoration: none; display: block; }}'
        f'.article a:hover {{ color: #3498db; text-decoration: none; }}'
        f'.article-meta {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 15px; align-items: center; color: #7f8c8d; font-size: 14px; }}'
        f'.article-meta span {{ white-space: nowrap; }}'
        f'.article-image {{ width: 100%; height: auto; max-height: 300px; object-fit: cover; margin: 12px 0; border-radius: 8px; }}'
        f'.summary {{ margin: 15px 0; line-height: 1.6; font-size: 14px; }}'
        f'.source {{ color: #7f8c8d; font-size: 14px; }}'
        f'.text-group {{ color: #34495e; }}'
        f'.text-translated {{ margin-top: 8px; }}'
        f'.text-divider {{ border-left: 3px solid #e8e8e8; margin: 10px 0; padding-left: 10px; font-size: 14px; }}'
        f'@media (max-width: 600px) {{'
        f'  body {{ padding: 10px; }}'
        f'  .container {{ padding: 10px; }}'
        f'  .article {{ margin-bottom: 20px; }}'
        f'  .article-meta {{ margin-bottom: 12px; }}'
        f'}}'
        f'</style>'
        f'</head>'
        f'<body>'
        f'<div class="container">'
        f'<h2 class="title">TOP{len(articles)} 新闻摘要</h2>'
        f'<div class="sources-wrapper"><div class="sources-tag">来源：{sources_text}</div></div>'
    )

    for article in articles:
        # 处理发布时间
        published_at = datetime.fromisoformat(article.get('publishedAt', '').replace('Z', '+00:00'))
        formatted_date = published_at.strftime('%Y-%m-%d %H:%M')

        # 获取并翻译内容
        title = article['title']
        title_zh = translate_text(title)
        description = article.get('description', '暂无描述')
        description_zh = translate_text(description) if description != '暂无描述' else description

        # 构建文章HTML
        html_content += (
            f'<div class="article">'
            f'<h3>'
            f'<div class="text-group">'
            f'<a href="{article["url"]}" target="_blank">{title}</a>'  # 英文标题
            f'<a href="{article["url"]}" target="_blank" class="text-translated">{title_zh}</a>'  # 中文标题
            f'</div>'
            f'</h3>'
            f'<div class="article-meta">'
            f'<span>📅 {formatted_date}</span>'
        )

        if article.get('author'):
            html_content += f'<span>✍️ {article["author"]}</span>'

        html_content += f'<span>🗞️ {article["source"]["name"]}</span>'
        html_content += f'</div>'

        # 显示描述（中英文）
        if description:
            html_content += (
                f'<div class="text-divider text-group">'
                f'<p class="description">{description}</p>'  # 英文描述
                f'<p class="text-translated">{description_zh}</p>'  # 中文描述
                f'</div>'
            )

        # 如果有图片则显示
        if article.get('urlToImage'):
            html_content += f'<img class="article-image" src="{article["urlToImage"]}" alt="{title_zh}">'

        html_content += f'</div>'

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

def translate_text(text: str) -> str:
    """将英文文本翻译为中文"""
    if not text:
        return ""
    try:
        translator = Translator(to_lang='zh')
        result = translator.translate(text)
        return result
    except Exception as e:
        logger.warning(f"翻译失败: {str(e)}")
        return text  # 如果翻译失败，返回原文

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