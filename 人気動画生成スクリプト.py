from openai import OpenAI
import os
from dotenv import load_dotenv
import time
from pathlib import Path
import requests
import re
from typing import Optional
from requests.exceptions import HTTPError

import uuid
run_id = str(uuid.uuid4())
print(f"RUN ID: {run_id}")

load_dotenv()
perpApiKey = os.getenv('PERPLE_API_KEY')

# Perplexity API
client = OpenAI(api_key=perpApiKey, base_url="https://api.perplexity.ai")

def safe_request_post(url, headers, data, max_retries=10):
    """レート制限対応のPOSTリクエスト"""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 30 * (attempt + 1)))
                print(f"レート制限（429）。{retry_after}秒待機中... (試行 {attempt + 1}/{max_retries})")
                time.sleep(retry_after)
                continue
            response.raise_for_status()
            return response
        except HTTPError as e:
            if response.status_code == 429:
                continue
            raise
    raise Exception("レート制限でリトライ上限超過")

def safe_request_get(url, headers, max_retries=3):
    """レート制限対応のGETリクエスト"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                print(f"ステータス確認でレート制限。10秒待機...")
                time.sleep(10)
                continue
            response.raise_for_status()
            return response
        except HTTPError:
            if response.status_code == 429:
                continue
            raise
    raise Exception("ステータス取得でリトライ上限超過")

def get_video_status(video_id: str) -> dict:
    """動画のステータスを取得"""
    url = f"{base_url}/videos/{video_id}/"
    response = safe_request_get(url, headers)
    return response.json()

def wait_for_completion(video_id: str, timeout: int = 600) -> Optional[str]:
    """動画生成の完了を待機し、ダウンロードURLを返す"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_data = get_video_status(video_id)
        if status_data["status"] == "completed":
            return status_data["download_url"]
        elif status_data["status"] == "failed":
            raise Exception("Video generation failed")
        time.sleep(10)  # 10秒ごとにポーリング
    raise TimeoutError("Video generation timed out")

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
        下記フォーマット例を参考にプロンプトを書いてください。
        プロンプト部分^^^で囲んでプロンプト部分であることがわかるようにしてください。
        
        ↓フォーマット例
        【動画の目的】
        商品の紹介をする短い動画。

        【映像】
        ・明るい白い背景で商品が置かれているシーン
        ・商品のクローズアップ
        ・最後にテキスト表示
        
        【動画の長さ】
         25秒

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
        """}
    ],
)
print('---------------------------------------------------------')
print(response.choices[0].message.content)
print('---------------------------------------------------------')
prompt = re.findall(r'\^\^\^(.*?)\^\^\^',response.choices[0].message.content, re.DOTALL)

print(f"出力された:{prompt[0]}")

NOLANG_API = os.getenv("NOLANG_API")
base_url = "https://api.no-lang.com/v1"
headers = {"Authorization": f"Bearer {NOLANG_API}"}

url = f"{base_url}/videos/generate/"
video_setting_id="3eb72d18-90d1-43d9-b46e-19150662e7c6"
text = f"""
    最近の動画のトレンドを調査した結果が下記になります。
    下記の条件を満たす動画を作成してください。
    
    ↓調査結果
    {prompt[0]}
    """

data = {
    "video_setting_id": video_setting_id,
    "text": text
}

# リトライ付きで動画生成
print("動画生成開始（レート制限対応）...")
response = safe_request_post(url, headers, data)
result = response.json()

print(f"Video ID: {result['video_id']}")

videoid = result['video_id']
# 完了を待機してダウンロード
download_url = wait_for_completion(videoid)
print(f"Download URL: {download_url}")
