import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

# .envファイルからAPIキーを読み込み
load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_API_KEYが設定されていません。")

# Gemini APIのモデルをLangChainで初期化（gemini-1.5-flashを使用、無料枠対応）
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", # ⭐ ここを修正
    google_api_key=api_key,
    temperature=0.7 
)

# 会話履歴を保持するリスト
conversation_history = []

def chat_with_agent(user_input):
    # 人間のメッセージを追加
    conversation_history.append(HumanMessage(content=user_input))
    
    # Geminiにメッセージを送信（履歴を含む）
    response = llm.invoke(conversation_history)
    
    # AIの応答を追加
    ai_response = response.content
    conversation_history.append(AIMessage(content=ai_response))
    
    return ai_response

# メインループ：インタラクティブなチャット
if __name__ == "__main__":
    print("AIエージェントに話しかけてください。'quit'で終了。")
    while True:
        user_input = input("あなた: ")
        if user_input.lower() == 'quit':
            break
        response = chat_with_agent(user_input)
        print(f"AI: {response}")












from openai import OpenAI
import os
from dotenv import load_dotenv
import google.genai as genai
import re
import time
from pathlib import Path

load_dotenv()
perpApiKey = os.getenv('PERPLE_API_KEY')

client = OpenAI(
    api_key=perpApiKey,
    base_url="https://api.perplexity.ai"
)

response = client.chat.completions.create(
    model="sonar",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "ここ1週間以内のインスタグラムの投稿で人気がある投稿をできる限り正確に推測/計測し、どのような動画なのかなど動画の特徴を教えてください。人気上位の動画と同じような動画を作成する場合にどのような特徴を再現すればよいかを具体的に説明してください。"}
    ],
)

print('---------------------------------------------------------')
print(response.choices[0].message.content)
print('---------------------------------------------------------')

googleKey = os.getenv('GOOGLE_API_KEY')
# APIキーを設定（環境変数から取得推奨）
genai.configure(api_key=googleKey)

# モデル初期化
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# 動画生成プロンプトを生成させるためのメタプロンプト
prompt = f"""
現在のインスタグラムのトレンドを調査しました。
調査をした結果を下記に乗せるので、
下記の特徴を満たす動画を生成するためのプロンプトを作成してください。
１度の生成で作れる動画は８秒が限界のため、
15秒以上にするために複数回投げれるようにプロンプトをください。
投げるべきプロンプトは^^^で切り取れるように返答をお願いします。

↓は調査結果になります。
{response.choices[0].message.content}"""

response = model.generate_content(prompt)

# 結果出力
print("---------------------------------------------------------------------")
print(response.text)
print("---------------------------------------------------------------------")

# 動画作成パート
createPronpt = re.findall(r"\^\^\^(.*?)\^\^\^", response.text, flags=re.DOTALL)

counter = 0
client = genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Veo 3.1 モデル
model = genai.GenerativeModel('veo-3.1-generate-preview')
print(f"パート分けした結果：{len(createPronpt)}")
for prm in createPronpt:
    if counter == 0:
        print("プロンプト1")
        print("-------------------------------------------------------------------------------")
        print(createPronpt[0])
        config = genai.types.GenerateVideosConfig(number_of_videos=1, resolution="720p")
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            video=None,
            config=config
        )
        while not operation.done:
            print("生成中...")
            time.sleep(10)
            operation = client.operations.get(operation)
        video = operation.response.generated_videos[0]
        client.files.download(file=video.video)
        video.video.save("output.mp4")
        current_video = video.video
    else:
        print(f"プロンプト{counter}")
        print("-------------------------------------------------------------------------------")
        print(prm)
        config = genai.types.GenerateVideosConfig(number_of_videos=1, resolution="720p")
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            video=current_video,
            config=config
        )
        while not operation.done:
            print("生成中...")
            time.sleep(10)
            operation = client.operations.get(operation)
        video = operation.response.generated_videos[0]
        client.files.download(file=video.video)
        video.video.save("output.mp4")
        current_video = video.video
    time.sleep(10)  # クォータ回避待機
    counter += 1

print("動画作成完了")
print(next_video)