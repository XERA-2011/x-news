import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests

# 将项目根目录添加到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

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

def create_session() -> requests.Session:
    """创建一个带有重试机制的会话"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # 总重试次数
        backoff_factor=1,  # 重试间隔
        status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def get_news_content() -> str:
    """获取Bloomberg新闻页面内容"""
    url = 'https://www.bloomberg.com/'
    headers = {
        'authority': 'www.bloomberg.com',
        'method': 'GET',
        'path': '/',
        'scheme': 'https',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Cookie': 'geo_info={"country":"US","region":"CA"}',
        'Dnt': '1',
        'Pragma': 'no-cache',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    session = create_session()
    try:
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
        
        # 解析HTML内容
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试不同的选择器来获取新闻内容
        content = None
        
        # 尝试获取主要新闻区域
        main_content = soup.find('main')
        if main_content:
            content = main_content
        
        # 如果没有找到main标签，尝试其他可能包含新闻的区域
        if not content:
            content = soup.find('div', {'class': 'top-news-v3'}) or \
                     soup.find('div', {'class': 'single-story-module'}) or \
                     soup.find('body')
        
        if not content:
            logger.warning("无法找到新闻内容区域，返回完整HTML")
            return html
            
        # 清理HTML内容
        for script in content.find_all('script'):
            script.decompose()
        for style in content.find_all('style'):
            style.decompose()
            
        return str(content)
    except requests.Timeout:
        logger.error("获取Bloomberg新闻超时")
        raise
    except requests.RequestException as e:
        logger.error(f"获取Bloomberg新闻失败: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"处理新闻内容时发生错误: {str(e)}")
        raise

def analyze_news_with_ai(html_content: str) -> List[Dict[str, Any]]:
    """使用AI分析新闻内容，返回前10条最重要的新闻"""
    prompt = """
    请分析以下Bloomberg新闻网页内容，选出最重要的10条新闻。
    对于每条新闻，请提供：
    1. 标题
    2. 简短摘要（不超过100字）
    3. 重要性评分（1-10，10为最重要）
    4. 新闻类别（如：经济、政治、科技等）
    
    请用JSON格式返回，格式如下：
    {
        "news": [
            {
                "title": "新闻标题",
                "summary": "新闻摘要",
                "importance": 8,
                "category": "经济"
            },
            ...
        ]
    }
    """
    
    try:
        result = ask_ai(prompt, html_content)
        return result.get("news", [])
    except Exception as e:
        logger.error(f"AI分析新闻失败: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        news_content = get_news_content()
        news_analysis = analyze_news_with_ai(news_content)
        for news in news_analysis:
            print(f"\n标题: {news['title']}")
            print(f"摘要: {news['summary']}")
            print(f"重要性: {news['importance']}")
            print(f"类别: {news['category']}")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")