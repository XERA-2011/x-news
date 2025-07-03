import logging
import os
import re
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Dict, List

# 将项目根目录添加到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import pytz
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from utils.ai import ask_ai

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
        html = response.text
        # 优化：先提取 <main> 标签，再在 <main> 内查找 <section>
        soup = BeautifulSoup(html, 'html.parser')
        main_tag = soup.find('main')
        if main_tag:
            section_tags = main_tag.find_all('section')
            if section_tags:
                section_html = "".join(str(tag) for tag in section_tags[:5])
            else:
                section_html = str(main_tag)
        else:
            # 降级为 <body> 或全文
            body_tag = soup.find('body')
            section_html = str(body_tag) if body_tag else html
        return section_html
    except requests.Timeout:
        logger.error("获取新闻超时")
        raise
    except requests.RequestException as e:
        logger.error(f"获取新闻失败: {str(e)}")
        raise

def analyze_news_with_ai(html_content: str) -> List[Dict[str, Any]]:
    """使用AI分析新闻内容，返回前10条最重要的新闻"""
    try:
        prompt = f"""请分析以下Reuters新闻页面的HTML内容，提取最重要的前10条新闻。请按重要性排序，对于每条新闻，请提供：
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
        
        # 新增：防止 response 为 None、非字符串或空字符串
        if not isinstance(response, str) or not response.strip():
            logger.error(f"AI返回结果无效（None、非字符串或空字符串），实际返回: {repr(response)}")
            # 返回一条伪新闻，提示AI异常
            return [{
                "title": {"en": "AI analysis failed", "zh": "AI分析失败，部分新闻内容无法获取"},
                "publish_time": "",
                "description": {"en": "AI service did not return valid news. Please try again later.", "zh": "AI服务未返回有效新闻，请稍后重试。"},
                "url": "https://www.reuters.com/",
                "image_url": "",
                "analysis": {
                    "overview": {"en": "AI error or overload.", "zh": "AI接口异常或过载。"},
                    "key_entities": {"en": "", "zh": ""},
                    "impact": {"en": "No news available.", "zh": "暂无新闻内容。"}
                }
            }]
        # 检查AI返回内容是否包含503、overload、error等异常
        error_keywords = ["503", "overload", "error", "failed", "unavailable"]
        if any(kw in response.lower() for kw in error_keywords):
            logger.error(f"AI返回内容包含错误信息: {response}")
            return [{
                "title": {"en": "AI analysis failed", "zh": "AI分析失败，部分新闻内容无法获取"},
                "publish_time": "",
                "description": {"en": "AI service error or overload. Please try again later.", "zh": "AI服务异常或过载，请稍后重试。"},
                "url": "https://www.reuters.com/",
                "image_url": "",
                "analysis": {
                    "overview": {"en": "AI error or overload.", "zh": "AI接口异常或过载。"},
                    "key_entities": {"en": "", "zh": ""},
                    "impact": {"en": "No news available.", "zh": "暂无新闻内容。"}
                }
            }]
        # 解析新闻内容
        try:
            import json
            import re
            # 提取新闻内容
            news_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
            if not news_match:
                logger.error(f"未找到新闻内容，AI原始返回: {response}")
                return [{
                    "title": {"en": "AI analysis failed", "zh": "AI分析失败，部分新闻内容无法获取"},
                    "publish_time": "",
                    "description": {"en": "AI did not return valid news JSON. Please try again later.", "zh": "AI未返回有效新闻JSON，请稍后重试。"},
                    "url": "https://www.reuters.com/",
                    "image_url": "",
                    "analysis": {
                        "overview": {"en": "AI response format error.", "zh": "AI响应格式错误。"},
                        "key_entities": {"en": "", "zh": ""},
                        "impact": {"en": "No news available.", "zh": "暂无新闻内容。"}
                    }
                }]
            json_str = news_match.group(0)
            try:
                # 尝试修复常见的JSON格式问题
                json_str = re.sub(r',\s*]', ']', json_str)
                json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
                if not json_str.endswith(']'):
                    json_str = json_str + ']'
                articles = json.loads(json_str)
                # 验证每个文章对象是否完整
                valid_articles = []
                for article in articles:
                    if all(key in article for key in ['title', 'description', 'url', 'analysis']):
                        if (all(key in article['title'] for key in ['en', 'zh']) and
                            all(key in article['description'] for key in ['en', 'zh']) and
                            all(key in article['analysis'] for key in ['overview', 'key_entities', 'impact']) and
                            all(key in article['analysis']['overview'] for key in ['en', 'zh']) and
                            all(key in article['analysis']['key_entities'] for key in ['en', 'zh']) and
                            all(key in article['analysis']['impact'] for key in ['en', 'zh'])):
                            valid_articles.append(article)
                        else:
                            logger.warning(f"跳过不完整的文章: {article.get('title', {}).get('en', 'Unknown')}")
                    else:
                        logger.warning(f"跳过缺少必需字段的文章: {article.get('title', {}).get('en', 'Unknown')}")
                if valid_articles:
                    logger.info(f"成功分析 {len(valid_articles)} 条新闻")
                    return valid_articles
                else:
                    logger.error(f"没有找到完整的新闻内容，AI原始返回: {response}")
                    return [{
                        "title": {"en": "AI analysis failed", "zh": "AI分析失败，部分新闻内容无法获取"},
                        "publish_time": "",
                        "description": {"en": "AI did not return valid news. Please try again later.", "zh": "AI未返回有效新闻，请稍后重试。"},
                        "url": "https://www.reuters.com/",
                        "image_url": "",
                        "analysis": {
                            "overview": {"en": "AI returned no valid news.", "zh": "AI未返回有效新闻。"},
                            "key_entities": {"en": "", "zh": ""},
                            "impact": {"en": "No news available.", "zh": "暂无新闻内容。"}
                        }
                    }]
            except json.JSONDecodeError as e:
                logger.error(f"新闻JSON解析失败: {str(e)}，原始JSON字符串: {json_str}")
                return [{
                    "title": {"en": "AI analysis failed", "zh": "AI分析失败，部分新闻内容无法获取"},
                    "publish_time": "",
                    "description": {"en": "AI returned invalid JSON. Please try again later.", "zh": "AI返回了无效的JSON，请稍后重试。"},
                    "url": "https://www.reuters.com/",
                    "image_url": "",
                    "analysis": {
                        "overview": {"en": "AI JSON decode error.", "zh": "AI JSON解析错误。"},
                        "key_entities": {"en": "", "zh": ""},
                        "impact": {"en": "No news available.", "zh": "暂无新闻内容。"}
                    }
                }]
        except Exception as e:
            logger.error(f"处理新闻响应时出错: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"AI分析失败: {str(e)}")
        return []

def format_publish_time(time_str: Any) -> str:
    if not time_str or not isinstance(time_str, str):
        return "N/A"

    target_format = "%Y-%m-%d %H:%M"
    
    # 1. 处理 UTC 时间格式 (如 "3:16 AM UTC")
    try:
        utc_pattern = r"(\d{1,2}):(\d{2})\s*(AM|PM)\s*UTC"
        utc_match = re.match(utc_pattern, time_str)
        if utc_match:
            hour, minute, meridiem = utc_match.groups()
            hour = int(hour)
            # 转换12小时制到24小时制
            if meridiem.upper() == "PM" and hour < 12:
                hour += 12
            elif meridiem.upper() == "AM" and hour == 12:
                hour = 0
                
            # 创建今天的UTC时间
            today = datetime.now().date()
            utc_time = datetime(today.year, today.month, today.day, hour, int(minute))
            
            # 使用 pytz 转换UTC时间到本地时间
            utc = pytz.UTC
            local_tz = pytz.timezone('Asia/Shanghai')  # 使用中国时区
            utc_time = utc.localize(utc_time)
            local_time = utc_time.astimezone(local_tz)
            return local_time.strftime(target_format)
    except ValueError:
        pass

    # 2. 处理英文月份日期格式 (如 "June 4, 2025")
    try:
        english_date_pattern = r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})"
        match = re.match(english_date_pattern, time_str)
        if match:
            month, day, year = match.groups()
            dt_obj = datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
            return dt_obj.strftime("%Y-%m-%d 00:00")
    except ValueError:
        pass

    # 3. Try parsing ISO 8601 formats (most common in APIs and modern systems)
    try:
        parsable_str = time_str
        # Handle cases where space is used instead of 'T' in ISO-like dates
        if 'T' not in parsable_str and ' ' in parsable_str:
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[\+\-]\d{2}:?\d{2})?$", parsable_str):
                parsable_str = parsable_str.replace(' ', 'T', 1)
        
        if 'Z' in parsable_str or '+' in parsable_str or (len(parsable_str) > 10 and '-' in parsable_str[10:] and parsable_str.count(':') >= 2):
            dt_obj = datetime.fromisoformat(parsable_str.replace('Z', '+00:00'))
            return dt_obj.strftime(target_format)
    except ValueError:
        pass

    # 4. Try parsing "ago" relative time strings
    ago_match = re.match(r"(\d+)\s+(minute|min|hour|hr|day)s?\s+ago", time_str, re.IGNORECASE)
    if ago_match:
        value = int(ago_match.group(1))
        unit_keyword = ago_match.group(2).lower()
        now = datetime.now()

        if unit_keyword.startswith("min"):
            delta = timedelta(minutes=value)
        elif unit_keyword.startswith("h"):
            delta = timedelta(hours=value)
        elif unit_keyword.startswith("day"):
            delta = timedelta(days=value)
        else: 
            return time_str

        publish_dt = now - delta
        return publish_dt.strftime(target_format)

    # 5. Try parsing other common absolute date/time formats using strptime
    common_abs_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%B %d, %Y",  # 添加对 "Month Day, Year" 格式的支持
        "%b %d, %Y",  # 添加对缩写月份格式的支持
    ]
    for fmt in common_abs_formats:
        try:
            dt_obj = datetime.strptime(time_str, fmt)
            if fmt in ["%B %d, %Y", "%b %d, %Y"]:
                # 对于没有时间的日期格式，默认使用当天 00:00
                return dt_obj.strftime("%Y-%m-%d 00:00")
            return dt_obj.strftime(target_format)
        except ValueError:
            continue
            
    return time_str

def create_email_content(articles: List[Dict[str, Any]]) -> str:
    """生成HTML邮件内容"""
    # Sort articles by publish time (newest first)
    articles.sort(key=lambda x: x.get("publish_time", ""), reverse=True)
    
    html_content = (
        f'<html>'
        f'<head>'
        f'<meta charset="UTF-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
        f'<style type="text/css">'
        f'* {{ box-sizing: border-box; }}'
        f'body {{ margin: 0; padding: 10px; background: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}'
        f'.container {{ max-width: 800px; width: 100%; margin: 0 auto; padding: 20px; }}'
        f'.title {{ color: #2c3e50; border-bottom: none; padding-bottom: 15px; text-align: center; font-size: 20px; margin: 0; }}'
        f'.article {{ background: #ffffff; padding: 15px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}'
        f'.article h3, .article .translation-title {{ font-size: 16px; line-height: 1.4; color: #2c3e50; margin: 0 0 10px 0; }}'
        f'.summary, .translation-summary {{ margin: 10px 0; line-height: 1.5; font-size: 14px; color: #222; }}'
        f'.ai-analysis p, .ai-analysis .translation-analysis {{ margin: 6px 0; font-size: 13px; color: #222; }}'
        f'.article a {{ color: #2980b9; text-decoration: none; display: block; word-break: break-all; }}'
        f'.article a:hover {{ color: #3498db; text-decoration: none; }}'
        f'.article-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; align-items: center; color: #7f8c8d; font-size: 13px; }}'
        f'.news-image {{ width: 100%; max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}'
        f'.image-container {{ position: relative; width: 100%; margin: 10px 0; }}'
        f'.publish-time {{ color: #95a5a6; font-size: 12px; margin: 5px 0; }}'
        f'@media screen and (max-width: 768px) {{'
        f'  .container {{ padding: 15px; }}'
        f'  .article {{ padding: 15px; margin-bottom: 20px; }}'
        f'  .article h3 {{ font-size: 16px; }}'
        f'  .summary {{ font-size: 14px; }}'
        f'  .ai-analysis {{ padding: 12px; }}'
        f'  .ai-analysis p {{ font-size: 13px; }}'
        f'  .news-image {{ width: 100% !important; max-width: 100% !important; margin: 10px auto; }}'
        f'}}'
        f'@media screen and (max-width: 480px) {{'
        f'  .container {{ padding: 10px; }}'
        f'  .article {{ padding: 12px; margin-bottom: 15px; }}'
        f'  .article h3 {{ font-size: 15px; }}'
        f'  .summary {{ font-size: 13px; }}'
        f'  .ai-analysis {{ padding: 10px; }}'
        f'  .ai-analysis p {{ font-size: 12px; }}'
        f'  .news-image {{ margin: 8px auto; }}'
        f'}}'
        f'</style>'
        f'</head>'
        f'<body>'
        f'<div class="container">'
        f'<h2 class="title">TOP{len(articles)} 新闻摘要</h2>'
    )

    # 添加新闻内容
    for article in articles:
        processed_url = article["url"]
        if not processed_url.startswith(("http://", "https://")):
            processed_url = f"https://www.reuters.com/{processed_url.lstrip('/')}"
        html_content += (
            f'<div class="article">'
            f'<h3 class="translation-title"><a href="{processed_url}" target="_blank">{article["title"]["en"]}</a></h3>'
            f'<div class="translation-title">{article["title"]["zh"]}</div>'
        )
        
        # 如果有发布时间，格式化并显示时间
        publish_time_raw = article.get("publish_time")
        if publish_time_raw:
            # Ensure the input to format_publish_time is a string
            formatted_time = format_publish_time(str(publish_time_raw))
            html_content += f'<div class="publish-time">发布时间: {formatted_time}</div>'
        
        # 如果有图片，添加图片
        if article.get("image_url"):
            html_content += (            f'<div class="image-container">'
            f'<img src="{article["image_url"]}" alt="{article["title"]["en"]}" class="news-image" style="width: 100%; max-width: 700px; height: auto; display: block; margin: 0 auto; border: 0; border-radius: 8px;" loading="lazy">'
            f'</div>'
            )
            
        html_content += (
            f'<div class="summary translation-summary">{article["description"]["en"]}</div>'
            f'<div class="translation-summary">{article["description"]["zh"]}</div>'
            f'<div class="ai-analysis">'
            f'<p><strong>主要事件：</strong>{article["analysis"]["overview"]["en"]}</p>'
            f'<div class="translation-analysis">{article["analysis"]["overview"]["zh"]}</div>'
            # f'<p><strong>关键人物和机构：</strong>{article["analysis"]["key_entities"]["en"]}</p>'
            # f'<div class="translation-analysis">{article["analysis"]["key_entities"]["zh"]}</div>'
            f'<p><strong>事件影响：</strong>{article["analysis"]["impact"]["en"]}</p>'
            f'<div class="translation-analysis">{article["analysis"]["impact"]["zh"]}</div>'
            f'</div>'
            f'</div>'
        )

    html_content += '</div></body></html>'
    return html_content

def send_email(content: str) -> None:
    """通过SMTP发送邮件"""
    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = f"Reuters每日新闻 {datetime.now().strftime('%Y-%m-%d')}"
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
        
        # 检查AI分析是否成功
        if not articles or (articles and "AI analysis failed" in articles[0].get("title", {}).get("en", "")):
            logger.info("AI分析失败或未获取到有效新闻，跳过发送邮件")
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