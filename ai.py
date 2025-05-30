# ai.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import datetime

# 导入搜索功能
from search import google_custom_search, format_search_results

load_dotenv()

# 可用的Gemini模型列表
AVAILABLE_MODELS = {
    # ================ 1.5 系列模型 ================
    # Flash 模型 (更快速)
    "gemini-1.5-flash-latest": {
        "description": "1.5 Flash 模型的最新版本，更快速，适合一般问答",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash": {
        "description": "1.5 Flash 基础模型",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash-001": {
        "description": "1.5 Flash 的 001 版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash-002": {
        "description": "1.5 Flash 的 002 版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash-8b": {
        "description": "1.5 Flash 8B 小型模型",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash-8b-latest": {
        "description": "1.5 Flash 8B 模型的最新版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    
    # Pro 模型 (更强大)
    "gemini-1.5-pro-latest": {
        "description": "1.5 Pro 模型的最新版本，更强大的推理能力",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-pro": {
        "description": "1.5 Pro 基础模型",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-pro-001": {
        "description": "1.5 Pro 的 001 版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-pro-002": {
        "description": "1.5 Pro 的 002 版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    
    # ================ 2.5 系列模型 (预览版) ================
    "gemini-2.5-flash-preview-05-20": {
        "description": "2.5 Flash 最新预览版本 (2025-05-20)",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-2.5-pro-preview-05-06": {
        "description": "2.5 Pro 最新预览版本 (2025-05-06)",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-2.5-flash-preview-tts": {
        "description": "2.5 Flash 支持文本转语音的预览版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-2.5-pro-preview-tts": {
        "description": "2.5 Pro 支持文本转语音的预览版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    
    # ================ 1.0 系列模型 ================
    "gemini-pro": {
        "description": "Gemini 1.0 Pro 模型，支持文本处理",
        "max_tokens": 2048,
        "supports_tools": True
    },
    "gemini-pro-vision": {
        "description": "Gemini 1.0 Pro Vision 模型，支持图像处理",
        "max_tokens": 2048,
        "supports_tools": False
    },
    
    # ================ 嵌入模型 ================
    "embedding-gecko-001": {
        "description": "PaLM 2 嵌入模型",
        "max_tokens": 768,  # 嵌入维度
        "supports_tools": False
    },
    "gemini-embedding-exp": {
        "description": "Gemini 嵌入模型（实验版）",
        "max_tokens": 768,  # 嵌入维度可能更高
        "supports_tools": False
    },
}

def get_available_free_models():
    """
    获取当前所有可用的免费模型
    
    Returns:
        dict: 以模型名称为键，模型类型为值的字典
    """
    try:
        # 获取API密钥
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("未配置 GEMINI_API_KEY")
            return {}
            
        genai.configure(api_key=api_key)
        
        # 获取所有模型
        all_models = genai.list_models()
        
        # 可能的免费模型前缀或标识符
        free_tier_identifiers = [
            "bison-001",           # PaLM2 文本/聊天
            "gecko-001",           # PaLM2 嵌入
            "gemini-2.5-flash",    # Gemini 2.5 Flash 预览
            "gemini-2.5-pro",      # Gemini 2.5 Pro 预览
            "gemini-embedding",    # Gemini 嵌入
            "gemini-1.5-flash",    # Gemini 1.5 Flash
            "gemini-1.5-pro",      # Gemini 1.5 Pro
            "gemini-pro",          # Gemini Pro
        ]
        
        # 按功能分类存储模型
        model_by_type = {
            "text": [],
            "chat": [],
            "embedding": [],
            "multimodal": [],
            "other": []
        }
        
        # 筛选可能的免费模型
        free_models = []
        for model in all_models:
            model_name = model.name
            # 提取模型实际名称（去除路径前缀）
            short_name = model_name.split('/')[-1] if '/' in model_name else model_name
            
            # 检查是否为可能的免费模型
            if any(identifier in short_name for identifier in free_tier_identifiers):
                free_models.append(short_name)
                
                # 根据名称或功能分类
                if "embedding" in short_name:
                    model_by_type["embedding"].append(short_name)
                elif "vision" in short_name or "multimodal" in short_name:
                    model_by_type["multimodal"].append(short_name)
                elif "chat" in short_name:
                    model_by_type["chat"].append(short_name)
                elif any(text_id in short_name for text_id in ["gemini", "pro", "flash", "bison"]):
                    model_by_type["text"].append(short_name)
                else:
                    model_by_type["other"].append(short_name)
        
        return model_by_type
    
    except Exception as e:
        print(f"获取模型列表失败: {str(e)}")
        return {}


def list_free_models():
    """列出并打印所有可用的免费模型"""
    model_by_type = get_available_free_models()
    
    if not any(model_by_type.values()):
        print("未找到任何可用模型或API调用失败")
        return
    
    print("\n当前可用的免费模型：")
    print("-" * 80)
    
    for model_type, models in model_by_type.items():
        if models:
            print(f"\n{model_type.title()} 模型:")
            for model in sorted(models):
                print(f"- {model}")
    
    print("\n" + "-" * 80)
    print("注意：模型的分类是根据名称特征推断的，可能不完全准确")
    print("-" * 80)


def ask_ai(prompt, model_name="gemini-1.5-flash-latest", max_output_tokens=None, enable_search=False, search_results_count=3):
    """
    使用 Gemini AI 模型获取对指定问题的回答
    
    Args:
        prompt (str): 向AI提问的内容
        model_name (str, optional): 使用的模型名称。默认为 "gemini-1.5-flash-latest"。
            可用模型：gemini-1.5-pro-latest, gemini-1.5-flash-latest, gemini-pro, gemini-pro-vision
        max_output_tokens (int, optional): 最大输出令牌数。如果不指定，将根据模型自动设置。
        enable_search (bool, optional): 是否启用网络搜索功能。默认为False。
        search_results_count (int, optional): 如果启用搜索，指定返回的搜索结果数量。
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("未配置 GEMINI_API_KEY")
        return

    try:
        genai.configure(api_key=api_key)

        # 配置安全设置
        safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
        ]

        # 配置生成参数
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 60,
            "max_output_tokens": 8192,
        }

        # 获取模型信息（如果存在）
        model_info = AVAILABLE_MODELS.get(model_name, {
            "description": "未知模型",
            "max_tokens": 8192,
            "supports_tools": True
        })
        
        # 根据模型配置修改最大输出令牌数
        if not max_output_tokens:
            generation_config["max_output_tokens"] = model_info["max_tokens"]
            
        # 创建模型实例
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        print(f"使用模型: {model_name} - {model_info['description']}")
        print(f"最大输出令牌数: {generation_config['max_output_tokens']}")

        print(f"\n🤖 向AI提问: {prompt}")
        print("-" * 80)
        
        # 如果启用搜索功能，先执行搜索并增强提示
        search_info = ""
        if enable_search:
            # 针对新闻查询优化搜索关键词
            search_query = prompt
            if "新闻" in prompt or "TOP" in prompt.upper() or "热点" in prompt:
                current_date = datetime.datetime.now().strftime("%Y年%m月")
                
                # 计算过去三天的日期范围
                today = datetime.datetime.now()
                three_days_ago = (today - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
                today_str = today.strftime("%Y-%m-%d")
                date_range = f"after:{three_days_ago} before:{today_str}"
                
                # 特别关注财经、军事和国际重大新闻，限制三天内
                search_query = f"(财经|金融|经济|军事|国际大事|全球新闻) 热点 重要 {date_range} site:ft.com OR site:wsj.com OR site:bloomberg.com OR site:reuters.com OR site:news.cn OR site:bbc.com OR site:cnn.com OR site:military.com"
                print(f"优化新闻搜索关键词 (最近3天): '{search_query}'")                
                # 按用户偏好增加财经新闻搜索(最近3天)
                finance_search_query = f"(全球财经|金融市场|股市|汇率|经济新闻) 重要 {date_range} site:ft.com OR site:wsj.com OR site:bloomberg.com OR site:cnbc.com"
                print(f"搜索财经新闻 (最近3天)...")
                finance_results = google_custom_search(finance_search_query, max(3, search_results_count//3))
                
                # 按用户偏好增加军事新闻搜索(最近3天)
                military_search_query = f"(军事新闻|军事冲突|安全局势|战争|国防) 重要 {date_range} site:military.com OR site:defenseone.com OR site:news.cn OR site:bbc.com"
                print(f"搜索军事新闻 (最近3天)...")
                military_results = google_custom_search(military_search_query, max(3, search_results_count//3))
                
            print(f"正在进行网络搜索...")
            search_results = google_custom_search(search_query, search_results_count)
            
            if search_results and search_results.get('items'):
                search_info = format_search_results(search_results, search_results_count)
                print("搜索完成，找到相关信息")
                
                # 针对新闻类查询构建专门的提示
                if "新闻" in prompt or "TOP" in prompt.upper() or "热点" in prompt:
                    # 整合额外的财经和军事新闻搜索结果（如果有）
                    finance_info = ""
                    if 'finance_results' in locals() and finance_results and finance_results.get('items'):
                        finance_info = "\n### 财经重要新闻\n" + format_search_results(finance_results, max(3, search_results_count//3))
                        
                    military_info = ""
                    if 'military_results' in locals() and military_results and military_results.get('items'):
                        military_info = "\n### 军事重要新闻\n" + format_search_results(military_results, max(3, search_results_count//3))
                    
                    # 合并所有搜索结果
                    all_search_info = search_info + finance_info + military_info
                    
                    enhanced_prompt = f"""你是一位专业的新闻分析师。我将为你提供一些最近三天内的新闻搜索结果，你的任务是整合这些信息并提取当前最重要的全球新闻事件。

这是最近三天的新闻搜索结果：
{all_search_info}

基于以上搜索结果和你的知识，请回答以下问题：{prompt}

要求：
1. 分析并提取最近三天内最重要的全球新闻事件，特别注重财经、军事和重大国际事件
2. 按重要性排序列出新闻条目，根据最新搜索结果确保内容的时效性
3. 每条新闻简要描述具体事件和影响，并注明属于哪类新闻（财经/军事/国际）
4. 尽量提供新闻发生的大致时间或日期
5. 如果搜索结果中没有足够信息，请基于你的知识来补充可能的重要新闻

请确保你的回答清晰、准确、客观、有条理。"""
                else:
                    # 一般查询的增强提示
                    enhanced_prompt = f"""我将为你提供一些最新的搜索结果，请基于这些信息和你的知识回答以下问题。

{search_info}

现在请回答这个问题：{prompt}

请综合使用搜索结果和你的知识进行回答，所有回答需要准确且及时。如果搜索结果中有更及时的信息，请以搜索结果为准。请用中文回答。"""
                prompt = enhanced_prompt
            else:
                print("无法获取搜索结果或未找到相关信息")
        
        # 生成内容
        response = model.generate_content(
            prompt,
            stream=True
        )

        full_response = ""
        for chunk in response:
            if chunk.text:
                print(chunk.text, end="", flush=True)
                full_response += chunk.text
        print("\n" + "-" * 80)
        
        return full_response

    except Exception as e:
        print(f"AI回答失败: {str(e)}")
        return None

if __name__ == "__main__":
    # 列出当前可用的免费模型
    # list_free_models()
    
    # 使用特定模型进行提问 (根据实际可用模型调整)
    # 不启用联网搜索的基本用法
    # ask_ai("你能使用哪些工具进行联网搜索？", model_name="gemini-2.5-flash-preview-05-20")
    
    # 启用联网搜索的增强用法
    ask_ai("截止至当前，全球大新闻TOP10", 
          model_name="gemini-1.5-flash-latest", 
          enable_search=True, 
          search_results_count=10)