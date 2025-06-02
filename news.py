import os
import sys
import logging
import smtplib
import requests
from typing import List, Dict, Any
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime
from ai import ask_ai

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 配置
class Config:
    # 邮件配置
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', '')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', 465))
    EMAIL_USER: str = os.getenv('EMAIL_USER', '')
    EMAIL_PASSWORD: str = os.getenv('EMAIL_PASSWORD', '')
    TO_EMAIL: str = os.getenv('TO_EMAIL', '')
    EMAIL_FROM_NAME: str = os.getenv('EMAIL_FROM_NAME', 'X-NEWS')
    
    @classmethod
    def validate(cls) -> bool:
        """验证必要的配置是否存在"""
        required_fields = ['SMTP_SERVER', 'EMAIL_USER', 'EMAIL_PASSWORD', 'TO_EMAIL']
        for field in required_fields:
            if not getattr(cls, field):
                logger.error(f"缺少必要的配置: {field}")
                return False
        return True

def get_news_content() -> str:
    """获取Reuters新闻页面内容"""
    url = 'https://www.reuters.com/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'DNT': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.Timeout:
        logger.error("获取新闻超时")
        raise
    except requests.RequestException as e:
        logger.error(f"获取新闻失败: {str(e)}")
        raise

def analyze_news_with_ai(html_content: str) -> List[Dict[str, Any]]:
    """使用AI分析新闻内容"""
    try:
        prompt = f"""请分析以下Reuters新闻页面的HTML内容，提取所有重要新闻。对于每条新闻，请提供：
1. 标题（英文原文和中文翻译）
2. 发布时间（如果有）
3. 简要描述（英文原文和中文翻译）
4. 新闻链接
5. 相关图片链接（如果有的话）
6. 主要事件概述（英文原文和中文翻译）
7. 关键人物和机构（英文原文和中文翻译）
8. 事件影响（英文原文和中文翻译）

请特别注意提取h2、h3标题下的重要新闻内容。请以JSON格式返回，格式如下：
[
    {{
        "title": {{
            "en": "英文标题",
            "zh": "中文标题"
        }},
        "publish_time": "发布时间（如果有）",
        "description": {{
            "en": "英文描述",
            "zh": "中文描述"
        }},
        "url": "新闻链接",
        "image_url": "图片链接（如果有）",
        "analysis": {{
            "overview": {{
                "en": "英文概述",
                "zh": "中文概述"
            }},
            "key_entities": {{
                "en": "英文关键人物和机构",
                "zh": "中文关键人物和机构"
            }},
            "impact": {{
                "en": "英文影响",
                "zh": "中文影响"
            }}
        }}
    }}
]

HTML内容：
{html_content}

请确保返回的是有效的JSON格式，并按照新闻重要性排序。每条新闻的JSON对象必须完整，不要截断。"""
        
        response = ask_ai(prompt)
        # 解析AI返回的JSON内容
        try:
            import json
            import re
            
            # 尝试提取JSON内容
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    articles = json.loads(json_str)
                    # 验证每个文章对象是否完整
                    valid_articles = []
                    for article in articles:
                        if all(key in article for key in ['title', 'description', 'url', 'analysis']):
                            valid_articles.append(article)
                        else:
                            logger.warning(f"跳过不完整的文章: {article.get('title', {}).get('en', 'Unknown')}")
                    
                    if valid_articles:
                        logger.info(f"成功分析 {len(valid_articles)} 条新闻")
                        return valid_articles
                    else:
                        logger.error("没有找到完整的新闻内容")
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {str(e)}")
                    # 尝试修复常见的JSON格式问题
                    try:
                        # 移除可能的尾随逗号
                        json_str = re.sub(r',\s*]', ']', json_str)
                        # 确保所有键都有引号
                        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
                        articles = json.loads(json_str)
                        logger.info(f"修复后成功解析 {len(articles)} 条新闻")
                        return articles
                    except:
                        logger.error("JSON修复失败")
                        return []
            else:
                logger.error("未在AI响应中找到有效的JSON内容")
                return []
        except Exception as e:
            logger.error(f"处理AI响应时出错: {str(e)}")
            return []
    except Exception as e:
        logger.error(f"AI分析失败: {str(e)}")
        return []

def create_email_content(articles: List[Dict[str, Any]]) -> str:
    """生成HTML邮件内容"""
    html_content = (
        f'<html>'
        f'<head>'
        f'<meta charset="UTF-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
        f'<style type="text/css">'
        f'* {{ box-sizing: border-box; }}'
        f'body {{ margin: 0; padding: 10px; background: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}'
        f'.container {{ max-width: 100%; margin: 0 auto; padding: 10px; }}'
        f'.title {{ color: #2c3e50; border-bottom: none; padding-bottom: 15px; text-align: center; font-size: 20px; margin: 0; }}'
        f'.article {{ background: #ffffff; padding: 15px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}'
        f'.article h3 {{ margin: 0 0 10px 0; font-size: 16px; line-height: 1.4; }}'
        f'.article a {{ color: #2980b9; text-decoration: none; display: block; word-break: break-all; }}'
        f'.article a:hover {{ color: #3498db; text-decoration: none; }}'
        f'.article-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; align-items: center; color: #7f8c8d; font-size: 13px; }}'
        f'.summary {{ margin: 10px 0; line-height: 1.5; font-size: 14px; }}'
        f'.ai-analysis {{ background: #f8f9fa; padding: 12px; border-radius: 8px; margin-top: 12px; }}'
        f'.ai-analysis h4 {{ margin: 0 0 8px 0; color: #2c3e50; font-size: 15px; }}'
        f'.ai-analysis p {{ margin: 6px 0; font-size: 13px; }}'
        f'.translation {{ color: #666; font-size: 13px; margin-top: 4px; }}'
        f'.news-image {{ width: 100%; max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}'
        f'.image-container {{ position: relative; width: 100%; margin: 10px 0; }}'
        f'.publish-time {{ color: #95a5a6; font-size: 12px; margin: 5px 0; }}'
        f'@media (max-width: 480px) {{'
        f'  .container {{ padding: 5px; }}'
        f'  .article {{ padding: 12px; margin-bottom: 15px; }}'
        f'  .article h3 {{ font-size: 15px; }}'
        f'  .summary {{ font-size: 13px; }}'
        f'  .ai-analysis {{ padding: 10px; }}'
        f'  .ai-analysis p {{ font-size: 12px; }}'
        f'  .news-image {{ margin: 8px 0; }}'
        f'}}'
        f'</style>'
        f'</head>'
        f'<body>'
        f'<div class="container">'
        f'<h2 class="title">Reuters 新闻分析</h2>'
    )

    for article in articles:
        html_content += (
            f'<div class="article">'
            f'<h3><a href="{article["url"]}" target="_blank">{article["title"]["en"]}</a></h3>'
            f'<div class="translation">{article["title"]["zh"]}</div>'
        )
        
        # 如果有发布时间，显示时间
        if article.get("publish_time"):
            html_content += f'<div class="publish-time">发布时间: {article["publish_time"]}</div>'
        
        # 如果有图片，添加图片
        if article.get("image_url"):
            html_content += (
                f'<div class="image-container">'
                f'<img src="{article["image_url"]}" alt="{article["title"]["en"]}" class="news-image" loading="lazy">'
                f'</div>'
            )
            
        html_content += (
            f'<div class="summary">{article["description"]["en"]}</div>'
            f'<div class="translation">{article["description"]["zh"]}</div>'
            f'<div class="ai-analysis">'
            f'<p><strong>主要事件：</strong>{article["analysis"]["overview"]["en"]}</p>'
            f'<div class="translation">{article["analysis"]["overview"]["zh"]}</div>'
            f'<p><strong>关键人物和机构：</strong>{article["analysis"]["key_entities"]["en"]}</p>'
            f'<div class="translation">{article["analysis"]["key_entities"]["zh"]}</div>'
            f'<p><strong>事件影响：</strong>{article["analysis"]["impact"]["en"]}</p>'
            f'<div class="translation">{article["analysis"]["impact"]["zh"]}</div>'
            f'</div>'
            f'</div>'
        )

    html_content += '</div></body></html>'
    return html_content

def send_email(content: str) -> None:
    """通过SMTP发送邮件"""
    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = f"Reuters新闻分析 {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = formataddr((Config.EMAIL_FROM_NAME, Config.EMAIL_USER))
    msg['To'] = Config.TO_EMAIL

    try:
        with smtplib.SMTP_SSL(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10) as server:
            server.login(Config.EMAIL_USER, Config.EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info("邮件发送成功")
    except smtplib.SMTPException as e:
        logger.error(f"邮件发送失败: {str(e)}")
        raise

def test_news_fetching() -> None:
    """测试获取新闻和分析功能"""
    try:
        if not Config.validate():
            raise SystemExit(1)

        # 获取新闻页面内容
        html_content = get_news_content()
        logger.info("成功获取新闻页面内容")
        
        # 使用AI分析新闻
        articles = analyze_news_with_ai(html_content)
        if not articles:
            logger.info("未获取到新闻")
            return

        # 打印分析结果
        logger.info(f"\n成功分析 {len(articles)} 条新闻:")
        for i, article in enumerate(articles, 1):
            logger.info(f"\n新闻 {i}:")
            logger.info(f"标题: {article['title']['en']}")
            logger.info(f"中文标题: {article['title']['zh']}")
            logger.info(f"英文描述: {article['description']['en']}")
            logger.info(f"中文描述: {article['description']['zh']}")
            logger.info(f"链接: {article['url']}")
            logger.info("AI分析:")
            logger.info(f"- 英文概述: {article['analysis']['overview']['en']}")
            logger.info(f"- 中文概述: {article['analysis']['overview']['zh']}")
            logger.info(f"- 英文关键人物和机构: {article['analysis']['key_entities']['en']}")
            logger.info(f"- 中文关键人物和机构: {article['analysis']['key_entities']['zh']}")
            logger.info(f"- 英文影响: {article['analysis']['impact']['en']}")
            logger.info(f"- 中文影响: {article['analysis']['impact']['zh']}")
            logger.info("-" * 80)

    except Exception as e:
        logger.error(f"测试执行失败: {str(e)}")
        raise SystemExit(1)

def main() -> None:
    """主函数"""
    try:
        if not Config.validate():
            raise SystemExit(1)

        # 获取新闻页面内容
        html_content = get_news_content()
        
        # 使用AI分析新闻
        articles = analyze_news_with_ai(html_content)
        if not articles:
            logger.info("未获取到新闻，跳过发送邮件")
            return

        # 生成邮件内容并发送
        email_content = create_email_content(articles)
        send_email(email_content)
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
    # test_news_fetching()