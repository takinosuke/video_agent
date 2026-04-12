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

# ページ設定
st.set_page_config(page_title="AIチャット", page_icon="🤖")
st.title("🤖 AIチャット")

#ユーザー聞き取り関数
def identifyUserNeeds(type, play_num, analysis_genre):
    apifyApiKey = st.secrets['APIFY_API']
    client = ApifyClient(apifyApiKey)

    # context = ""
    # for msg in history_text:
    #     role = "ユーザー" if msg["role"] == "user" else "AI"
    #     context += f"{role}: {msg['content']}\n"
    
    prompt = f"""
        Instagramの動画検索用キーワードを生成してください。
        以下の【制約事項】を厳守し、結果のみを出力してください。

        # 制約事項
        1. キーワードは【ユーザーの要望】に最も関連するものを3個厳選すること。
        2. 出力形式は、Pythonのリスト形式 ["A", "B", "C"] で出力すること。
        3. ハッシュタグ記号（#）、箇条書き記号（* や -）、説明文、改行などは一切含めないこと。
        4. 1行で出力すること。

        # ユーザーの要望
        {analysis_genre}
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
        "resultsType": type,
        "searchLimit": 5,
        "onlyPostsNewerThan": "2024-01-01",
        "resultsLimit": 4,
        "proxyConfiguration": { "useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"] }
    }
    
    run = client.actor("apify/instagram-scraper").call(run_input=run_input)

    # 結果のリストを作成
    #video_list = []
    url_list = []
    counter = -1
    st.info("動画取得機能開始")
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        counter += 1
        # video_list.append({
        #     "url": item.get("url"),
        #     "video_url": item.get("videoUrl"),
        #     "caption": item.get("caption"),
        #     "likes": item.get("likesCount")
        # })
        st.write(f"videUrlは：{item.get('videoUrl')}")
        st.write(f"urlは：{item.get('url')}")
        st.write(f"typeは：{item.get('type')}")
        st.write(f"回数は：{item.get('videoPlayCount')}")
        st.write(f"回数は：{item.get('videoViewCount')}")
        st.write(f"回数は：{item.get('viewCount')}")
        st.write(f"回数は：{item.get('playCount')}")
        views = item.get("videoPlayCount") or item.get("videoViewCount") or 10000
        st.write(f"視聴回数は：{views}")
        if views >= int(play_num):
            # 1. 動画を一時的に保存
            video_data = requests.get(item.get("videoUrl")).content
            with open(f"temp_video_{counter}.mp4", "wb") as f:
                f.write(video_data)
            url_list.append(f"temp_video_{counter}.mp4")
    
    ## url毎に特徴を取得する。
    raw_text = []
    if len(url_list) == 0:
        st.write("取得した動画が0件のため、処理終了")
        return 0
    st.info("動画解析開始")
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
    st.info("全体分析開始")
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



def show_form_page():
    placeholder = st.empty()
    with placeholder.container():
        st.title("要件入力フォーム")
        st.write("動画分析設定")
        serch_type = st.selectbox("検索するコンテンツのの種類を選んでください。", ["reels", "投稿データ", "コメント"])
        serch_num =st.text_input("再生回数は何回以上の動画に絞り込みますか。")
        serch_genre = st.text_input("分析したい動画のジャンルを入力してください。")
        
        st.write("台本設定")    
        senario_genre = st.text_input("作成する台本のジャンルを入力。")
        senario_stringnum = st.text_input("台本の文字数を入力。")
        senario_pattern = st.text_input("台本のパターン数を入力。")
        
        if st.button("既存の画面へ遷移"):
            st.session_state.analysis_contants = serch_type
            st.session_state.analysis_numbers = serch_num
            st.session_state.analysis_genre = serch_genre
            st.session_state.scenario_genre = senario_genre
            st.session_state.scenario_stringnum = senario_stringnum
            st.session_state.scenario_pattern = senario_pattern
            
            st.session_state.page = 'main'
            st.rerun() # 画面を再描画して切り替える)

def show_main_page():
    container = st.chat_message("assistant")
    try:
        # AI返信を生成・表示
        with container:
            with st.spinner("AIが考え中..."):
                ## 最初の分岐。0：動画分析セクション。1：台本作成セクション
                response = identifyUserNeeds(st.session_state.analysis_contants, st.session_state.analysis_numbers, st.session_state.analysis_genre)
                st.write(response)
        
        # ユーザー入力フォーム
        if prompt := st.chat_input("メッセージを入力してください...",key="input_1"):
            # ユーザー入力を追加
            with st.chat_message("user"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.markdown(prompt)

            
        # クリアボタン
        if st.button("会話クリア", use_container_width=True, key="clear_button"):
            st.session_state.messages = []
            st.rerun()
        # 戻るボタン（任意）
        if st.button("フォームに戻る"):
            st.session_state.page = 'form'
            st.rerun()
    except Exception as e:
        st.write(e)
        st.stop()


def setup_app():
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
    # セッション状態の初期化
    if 'page' not in st.session_state:
        st.session_state.page = 'form'
    if 'user_input' not in st.session_state:
        st.session_state.user_input = ""
    if 'analysis_contants' not in st.session_state:
        st.session_state.analysis_contants = ""
    if 'analysis_numbers' not in st.session_state:
        st.session_state.analysis_numbers = ""
    if 'analysis_genre' not in st.session_state:
        st.session_state.analysis_genre = ""
    if 'scenario_genre' not in st.session_state:
        st.session_state.scenario_genre = ""
    if 'scenario_stringnum' not in st.session_state:
        st.session_state.scenario_stringnum = ""
    if 'scenario_pattern' not in st.session_state:
        st.session_state.scenario_pattern = ""
    
    # ★ 修正ポイント：ページ全体の入れ物を作る
    main_placeholder = st.empty()

    # ★ container の中で各ページを呼び出す
    with main_placeholder.container():
        if st.session_state.page == 'form':
            show_form_page()
        elif st.session_state.page == 'main':
            show_main_page()

def display_chat_history():
    # 過去の会話を表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

#load_dotenv()
googleKey = st.secrets['GOOGLE_API_KEY']
genai_client = genai.Client(api_key=googleKey)
setup_app()
display_chat_history()