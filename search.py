# search.py
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def google_custom_search(query, num_results=10):
    """
    使用 Google Custom Search JSON API 执行网络搜索
    
    Args:
        query (str): 搜索查询
        num_results (int): 返回结果数量，最大为10
    
    Returns:
        dict: 搜索结果，包含搜索元数据和搜索项目列表
    """
    # 从环境变量获取API密钥和搜索引擎ID
    api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    cse_id = os.getenv('GOOGLE_CSE_ID')
    
    if not api_key or not cse_id:
        print("错误: 未配置 GOOGLE_SEARCH_API_KEY 或 GOOGLE_CSE_ID")
        print("请在.env文件中添加这两个环境变量")
        return None
    
    # 构建API请求URL
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'key': api_key,
        'cx': cse_id,
        'num': min(num_results, 10)  # API限制最多10个结果
    }
    
    try:
        # 发送请求
        response = requests.get(search_url, params=params)
        response.raise_for_status()  # 检查HTTP错误
        
        # 解析结果
        search_results = response.json()
        
        if 'items' not in search_results:
            print(f"未找到'{query}'的搜索结果")
            return {
                'query': query,
                'total_results': 0,
                'items': []
            }
        
        # 返回结果
        return {
            'query': query,
            'total_results': search_results.get('searchInformation', {}).get('totalResults', 0),
            'items': search_results.get('items', [])
        }
    
    except requests.exceptions.RequestException as e:
        print(f"搜索请求失败: {str(e)}")
        return None
    except json.JSONDecodeError:
        print("解析搜索结果失败")
        return None
    except Exception as e:
        print(f"搜索过程中发生错误: {str(e)}")
        return None


def format_search_results(search_results, max_snippets=10, include_urls=True):
    """
    将Google搜索结果格式化为可读的文本
    
    Args:
        search_results (dict): 搜索结果字典
        max_snippets (int): 返回的最大摘要数量
        include_urls (bool): 是否包含URL
    
    Returns:
        str: 格式化后的搜索结果文本
    """
    if not search_results or 'items' not in search_results or not search_results['items']:
        return f'未找到有关"{search_results.get("query", "")}"的搜索结果'
    
    output = f'### 搜索结果："{search_results["query"]}"\n\n'
    
    # 限制结果数量
    items = search_results['items'][:max_snippets]
    
    for i, item in enumerate(items, 1):
        title = item.get('title', '无标题')
        snippet = item.get('snippet', '无摘要').replace('\n', ' ')
        link = item.get('link', '#')
        
        output += f"{i}. **{title}**\n"
        output += f"   {snippet}\n"
        if include_urls:
            output += f"   链接: {link}\n"
        output += "\n"
    
    return output
