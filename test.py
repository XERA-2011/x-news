# test_run.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
import requests

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

def test_newsapi():
    # 获取新闻数据
    response = requests.get(
        f"https://newsapi.org/v2/top-headlines?sources=bloomberg&pageSize=3&apiKey={os.getenv('NEWS_API_KEY')}"
    )
    print(f"NewsAPI 响应状态码: {response.status_code}")
    articles = response.json()['articles']
    print(f"获取到 {len(articles)} 条新闻")

    # AI生成摘要
    generate_news_summary(articles)

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
    # test_smtp() # 本地测试，很可能会超时