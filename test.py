# test_run.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import requests
from translate import Translator
from datetime import datetime, timedelta

load_dotenv()

def generate_news_summary(articles):
    """
    使用 Gemini AI 为新闻列表生成中文摘要
    Args:
        articles: 新闻文章列表，每个文章应包含 title、description 和 content 字段
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("未配置 GEMINI_API_KEY，跳过AI摘要")
        return

    try:
        genai.configure(api_key=api_key)
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=100
        )
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            generation_config=generation_config
        )

        print("\n生成新闻摘要:")
        for article in articles:
            title = article['title']
            description = article['description'] or ""
            content = article['content'] or ""

            # 构建提示
            prompt = f"""请用中文简要总结以下新闻（不超过50字）：
            标题：{title}
            描述：{description}
            内容：{content}
            """

            # 生成摘要
            response = model.generate_content(prompt)
            if response.parts:
                summary = response.text.strip()
                print(f"\n原标题: {title}")
                print(f"AI摘要: {summary}")

    except Exception as e:
        print(f"生成摘要失败: {str(e)}")

def translate_news(articles):
    """
    翻译新闻列表中的英文标题为中文，并显示日期和来源
    Args:
        articles: 新闻文章列表，每个文章应包含 title、publishedAt 和 source 字段
    """
    try:
        translator = Translator(to_lang="zh")
        print("\n新闻翻译:")

        for article in articles:
            title = article['title']
            published_at = article.get('publishedAt', '未知时间')
            source = article.get('source', {}).get('name', '未知来源')

            # 解析并格式化日期时间
            try:
                dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
            except:
                formatted_date = published_at

            # 翻译标题
            translated_title = translator.translate(title)

            print(f"\n时间: {formatted_date}")
            print(f"来源: {source}")
            print(f"原标题: {title}")
            print(f"翻译标题: {translated_title}")
            print("-" * 80)

    except Exception as e:
        print(f"翻译失败: {str(e)}")

def test_newsapi():
    # 从环境变量获取参数
    news_sources = os.getenv('NEWS_SOURCES', 'axios,reuters,bloomberg,xinhua-net,time')
    page_size = int(os.getenv('NEWS_PAGE_SIZE', '100'))
    # 设置时间范围
    days = int(os.getenv('NEWS_DAYS', '2'))
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    # 构建请求参数
    # url = 'https://newsapi.org/v2/top-headlines'
    url = 'https://newsapi.org/v2/everything'  # 使用 everything 以支持时间范围查询
    params = {
        'sources': news_sources,
        'pageSize': page_size,
        'apiKey': os.getenv('NEWS_API_KEY'),
        'language': 'en',
        'sortBy': 'popularity',
        'from': from_date.strftime('%Y-%m-%d'),
        'to': to_date.strftime('%Y-%m-%d')
    }

    # 获取新闻数据
    response = requests.get(url, params=params, timeout=10)
    print(f"NewsAPI 响应状态码: {response.status_code}")
    articles = response.json()['articles']
    print(f"获取到 {len(articles)} 条新闻")

    # 翻译新闻
    translate_news(articles)
    # AI生成摘要
    # generate_news_summary(articles)

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

def get_global_top_news():
    """
    使用 Gemini AI 获取当前全球热点新闻TOP10，支持联网搜索
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

        # 创建模型实例
        # 使用 gemini-1.5-flash-latest 模型，它具备联网搜索能力
        # 移除了不正确的 tools=genai.tools.code_interpreter 参数
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        prompt = f"""请利用你的搜索能力，查找并列出近期全球范围内受到广泛关注的10条重要新闻。
        要求：
        1. 请确保新闻来源具有一定的可靠性。
        2. 新闻应具有全球性视角或重要影响。
        3. 每条新闻内容请简明扼要，大约50字左右。
        4. 如果可能，请按近期发生的顺序或重要性进行大致排序。
        5. 输出格式：序号. [相关日期或时期] 新闻内容
        6. 请用中文输出。
        """

        # 生成内容，模型会根据提示利用其搜索能力
        response = model.generate_content(
            prompt,
            stream=True
        )

        print("\n正在搜索并生成全球十大热点新闻...")
        full_response = ""
        for chunk in response:
            if chunk.text:
                print(chunk.text, end="", flush=True)
                full_response += chunk.text
        print("\n" + "-" * 80)

    except Exception as e:
        print(f"获取全球新闻失败: {str(e)}")

if __name__ == "__main__":
    test_newsapi()
    # test_newsapi_sources()
    # test_smtp()
    # get_global_top_news()  # 运行新函数