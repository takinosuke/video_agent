from dotenv import load_dotenv
import streamlit as st
from google import genai
import time
import json
import random
import os
import ScenarioMakeAgent
from apify_client import ApifyClient
import re
import requests

#ユーザー聞き取り関数
def identifyUserNeeds(user_input, history_text):
    apifyApiKey = os.getenv('APIFY_API')
    client = ApifyClient(apifyApiKey)

    context = ""
    for msg in history_text:
        role = "ユーザー" if msg["role"] == "user" else "AI"
        context += f"{role}: {msg['content']}\n"
    
    prompt = f"""
        Instagramの動画検索用キーワードを生成してください。
        以下の【制約事項】を厳守し、結果のみを出力してください。

        # 制約事項
        1. キーワードは【ユーザーの要望】に最も関連するものを3個厳選すること。
        2. 出力形式は、Pythonのリスト形式 ["A", "B", "C"] で出力すること。
        3. ハッシュタグ記号（#）、箇条書き記号（* や -）、説明文、改行などは一切含めないこと。
        4. 1行で出力すること。

        # ユーザーの要望
        {context}
    """
    raw_text = ""
    for attempt in range(2):
        try:           
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_text = response.text
            break
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"

    st.write(raw_text)

    # 1. 記号（ [ ] ' " ）をすべて除去して純粋なテキストにする
    clean_text = re.sub(r"[\[\]'\"“”‘’]", "", raw_text)
    # 2. カンマ、改行、スペースのどれかで区切って、個別のワードに分ける
    # これで ['おもしろ動画', 'Vlog'] のようなリストになります  
    keyword_list = [word.strip() for word in re.split(r'[,\n\s]+', clean_text) if word.strip()]

    st.write(f"抽出後：{keyword_list}")

    keywords = [f"https://www.instagram.com/explore/tags/{key}/" for key in keyword_list]
    st.write(f"{keywords}")

    run_input = {
        "searchType": "hashtag",        # モード指定を先頭に
        "directUrls": keywords,           # 抽出した ['投資', '節約術', '資産形成']
        "resultsType": "reels",
        "searchLimit": 5,
        "onlyPostsNewerThan": "2024-01-01",
        "resultsLimit": 1,
        "proxyConfiguration": { "useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"] }
    }
    
    run = client.actor("apify/instagram-scraper").call(run_input=run_input)

    # 結果のリストを作成
    video_list = []
    url_list = []
    counter = 0
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        video_list.append({
            "url": item.get("url"),
            "video_url": item.get("videoUrl"),
            "caption": item.get("caption"),
            "likes": item.get("likesCount")
        })
        st.write(f"videUrlは：{item.get("videoUrl")}")
        st.write(f"urlは：{item.get("url")}")
        st.write(f"typeは：{item.get("type")}")
        # 1. 動画を一時的に保存
        video_data = requests.get(item.get("videoUrl")).content
        with open(f"temp_video_{counter}.mp4", "wb") as f:
            f.write(video_data)
        url_list.append(f"temp_video_{counter}.mp4")
    
    ## url毎に特徴を取得する。
    raw_text = []
    for item in url_list:
        with open(item, "rb") as f:
            # 動画をアップロード（Apifyで落としたファイル）
            video_file = genai_client.files.upload(file=f, config={'mime_type': 'video/mp4'})
        
        # アップロード直後
        print("動画を処理中...")
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai_client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED":
            st.write("失敗しました。")
            raise ValueError("Video processing failed.")

        prompt = f"""
                あなたはプロの動画分析クリエイターです。
                送付した動画が流行る理由をさまざまな角度から推測し、特徴を教えてください。
        """        
        for attempt in range(5):
            try:           
                response = genai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[prompt, video_file]
                )
                st.write(response.text)
                raw_text.append(response.text)
                break
            
            except Exception as e:
                wait = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait)
                st.write("gemini問い合わせに失敗。")
                st.error(f"--- 試行 {attempt+1} 回目のエラー詳細 ---")
                st.warning(f"エラー種別: {type(e).__name__}")
                st.code(str(e)) # エラーメッセージ本体
                if attempt == 4:
                    #return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"
                    break

    #全体の特徴を出す。
    prompt = f"""
                あなたは特徴量分析のプロです。
                下記は最近の流行の動画の特徴を1つ1つ分析した文章になります。
                この文章から、最近の流行りの動画にはどのような傾向やギミックがあるのかをまとめてください。

                # 動画分析文
                {raw_text}
    """        
    for attempt in range(5):
        try:           
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            st.write(response.text)
            break
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                #return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"
                break
    return 0

def setup_app(): 
    # ページ設定
    st.set_page_config(page_title="AIチャット", page_icon="🤖")
    st.title("🤖 AIチャット")

    # チャット履歴をセッション状態で保持（初回のみ実行）
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "transitionState" not in st.session_state:
        st.session_state.transitionState = 0
    if "log" not in st.session_state:
        st.session_state.log = []
    if "jsonList" not in st.session_state:
        st.session_state.jsonList = []
    if "analysisText" not in st.session_state:
        st.session_state.analysisText = ""

def display_chat_history():
    # 過去の会話を表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_chat():    
    try:
        # ユーザー入力フォーム
        if prompt := st.chat_input("メッセージを入力してください...",key="input_1"):
            # ユーザー入力を追加
            with st.chat_message("user"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.markdown(prompt)

            # AI返信を生成・表示
            with st.chat_message("assistant"):
                with st.spinner("AIが考え中..."):
                    ## 最初の分岐。0：動画分析セクション。1：台本作成セクション
                    #if st.session_state.transitionState == 0:
                    response = identifyUserNeeds(prompt, st.session_state.messages)
                    st.write(response)
        # クリアボタン
        if st.button("会話クリア", use_container_width=True, key="clear_button"):
            st.session_state.messages = []
            st.rerun()
    except Exception as e:
        st.write(e)
        st.stop()

load_dotenv()
googleKey = os.getenv('GOOGLE_API_KEY')
genai_client = genai.Client(api_key=googleKey)
setup_app()
display_chat_history()
handle_chat()