from tavily import TavilyClient
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("LLM_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def ai_agent_with_tavily(query: str) -> str:
    """
    Tavilyで検索し、その結果をOpenAIで要約するAIエージェント
    """
    try:
        # 1. TavilyでWeb検索
        search_results = tavily.search(query, max_results=5)
        if not search_results or "results" not in search_results:
            return "検索結果が見つかりませんでした。"

        # 2. 検索結果をテキスト化
        combined_text = "\n".join(
            f"- {item['title']}: {item['content']}" 
            for item in search_results["results"]
        )

        # 3. OpenAIで要約
        prompt = f"""
        あなたは便利なアシスタントで以下はWeb検索結果です。質問に答える形で簡潔にまとめてください。
        質問: {query}
        検索結果:
        {combined_text}
        """
        
        system_prompt = {
            "role": "user",
            "content": prompt
        }

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[system_prompt],
            max_tokens=100,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"エラーが発生しました: {e}"

# ====== 実行例 ======
if __name__ == "__main__":
    print("=== 質問 ===")
    user_query = input()
    answer = ai_agent_with_tavily(user_query)
    print("=== AIエージェントの回答 ===")
    print(answer)