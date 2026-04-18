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

#台本作成エージェント
def senarioAgent(input):
    prompt = f"""
    # 目的
    Instagramで現在バズっている動画の特徴を反映し、指定されたジャンルで視聴者の維持率が高いショート動画の台本を{int(st.session_state.scenario_pattern)}件作成してください。

    # インプット情報
    1. 分析されたトレンドの特徴:
    {input}

    2. ターゲットジャンル: {st.session_state.scenario_genre}
    3. 文字数目安（1本あたり）: {st.session_state.scenario_stringnum}文字程度
    4. 作成パターン数: {int(st.session_state.scenario_pattern)}パターン

    # 台本構成ルール
    各パターン、以下の構成で作成してください。
    - 【フック（0-3秒）】: 思わず手を止める強烈な一言 or 問いかけ
    - 【ボディ（内容）】: テンポよく情報を伝える。1文を短く。
    - 【オチ / CTA（最後）】: 感想を促す問いかけ or プロフィールへの誘導

    # 出力形式
    以下のフォーマットで出力してください。

    ---
    ### パターン1：[パターンのコンセプト]
    【動画の全体イメージ】
    （BGMの雰囲気、カット割りの頻度など）

    【台本テキスト】
    （ここに指定文字数で台本を記述）

    【編集のポイント】
    （トレンド分析に基づいた、文字入れのタイミングやエフェクトの指示）
    ---
    （指定されたパターン数分繰り返し）
    """
    for attempt in range(2):
        try:
            status = 0
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            requestresponse_text = response.text
            st.write(f"分析結果：{requestresponse_text}")                
            return requestresponse_text
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"            
           
    return "AIの応答を生成できませんでした。"

#yes/noジャッジエージェント
def jadgeAgent(userImput):
    prompt = f"""
        下記のユーザーインプットが肯定(はい)しているか、否定(いいえ)しているかを判定してほしいです。
        肯定の場合は"YES"を返してください。
        否定の場合は"NO"を返してください。
        返答は上記どちらかの文字列のみにしてください。

        # ユーザーの入力
        {userImput}
    """
    raw_text = ""
    for attempt in range(2):
        try:           
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_text = response.text
            st.session_state.messages.append(raw_text)
            break
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"
    return raw_text

#ユーザー聞き取り関数
def identifyUserNeeds(type, play_num, analysis_genre):
    apifyApiKey = st.secrets["APIFY_API"]
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
            st.write(F"中身のデバッグ：{raw_text}")
            break
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"

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
        # 役割
        あなたは、TikTok、YouTubeショート、Instagramリール等のショート動画において、数百万再生を連発させる「プロの動画分析クリエイター」です。

        # 依頼
        送付した動画を詳細に分析し、この動画が視聴者を惹きつけ、拡散される理由を以下の構成要素に沿って【秒数（タイムスタンプ）付き】で解説してください。

        # 分析の必須項目
        1. **動画の基本情報**
        - 動画の総時間、テンポ感（BPMやカット割りの頻度）
        2. **構成要素のタイムライン分析**
        - 【フック（0〜3秒）】：冒頭でどのように視聴者の指を止めたか？（視覚的衝撃、共感、問いかけ等）
        - 【リードの導入】：本編へ繋げるための期待感をどう醸成しているか？
        - 【本編】：視聴者が離脱しないための情報の出し方や、盛り上がりの作り方。
        - 【コールトゥアクション（CTA）】：視聴者にどのようなアクション（保存、共有、フォロー等）を促しているか。
        3. **バズる理由の多角的推測**
        - 視聴維持率を高めるための編集の工夫（テロップ、SE、エフェクト）
        - ターゲット層の心理をどう突いているか
        - アルゴリズムに評価されやすいポイント（ループ性、コメントの誘発等）

        # 出力形式
        ## 1. 全体概要
        （動画の第一印象と成功の核心を短文で記載）

        ## 2. タイムライン詳細解説
        - **00:00 - 00:0X [フック]**: 
        - **00:0X - 00:0X [リード]**: 
        - **00:0X - 00:0X [本編]**: 
        - **00:0X - 終了 [CTA]**: 

        ## 3. クリエイターの視点：なぜ流行るのか？
        - **視覚/聴覚的戦略**: 
        - **心理的トリガー**: 
        - **真似できるポイント**:
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
    # 役割
    あなたは、100万再生超えのヒット動画を数千本分析してきた「コンテンツ・データサイエンティスト」です。
    複数の動画分析データから、表面的な感想を排除し、統計的に有意な「共通の成功法則（ギミック）」を抽出してください。

    # 目的
    入力された複数の分析結果を横断的に比較し、どの動画にも共通して組み込まれている「バズの構造」を特定する。

    # 分析の固定軸（以下の5つの角度からのみ出力してください）
    1. 【0.5秒の視覚的フック】
    - 最初の1秒未満で、脳をどう刺激しているか。共通する視覚効果や構図。
    2. 【情報の「引き算」と「密度」】
    - あえて説明を省いている点や、カット割りのスピード感に共通するルールはあるか。
    3. 【コメント誘発（ツッコミどころ）の設計】
    - 視聴者が思わず書き込みたくなる「違和感」や「議論の火種」がどう共通して仕込まれているか。
    4. 【聴覚的トリガー】
    - BGMの切り替えタイミング、SE（効果音）の入れ方、ナレーションの抑揚の共通点。
    5. 【視聴完了を促す心理的報酬】
    - 最後にどのような「カタルシス」や「意外性」を配置しているか。

    # 出力形式
    ## 1. 共通する黄金パターン（サマリー）
    （分析した動画群に共通する最大公約数的な構造を1文で定義）

    ## 2. 構造的特徴量の詳細（5つの軸に基づき解説）
    - **視覚的共通点**:
    - **構成/テンポの共通点**:
    - **心理的仕掛けの共通点**:

    ## 3. 即導入可能な「バズのチェックリスト」
    （今回の分析結果から導き出された、次の動画制作で必ず守るべき項目を箇条書きで）

    # 動画分析文
    {raw_text}
    """
    response = ""
    for attempt in range(5):
        try:           
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            #st.write(response.text)
            st.session_state.messages.append(response.text)
            break
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                #return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"
                break
    return response

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
        analysis = ""
        # AI返信を生成・表示
        with container:
            with st.spinner("AIが考え中..."):
                if st.session_state.transitionState == 0:
                    ## 最初の分岐。0：動画分析セクション。1：台本作成セクション
                    analysis = identifyUserNeeds(st.session_state.analysis_contants, st.session_state.analysis_numbers, st.session_state.analysis_genre)
                    st.write(f"分析結果は：{analysis}")
                    st.write(f"##この分析結果で台本作成をしますか？")                    
            
                    # ユーザー入力フォーム
                    if prompt := st.chat_input("メッセージを入力してください...",key="input_1"):
                        re = jadgeAgent(prompt)
                        if re == "YES":
                            container = st.empty()
                            st.rerun()
                            st.session_state.transitionState += 1
                        elif re == "NO":
                            st.warning("修正が必要な場合は、要件入力フォームからやり直してください。")
                        
                if st.session_state.transitionState == 1:
                    response = senarioAgent(analysis)
                    st.write(response)
                    

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
googleKey = st.secrets["GOOGLE_API_KEY"]
genai_client = genai.Client(api_key=googleKey)
setup_app()
#display_chat_history()