import os
import datetime
import time
import random
from dotenv import load_dotenv
import google.generativeai as genai

# 导入所需的类型
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.ai.generativelanguage import FunctionDeclaration, Tool

# 定义生成内容的基本结构
class Part:
    def __init__(self, text=None, function_call=None, function_response=None):
        self.text = text
        self.function_call = function_call
        self.function_response = function_response

# 尝试导入 googlesearch，如果失败则提示安装
try:
    from googlesearch import search as perform_google_search
except ImportError:
    print("错误：未能导入 'googlesearch' 库。")
    print("请先安装它：pip install googlesearch-python")
    exit()

load_dotenv()

# --- 步骤 1: 定义实际执行搜索的 Python 函数 ---
def execute_google_search(query: str, num_results: int = 5) -> str:
    """
    使用 'googlesearch-python' 库执行Google搜索。

    注意: 这个基础实现主要返回搜索到的URL列表。
    'googlesearch-python' 默认情况下返回URL。为了获得更丰富的信息
    （如标题和内容摘要），可能需要进一步处理这些URL（例如通过网络抓取，
    这会增加复杂性和潜在的道德及技术问题），或者使用其他能直接提供摘要的搜索库。
    """
    print(f"\n🤖 工具调用：正在为查询 '{query}' 执行Google搜索 (最多 {num_results} 条结果)...")
    search_results_list = []
    try:
        # googlesearch.search 返回一个URL字符串的生成器
        # stop 参数控制结果数量, pause 参数避免请求过于频繁被Google阻止
        for url in perform_google_search(query, num_results=num_results, lang='zh-CN', stop=num_results, pause=2.0):
            search_results_list.append(url)
        
        if not search_results_list:
            return f"针对查询 '{query}' 未找到Google搜索结果。"

        # 将结果格式化为字符串
        results_str = f"为查询 '{query}' 找到了以下 {len(search_results_list)} 个URL：\n"
        for idx, url_item in enumerate(search_results_list):
            results_str += f"{idx+1}. {url_item}\n"
        
        results_str += "\n请注意：以上是URL列表。这些页面的实际内容未被提取。"
        print(f"🔍 搜索工具返回 (部分内容): {results_str[:300]}...") # 打印部分结果，避免过长
        return results_str

    except Exception as e:
        error_message = f"通过 'googlesearch-python' 执行Google搜索时发生错误: {e}"
        print(error_message)
        return error_message

# --- 步骤 2: 为Gemini模型声明搜索工具 ---
google_search_tool_declaration = FunctionDeclaration(
    name="execute_google_search", # 必须与您的Python函数名一致
    description=(
        "当需要获取关于特定主题的最新信息、新闻或回答在自身知识库中找不到的问题时，"
        "使用此工具进行Google网络搜索。输入应该是一个搜索查询字符串。"
        "此工具将返回一个包含相关URL的列表。"
    ),
    parameters={
        "type_": "OBJECT", 
        "properties": {
            "query": {"type_": "STRING", "description": "搜索查询的关键词或问题 (例如 '全球最新科技新闻')"},
            "num_results": {"type_": "INTEGER", "description": "期望返回的搜索结果URL数量 (默认为5)"}
        },
        "required": ["query"] 
    }
)

web_search_tool = Tool(function_declarations=[google_search_tool_declaration])

# --- 主要函数: 获取全球新闻并使用Google搜索工具 ---
def get_global_top_news():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("错误：未在 .env 文件中配置 GEMINI_API_KEY")
        return

    try:
        genai.configure(api_key=api_key)

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
        
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 60,
            "max_output_tokens": 8192,
        }

        # 模型选择，允许降级使用不同模型
        model_options = [
            "gemini-1.5-pro-latest",  # 首选，工具使用能力最强
            "gemini-1.5-flash-latest", # 备选1，更快但工具使用能力较弱
            "gemini-pro",            # 备选2，旧版本但有不同的配额
        ]
        
        # 默认使用第一个模型
        model_name = model_options[0]
        print(f"ℹ️ 使用模型: {model_name}")

        model = genai.GenerativeModel(
            model_name=model_name, 
            generation_config=generation_config,
            safety_settings=safety_settings,
            tools=[web_search_tool] 
        )

        current_date_str = datetime.date.today().strftime('%Y年%m月%d日')
        initial_prompt_text = f"""今天是 {current_date_str}。
        请利用你拥有的 'execute_Google Search' 工具来查找并列出近期全球范围内受到广泛关注的5条重要新闻。
        对于你找到的每个新闻事件，请执行以下操作：
        1. 简明扼要地描述新闻内容（约50字）。由于工具仅返回URL，你需要根据URL本身可能包含的信息（如果URL具有描述性）或结合你的通用知识进行推断。如果URL不足以推断，请明确说明。
        2. 提及相关的大致日期或时期。
        3. 列出你推断所依据的来源URL（来自工具的返回结果）。
        请用中文输出。如果工具返回的URL信息不足，请也如实告知。
        """
        
        print(f"💬 发送给模型的初始提示 (部分): {initial_prompt_text[:200]}...\n")
        
        # 直接使用文本字符串作为提示
        conversation_history = initial_prompt_text
        
        max_tool_interaction_rounds = 3 
        final_text_response_generated = False

        for i in range(max_tool_interaction_rounds):
            print(f"🔄 第 {i+1} 轮与模型交互 (非流式，检查函数调用)...")
            # 第一次/中间的调用是非流式的，以便检查是否有函数调用
            
            # 添加指数退避重试机制和模型降级策略
            retry_count = 0
            max_retries = 3
            current_model_index = 0
            
            while retry_count < max_retries and current_model_index < len(model_options):
                try:
                    # 如果不是第一次尝试，更新模型
                    if retry_count > 0 or current_model_index > 0:
                        model_name = model_options[current_model_index]
                        print(f"⚠️ 尝试使用替代模型: {model_name}")
                        model = genai.GenerativeModel(
                            model_name=model_name, 
                            generation_config=generation_config,
                            safety_settings=safety_settings,
                            tools=[web_search_tool] 
                        )
                    
                    # 尝试生成内容
                    response = model.generate_content(conversation_history)
                    break  # 成功则跳出循环
                    
                except Exception as e:
                    error_message = str(e)
                    print(f"与Gemini模型交互过程中发生错误: {error_message}")
                    
                    # 检查是否是配额错误 (429)
                    if "429" in error_message and "exceeded your current quota" in error_message:
                        # 如果是当前模型的配额问题，尝试切换到下一个模型
                        current_model_index += 1
                        if current_model_index < len(model_options):
                            print(f"配额超限，将尝试切换到: {model_options[current_model_index]}")
                            retry_count = 0  # 重置重试计数，因为我们要尝试新模型
                        else:
                            print("所有可用模型的配额都已超限，请稍后再试或升级到付费计划。")
                            return
                    else:
                        # 其他错误使用指数退避策略
                        retry_count += 1
                        if retry_count < max_retries:
                            # 计算等待时间 (指数退避 + 随机抖动)
                            wait_time = (2 ** retry_count) + (random.random() * 2)
                            print(f"将在 {wait_time:.2f} 秒后重试... (尝试 {retry_count}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            print(f"达到最大重试次数 ({max_retries})，放弃。")
                            return
            
            # 如果所有重试和模型尝试都失败
            if retry_count >= max_retries and current_model_index >= len(model_options):
                print("无法成功与任何模型交互，请稍后再试。")
                return
                
            # 成功获取响应后的处理
            
            if not response.candidates:
                print("模型没有返回候选答案。")
                break
            candidate = response.candidates[0]

            if not candidate.content:
                print("模型回复中没有内容部分。")
                break

            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_call = part.function_call
                        function_name = function_call.name
                        args = dict(function_call.args)

                print(f"⚡ 模型请求调用函数: '{function_name}'，参数: {args}")

                if function_name == "execute_Google Search":
                    search_query = args.get("query", "全球热点新闻") 
                    num_res = args.get("num_results", 5)
                    
                    tool_response_content = execute_google_search(query=search_query, num_results=num_res)
                    
                    # 更新对话历史为工具的响应
                    conversation_history = f"{conversation_history}\n工具响应: {tool_response_content}"
                    print(f"🗣️ 已将 '{function_name}' 的执行结果返回给模型。准备获取最终答复...\n")
                else:
                    print(f"错误：模型尝试调用一个未定义的函数 '{function_name}'。已停止。")
                    # 可以考虑将此信息也反馈给模型
                    # 更新对话历史，包含错误信息
                    conversation_history = f"{conversation_history}\n错误: 未知的函数名 {function_name}"
                    # 重新生成一次，看模型如何反应
                    # continue # 或者直接 break
                    break 
            
            else: # 没有函数调用，这应该是包含最终文本回复的响应
                print("\n✅ AI正在生成最终回复 (流式输出):")
                # 现在，我们得到了包含文本的回复，可以用流式方式打印它
                # 为了流式打印，需要重新用 stream=True 调用，或者假设此非流式回复已是最终答案
                # 为了简单起见，如果上一步是非流式，我们直接打印文本
                # 若要严格按用户原样流式输出最终结果，则在确认无函数调用后，
                # 或者在函数调用完成后，用 stream=True 重新请求一次。

                # 为了实现最终答案的流式输出，我们在确认所有工具调用完成后，
                # 用更新后的 conversation_history 进行一次流式调用。
                # 此处的 'else' 意味着上一次的非流式调用已是最终文本。
                # 我们将直接打印这个文本，如果希望它也流式，则需要调整逻辑。

                # 修正逻辑：如果上一个response是最终文本，直接打印。
                # 若希望最终部分也流式，则需要在工具调用结束后，明确进行一次流式generate_content
                if part.text:
                    print(part.text) # 这是上一个非流式调用的直接文本结果
                else:
                    print("(回复中不包含文本)")
                final_text_response_generated = True
                break 
        
        # 如果经历了函数调用，并且现在期望模型基于工具结果生成最终回复（流式）
        if not final_text_response_generated and any(p.function_response for p in conversation_history if hasattr(p, 'function_response')):
            print("\n✅ AI正在根据搜索结果生成最终回复 (流式输出):")
            final_response_stream = model.generate_content(
                conversation_history, # 包含所有历史记录，包括工具调用和响应
                stream=True
            )
            full_final_text = ""
            for chunk in final_response_stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    full_final_text += chunk.text
            print() # 换行
            final_text_response_generated = True

        if not final_text_response_generated :
             print("\n未能从模型获取最终的文本回复或已达最大交互轮次。")
             # 尝试打印最后一次的候选回复（如果存在）
             if 'candidate' in locals() and candidate.content and candidate.content.parts and candidate.content.parts[0].text:
                  print("模型的最后文本输出:", candidate.content.parts[0].text)

    except Exception as e:
        print(f"与Gemini模型交互过程中发生错误: {e}")
        # 可以在这里添加更详细的错误信息，例如 response.prompt_feedback
        # if 'response' in locals() and hasattr(response, 'prompt_feedback'):
        #     print(f"模型的提示反馈: {response.prompt_feedback}")

    finally:
        print("\n" + "-" * 80)
        print("新闻获取流程结束。")


if __name__ == "__main__":
    get_global_top_news()