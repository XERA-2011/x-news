# ai.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import datetime

load_dotenv()

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

        today_date = datetime.datetime.now().strftime("%Y年%m月%d日") # 获取当前日期
        prompt = f"""请利用你的搜索能力，查找并列出**截至{today_date}**的近期全球范围内受到广泛关注的10条重要新闻。
        要求：
        1. 请确保新闻来源具有一定的可靠性。
        2. 新闻应具有全球性视角或重要影响。
        3. 每条新闻内容请简明扼要，大约50字左右。
        4. 请按近期发生的顺序或重要性进行大致排序。
        5. 输出格式：序号. [相关日期或时期] 新闻内容
        6. 请用中文输出。
        7. 确保新闻是最新的，而不是几个月前或去年的。
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
    get_global_top_news()  # 运行新函数