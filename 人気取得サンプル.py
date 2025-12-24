from openai import OpenAI
import os
from dotenv import load_dotenv
from google import genai
import google.genai.types as types
import re
import time
import random
from pathlib import Path

load_dotenv()
perpApiKey = os.getenv('PERPLE_API_KEY')
googleKey = os.getenv('GOOGLE_API_KEY')

# Perplexity API
client = OpenAI(api_key=perpApiKey, base_url="https://api.perplexity.ai")

# -------------------
#  リトライ共通関数
# -------------------
def exponential_backoff(attempt):
    """指数バックオフの計算"""
    return (2 ** attempt) + random.uniform(0, 1)


# -----------------------------
# Gemini generate_content 安全版
# -----------------------------
def safe_generate_content(prompt, retries=12):
    for attempt in range(retries):
        try:
            return genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
        except Exception as e:
            print(f"⚠ generate_content エラー（{attempt+1}/{retries}）: {e}")
            wait = exponential_backoff(attempt)
            print(f"⏳ {wait:.1f} 秒待機してリトライ…")
            time.sleep(wait)

    raise RuntimeError("❌ generate_content が連続失敗しました。Gemini が過負荷状態です。")


# -----------------------------
# VEO 動画生成 安全版
# -----------------------------
def safe_generate_video(prompt, current_video, retries=12):
    for attempt in range(retries):
        try:
            config = types.GenerateVideosConfig(
                number_of_videos=1,
                resolution="720p"
            )
            return genai_client.models.generate_videos(
                model=veo_model,
                prompt=prompt.strip(),
                video=current_video,
                config=config
            )
        except Exception as e:
            print(f"⚠ generate_videos エラー（{attempt+1}/{retries}）: {e}")
            wait = exponential_backoff(attempt)
            print(f"⏳ {wait:.1f} 秒待機してリトライ…")
            time.sleep(wait)

    raise RuntimeError("❌ generate_videos が連続失敗しました。VEO が過負荷状態です。")


# ----------------------------------------
# Perplexity：トレンド調査プロンプト生成
# ----------------------------------------
response = client.chat.completions.create(
    model="sonar",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": """
        直近トレンドから、「実際に再生数が非常に伸びやすい動画の特徴」をかなり具体的に推測してください。
        このあとAIにその特徴を含んだ映画を作らせたいため、そのためのプロンプトを作ってください。
        """}
    ],
)
print('---------------------------------------------------------')
print(response.choices[0].message.content)
print('---------------------------------------------------------')

# Gemini Client
genai_client = genai.Client(api_key=googleKey)

# -------------------------------
#  プロンプト 3パート生成
# -------------------------------
moviePrompt = []

for i in range(3):

    if i == 0:
        # 最初のメタプロンプト
        prompt = f"""
        現在のインスタグラムのトレンドを調査しました。
        調査結果を下記に乗せるので、
        AIに動画生成をさせるためのプロンプトを
        下記のフォーマットに従って教えてください。
        特に画面に表示させる文字については正確に何を表示させるかを指定してください。
        音声についても読ませる文字を台本として定義し、指定してください。
        
        ↓フォーマット例
        【動画の目的】
        商品の紹介をする短い動画。
        【映像】
        ・明るい白い背景で商品が置かれているシーン
        ・商品のクローズアップ
        ・最後にテキスト表示
        【動画内テキストについて】
        以下の日本語テキストを、正確にこのまま表示してください。
        ・他の言語に翻訳しない
        ・フォントは日本語フォント（Noto Sans JP または類似の日本語フォント）を使用
        ・文字の崩れや省略をしない
        【表示するテキスト内容】
        「高品質・低価格」
        「おすすめ商品です！」
        【ナレーション】
        自然な日本語で読み上げてください。
        話者：落ち着いた30代の日本人
        イントネーション：標準的な日本語
        読み上げ台本：
        「こちらの商品は、高品質で低価格を実現した自信作です。」
        【禁止事項】
        ・中国語や簡体字・繁体字を使用しない
        ・ローマ字化しない
        ・抽象的な模様のような文字を生成しない

        ↓ 調査結果
        {response.choices[0].message.content}

        投げるべきプロンプトは^^^で囲んで返答をお願いします。
        """
    else:
        # 2回目以降、つながる動画のための続きプロンプト
        prompt = f"""
        現在のインスタグラムのトレンドを調査しました。
        下記の特徴を満たす動画を生成するためのプロンプトを作成してください。
        特に画面に表示させる文字については正確に何を表示させるかを指定してください。
        音声についても読ませる文字を台本として定義し、指定してください。
        
        ↓フォーマット例
        【動画の目的】
        商品の紹介をする短い動画。
        【映像】
        ・明るい白い背景で商品が置かれているシーン
        ・商品のクローズアップ
        ・最後にテキスト表示
        【動画内テキストについて】
        以下の日本語テキストを、正確にこのまま表示してください。
        ・他の言語に翻訳しない
        ・フォントは日本語フォント（Noto Sans JP または類似の日本語フォント）を使用
        ・文字の崩れや省略をしない
        【表示するテキスト内容】
        「高品質・低価格」
        「おすすめ商品です！」
        【ナレーション】
        自然な日本語で読み上げてください。
        話者：落ち着いた30代の日本人
        イントネーション：標準的な日本語
        読み上げ台本：
        「こちらの商品は、高品質で低価格を実現した自信作です。」
        【禁止事項】
        ・中国語や簡体字・繁体字を使用しない
        ・ローマ字化しない
        ・抽象的な模様のような文字を生成しない
        
        直前の動画プロンプトはこちら：
        {moviePrompt[i-1]}

        この内容と自然につながる動画になるように、
        続きのプロンプトを作ってください。

        投げるべきプロンプトは^^^で囲んで返答をお願いします。
        """

    # 指数バックオフ付き API 呼び出し
    response = safe_generate_content(prompt)

    print("---------------------------------------------------------------------")
    print(response.text)
    print("---------------------------------------------------------------------")

    moviePrompt.append(response.text)

    # 最低限のクールダウン
    time.sleep(5)


# -------------------------------
#  動画生成パート（3分割）
# -------------------------------
veo_model = "veo-3.1-generate-preview"
current_video = None
counter = 0

for prm in moviePrompt:

    print(f"\n＝＝＝＝＝＝＝＝ プロンプト {counter + 1} ＝＝＝＝＝＝＝＝")
    print(prm)

    # 安全な generate_videos（指数バックオフ付き）
    operation = safe_generate_video(prm, current_video)

    # 完成を待つ
    while not operation.done:
        print("生成中…")
        time.sleep(10)
        operation = genai_client.operations.get(operation)

    # 生成された動画を保存
    generated_video = operation.response.generated_videos[0]

    # ダウンロード
    genai_client.files.download(file=generated_video.video)

    # 保存
    output_path = f"output_part_{counter + 1}.mp4"
    generated_video.video.save(output_path)

    print(f"✅ パート{counter + 1} 保存完了: {output_path}")

    # 次の動画のために引き継ぎ
    current_video = generated_video.video

    # クールダウン
    time.sleep(8)

    counter += 1

print("\n🎉 すべての動画パートが正常に生成・保存されました！")
