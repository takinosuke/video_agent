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
import unicodedata
import google.genai.types as types
import streamlit as st
import cloudinary
import cloudinary.uploader

# ページ設定
st.set_page_config(page_title="動画生成AI", page_icon="🤖")
st.title("🤖 動画生成AI")

def try_parse_method(input_string):
    try:
        result = unicodedata.normalize('NFKC', input_string)
        re = int(result)
        return re
    except:
        return 0

# 動画作成関数
def create_video():
    cloudinary.config(
        cloud_name = st.secrets["CLOUDINARY_NAME"],
        api_key = st.secrets["CLOUDINARY_API_KEY"],
        api_secret = st.secrets["CLOUDINARYSEECRET_API_KEY"],
        secure = True # HTTPSのセキュアなURLを発行する設定
    )
    st.title("Cloudinary 画像アップロードテスト")

    # 2. ファイルアップローダーの配置
    #uploaded_file = st.file_uploader("画像を選択してください", type=["jpg", "jpeg", "png"])
    uploaded_file = st.session_state.character_image[0]

    # if uploaded_file is not None:
    #     # アップロードされた画像を画面に表示
    #     st.image(uploaded_file, caption="選択された画像", width=300)
        
    #     # アップロードボタン
    #     if st.button("Cloudinaryにアップロード"):
    st.info("Cloudinaryへアップロード中...")
    
    try:
        # 🌟対策2: データの型（手動アップロードか、Gemini生成バイナリか）を判定して適切に処理
        if hasattr(uploaded_file, "getvalue"):
            # st.file_uploader から取得したオブジェクトの場合
            file_data = uploaded_file.getvalue()
        else:
            # すでに bytes 型データ（Gemini生成画像）の場合
            file_data = uploaded_file

        # Cloudinaryへバイナリデータを送信
        upload_result = cloudinary.uploader.upload(file_data)
        # 4. レスポンスから公開URL（直リンク）を抽出
        # secure_url を使うことで「https://...」から始まる安全なURLが取得できます
        public_url = upload_result.get("secure_url")
        
        st.success("アップロードが成功しました！")
        st.write("---")
        st.write("**生成された公開URL（D-IDに渡すURL）:**")
        st.code(public_url)
        
        # テストとして、発行されたURLを使って画像を表示してみる
        st.image(public_url, caption="Cloudinaryから読み込んだ画像", width=300)
        
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
    
    did_format = """
    {
        "script": {
            "type": "text",
            "provider": {
                "type": "microsoft",
                "voice_id": "ja-JP-NanamiNeural"
            },
            "input": "ここに台本が入ります"
        },
        "source_url": "https://example.com/image.jpg",
        "config": {
            "fluent": "false",
            "pad_audio": "0.1",
            "stitch": true
        }
    }
    """

    prompt = f"""
    あなたはD-IDのAPI連携を行うシステムです。
    提供された「台本」と「画像URL」をもとに、D-IDの `/talks` エンドポイントへ送信するための有効なJSONデータを作成してください。
    パターンは1を使用するようにしてください。

    # 制約ルール
    1. **文字数制限（上限300文字）**:
    - `input` に格納するテキストは、改行やスペースを含めて【必ず300文字以内】としてください。
    - 提供された台本が300文字を超える場合は、文脈を維持したまま、300文字以内に収まるよう内容を整えてください。301文字以上の出力は不可とします。

    2. **音声合成（TTS）向けのテキスト処理**:
    - 「〇」などの伏字は、音声エラーを防ぐため適切な言葉（例: 「数万円」「なになに」など）に置き換えるか削除してください。
    - 「1%」は「1パーセント」、「NISA」は「ニーサ」のように、英語や記号は読み通りのカタカナや日本語に変換してください。
    - 「1つ目」「3つ」などの表記は、「ひとつ目」「みっつ」のようにひらがなに変換してください。

    3. **出力形式**:
    - 出力は、提供された「出力フォーマット」の構造に従った純粋なJSONデータのみとしてください。
    - マークダウンの ```json などの囲み、および前後の解説テキストは一切含めないでください。

    # 入力データ
    ### 台本
    {st.session_state.scenario_export}

    ### 画像URL
    {public_url}

    # 出力フォーマット
    {did_format}
    """
    raw_text = ""
    for attempt in range(2):
        try:           
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            raw_text = response.text
            st.session_state.messages.append(raw_text)
            # --- トークン計測の追加 ---
            usage = response.usage_metadata
            st.info(f"消費トークン - 入力: {usage.prompt_token_count}, 出力: {usage.candidates_token_count}, 合計: {usage.total_token_count}")
            st.session_state.gemini_input_token += usage.prompt_token_count
            st.session_state.gemini_output_token += usage.candidates_token_count
            st.session_state.gemini_total_token += usage.total_token_count
            # -----------------------
            break
        
        except Exception as e:
            st.write("exceptionに入った。")
            st.write(e)
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"
    #return raw_text
    st.write(f"""D-idに渡すJSONは：{raw_text}""")
    st.write("D-id処理開始")
    DID_API_KEY = st.secrets["DID_API_KEY"]
    # 1. 動画生成をリクエストする（POST）
    URL_POST = "https://api.d-id.com/talks"
    HEADERS = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Basic {DID_API_KEY}"
    }
    PAYLOAD = json.loads(raw_text)
    # --------------------------------------------------
    # ステップ 1: 動画生成ジョブの作成
    # --------------------------------------------------
    print("D-ID に動画生成リクエストを送信中...")
    response = requests.post(URL_POST, json=PAYLOAD, headers=HEADERS)

    if response.status_code != 201:
        print(f"エラーが発生しました (Status Code: {response.status_code})")
        print(response.text)
        st.write(f"エラーが発生しました (Status Code: {response.status_code})")
        st.write(response.text)
        exit()

    res_data = response.json()
    talk_id = res_data.get("id")
    print(f"ジョブが作成されました。Talk ID: {talk_id}")

    # --------------------------------------------------
    # ステップ 2: 動画の生成完了を待つ（ポーリング）
    # --------------------------------------------------
    URL_GET = f"https://api.d-id.com/talks/{talk_id}"
    print("動画の生成完了を待っています...")
    st.write("動画生成完了待ち中")

    while True:
        get_response = requests.get(URL_GET, headers=HEADERS)
        
        if get_response.status_code != 200:
            print(f"ステータス取得エラー: {get_response.text}")
            break
            
        status_data = get_response.json()
        status = status_data.get("status")
        print(f"現在のステータス: {status}")
        st.toast(f"現在のステータス: {status}")
        
        if status == "done":
            result_url = status_data.get("result_url")
            
            # 【変更】print から st.success に変更（画面に成功メッセージを出すため）
            st.success("🎉 動画の生成が完了しました！")
            
            # 【追加】作成された動画を Streamlit 画面に表示するプレイヤーを追加
            st.video(result_url)
            break
        
        elif status == "error":
            print("\n❌ 動画の生成中にエラーが発生しました。")
            print(status_data)
            break
            
        # 5秒待ってから再確認
        time.sleep(5)

# 画像生成関数    
def create_image():
    prompt = F"""
    {st.session_state.character_make}, {st.session_state.character_sex}, {st.session_state.character_tribe}, {st.session_state.character_hairstyle}, {st.session_state.character_haircolors}, {st.session_state.character_eyeshape}, {st.session_state.character_eyecolors}, {st.session_state.character_other}, {st.session_state.character_location}, {st.session_state.character_environment}, {st.session_state.character_touch}, {st.session_state.character_tone}
    """      
    #response = safe_generate_content(prompt)

    # 最低限のクールダウン
    time.sleep(5)
    
    image_response = genai_client.models.generate_images(
        model='models/imagen-4.0-fast-generate-001',
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
        )
    )
    # このセクションの4枚を配列に格納
    section_images_list = []
    # 4枚すべてを表示
    for i, img in enumerate(image_response.generated_images):
        img_data = img.image.image_bytes
        st.image(img_data, caption=f"Generated Image {i+1}", use_container_width=True)
        # 画像オブジェクトを配列に追加（Gemini用）
        section_images_list.append(img.image)
        st.session_state.character_image.append(img_data)

#台本作成エージェント
def senarioAgent(input):
    prompt = f"""
    # 目的
    Instagramの最新トレンド（アルゴリズム・編集スタイル）を網羅し、視聴維持率を最大化させるショート動画の台本を {int(st.session_state.scenario_pattern)} 件作成してください。
    特に、最初の3秒で離脱させない「強烈な引き」と、最後まで飽きさせない「0.5秒単位の画面構成」を意識してください。

    # インプット情報
    1. 分析されたトレンドの特徴:
    {input}

    2. ターゲットジャンル: {st.session_state.scenario_genre}
    3. 作成パターン数: {int(st.session_state.scenario_pattern)} パターン

    # 台本構成・演出ルール
    各台本は、以下の構成に沿って作成してください。
    1. 【フック（0-3s）】: 冒頭0.1秒で視覚・聴覚的インパクトを与え、指を止めさせる。
    2. 【展開・ボディ（3-25s）】: 1.5秒〜2秒に一度は必ず「画角（ズーム）」や「テロップ」を切り替える。
    3. 【結末・CTA（25-30s）】: 「保存」や「コメント」を促す心理的トリガーを組み込む。

    # 出力形式（厳守ルール）
    - 表の中では <br> や \n などの**マークアップ・改行タグは一切使用しないでください**。
    - 1つのセルに情報を詰め込みすぎず、展開が変わるごとに「行（列）」を分けて記載してください。
    - 専門用語は避け、動画編集の素人でもパッと見て映像が浮かぶ言葉を使ってください。

    ---
    ### パターン[番号]：[キャッチコピー的なコンセプト名]

    【動画の全体戦略】
    （なぜこの構成が今のトレンドに刺さるのか、狙いを記述）

    【詳細タイムライン台本】
    | 秒数 | 音声（ナレーション/セリフ） | 映像・演出（動きや画面の変化） | テロップ（表示させる文字） |
    | :--- | :--- | :--- | :--- |
    | 00-01s | [セリフ] | [どんな顔・どんな動きか] | [短い言葉] |
    | 01-03s | ... | ... | ... |
    | 03-05s | ... | ... | ... |
    | （以下、5秒単位ではなく、展開の切り替わりごとに細かく行を追加） |

    【編集の極意】
    - BGMの選定: （曲調やタイミング）
    - フォント・配色: （見やすい色の組み合わせ）
    - 離脱防止のアドバイス: （ループ率を上げるための具体的な工夫）
    ---
    """
    for attempt in range(2):
        try:
            status = 0
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            requestresponse_text = response.text
            # --- トークン計測の追加 ---
            usage = response.usage_metadata
            st.info(f"消費トークン - 入力: {usage.prompt_token_count}, 出力: {usage.candidates_token_count}, 合計: {usage.total_token_count}")
            st.session_state.gemini_input_token += usage.prompt_token_count
            st.session_state.gemini_output_token += usage.candidates_token_count
            st.session_state.gemini_total_token += usage.total_token_count
            # -----------------------
            st.session_state.scenario_export = requestresponse_text
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
            # --- トークン計測の追加 ---
            usage = response.usage_metadata
            st.info(f"消費トークン - 入力: {usage.prompt_token_count}, 出力: {usage.candidates_token_count}, 合計: {usage.total_token_count}")
            st.session_state.gemini_input_token += usage.prompt_token_count
            st.session_state.gemini_output_token += usage.candidates_token_count
            st.session_state.gemini_total_token += usage.total_token_count
            # -----------------------
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
            #st.write(F"中身のデバッグ：{raw_text}")
            print(F"中身のデバッグ：{raw_text}")
            # --- トークン計測の追加 ---
            usage = response.usage_metadata
            st.info(f"消費トークン - 入力: {usage.prompt_token_count}, 出力: {usage.candidates_token_count}, 合計: {usage.total_token_count}")
            st.session_state.gemini_input_token += usage.prompt_token_count
            st.session_state.gemini_output_token += usage.candidates_token_count
            st.session_state.gemini_total_token += usage.total_token_count
            # -----------------------
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

    print(f"抽出後：{keyword_list}")

    keywords = [f"https://www.instagram.com/explore/tags/{key}/" for key in keyword_list]
    print(f"{keywords}")

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
    for item in client.dataset(run.default_dataset_id).iterate_items():
        counter += 1
        # video_list.append({
        #     "url": item.get("url"),
        #     "video_url": item.get("videoUrl"),
        #     "caption": item.get("caption"),
        #     "likes": item.get("likesCount")
        # })
        print(f"videUrlは：{item.get('videoUrl')}")
        print(f"urlは：{item.get('url')}")
        print(f"typeは：{item.get('type')}")
        print(f"回数は：{item.get('videoPlayCount')}")
        print(f"回数は：{item.get('videoViewCount')}")
        print(f"回数は：{item.get('viewCount')}")
        print(f"回数は：{item.get('playCount')}")
        views = item.get("videoPlayCount") or item.get("videoViewCount") or 10000
        print(f"視聴回数は：{views}")
        #消費トークンの取得
        run_handle = client.run(run.id)
        run_details = run_handle.wait_for_finish()
        time.sleep(2)
        # 消費された計算リソース(CU)を取得
        if run_details.stats:
            usage_ori = run_details.stats.compute_units
        else:
            usage_ori = 0
        st.write(usage_ori)
        # Streamlitのセッション状態に加算
        st.session_state.apify_token += usage_ori
        print(f"今回のApify消費リソース: {usage_ori} CU")
        if views >= int(play_num):            
            # 1. 動画を一時的に保存
            video_data = requests.get(item.get("videoUrl")).content
            with open(f"temp_video_{counter}.mp4", "wb") as f:
                f.write(video_data)
            url_list.append(f"temp_video_{counter}.mp4")
    
    ## url毎に特徴を取得する。
    raw_text = []
    if len(url_list) == 0:
        print("取得した動画が0件のため、処理終了")
        return 0
    st.info("動画解析開始")
    for item in url_list:
        with open(item, "rb") as f:
            # 動画をアップロード（Apifyで落としたファイル）
            video_file = genai_client.files.upload(file=f, config={'mime_type': 'video/mp4'})
        
        # アップロード直後
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai_client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED":
            st.write("失敗しました。")
            raise ValueError("Video processing failed.")

        prompt = f"""
        # 役割
        あなたは動画の1フレーム単位で「視聴維持率」と「離脱ポイント」を特定する、超精密動画アナリストです。
        送付された動画を0.1秒単位でスキャンし、以下の【厳格なフォーマット】に従って分析結果を出力してください。

        # 必須条件
        1. 必ず「00:00」からのタイムスタンプを付けてください。
        2. 各構成要素（フック・リード・本編・CTA）を明確に区切ってください。
        3. 推測ではなく、実際に映像に映っている「テロップの内容」「スピーカーの発話」「画面の切り替わり」をベースに分析してください。

        # 分析・出力形式（この通りに出力すること）

        ## 1. タイムライン解剖
        - **【00:00 - 00:0X】フック（冒頭の掴み）**
          - **内容**: （例：画面いっぱいの札束と「年収1000万の真実」という赤文字テロップ）
          - **心理的効果**: なぜ視聴者はここで指を止めるのか？
        - **【00:0X - 00:0X】リードの導入（期待感）**
          - **内容**: （例：問いかけや「知らないと損する理由3選」などの宣言）
          - **心理的効果**: 続きを見る「ベネフィット」をどう提示しているか。
        - **【00:0X - 00:0X】本編（価値提供）**
          - **内容**: 具体的な解説やストーリーの展開。
          - **ギミック**: 飽きさせないための「画面の切り替わり頻度」や「SEのタイミング」。
        - **【00:0X - 終了】コールトゥアクション（CTA）**
          - **内容**: （例：プロフィール誘導、保存の促し）
          - **心理的効果**: なぜ今、そのアクションが必要だと感じさせるのか。

        ## 2. 定量的特徴
        - **総再生時間**: [数字]秒
        - **平均カット割りの速さ**: 約[数字]秒に1回
        - **テロップの密度**: 低・中・高

        ## 3. 全体評価：なぜバズるのか
        - **情報の凝縮度**: 無駄な「間」がどこに排除されているか。
        - **ループ性**: 最後から最初へどう繋がっているか（無限ループの有無）。
        """        
        for attempt in range(5):
            try:           
                response = genai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[prompt, video_file]
                )
                print(response.text)
                raw_text.append(response.text)
                # --- トークン計測の追加 ---
                usage = response.usage_metadata
                st.info(f"消費トークン - 入力: {usage.prompt_token_count}, 出力: {usage.candidates_token_count}, 合計: {usage.total_token_count}")
                st.session_state.gemini_input_token += usage.prompt_token_count
                st.session_state.gemini_output_token += usage.candidates_token_count
                st.session_state.gemini_total_token += usage.total_token_count
                # -----------------------
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
    あなたは、100万再生超えのヒット動画を数千本、フレーム単位で時系列解析してきた「コンテンツ・データサイエンティスト」です。
    複数の動画分析データから、単なる共通点ではなく「何秒目に、どの強度の刺激が配置されているか」という【時間軸の黄金比】を抽出してください。

    # 目的
    入力された複数の分析結果を横断的に比較し、視聴維持率を最大化させるための「タイムライン・ストラクチャー（時間構造）」を特定する。

    # 分析の固定軸
    1. 【秒単位の離脱阻止（リテンション・カーブ分析）】
    2. 【カット割りと情報の平均サイクル】
    3. 【感情のピークタイム】
    4. 【音響のスイッチング・タイミング】
    5. 【終盤のCTA（誘導）への移行秒数】

    # 出力形式

    ## 1. タイムライン・ヒートマップ（共通秒数）
    分析結果から導き出された共通のイベント発生タイミングを、以下の表形式で整理してください。
    ※セル内での改行タグ（<br>等）は使用せず、項目ごとに「行」を分けて記述してください。

    | 時間帯（秒） | フェーズ名 | 発生させるべきイベント・特徴 | 具体的な演出例 |
    | :--- | :--- | :--- | :--- |
    | 00-01s | 指止めフック | [視覚的・聴覚的インパクトの内容] | [具体的なアクション] |
    | 01-05s | 期待値の具体化 | [視聴継続を決意させる情報の提示] | [具体的な演出] |
    | 05-15s | テーマの確立 | [価値提供への誘導・問題提起] | [具体的な演出] |
    | 15-25s | 本編・核心 | [メインコンテンツの展開] | [具体的な演出] |
    | 終盤 | クライマックス | [最大の盛り上がり・オチ] | [SEやBGMの変化] |
    | ラスト | CTA・ループ | [次の行動誘導・余韻の設計] | [テロップや誘導文] |

    ## 2. 定量的な構造パラメーター
    - **平均情報更新頻度**: [数字]秒に1回（テロップや画面切替）
    - **結論提示のタイミング**: 開始[数字]秒時点 / 全体の[数字]%地点
    - **テンポの推移**: （例：前半は0.8秒刻み、中盤は1.5秒、後半に再度加速など）

    ## 3. 即導入可能な「秒単位の制作指示書」
    動画制作にそのまま使える指示を、以下の表形式で整理してください。

    | タイミング | 指示内容 | 狙い（心理的効果） | 編集上の注意点 |
    | :--- | :--- | :--- | :--- |
    | 0秒地点 | [必須フック] | [なぜこれが必要か] | [フォント・音の指定] |
    | 3秒地点 | [追いフック] | [離脱を防ぐロジック] | [画面構成の指定] |
    | 15秒以降 | [情報の小出し] | [飽きさせない工夫] | [カット割りのテンポ] |
    | ラスト | [アクション誘導] | [視聴者に何をさせるか] | [ループや遷移の工夫] |

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
            # --- トークン計測の追加 ---
            usage = response.usage_metadata
            st.info(f"消費トークン - 入力: {usage.prompt_token_count}, 出力: {usage.candidates_token_count}, 合計: {usage.total_token_count}")
            st.session_state.gemini_input_token += usage.prompt_token_count
            st.session_state.gemini_output_token += usage.candidates_token_count
            st.session_state.gemini_total_token += usage.total_token_count
            # -----------------------
            break
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                #return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"
                break
    return response.text

def show_form_page():
    placeholder = st.empty()
    with placeholder.container():
        st.title("要件入力フォーム")
        st.write("動画分析設定")
        serch_make = st.selectbox("動画分析が必要かどうか。", ["分析する", "分析しない"])
        serch_visivleFlag = (serch_make == "分析しない")
        serch_type = st.selectbox("検索するコンテンツのの種類を選んでください。", ["reels", "投稿データ", "コメント"], disabled = serch_visivleFlag)
        serch_num =st.text_input(label="再生回数は何回以上の動画に絞り込みますか。", placeholder="例：10000", disabled = serch_visivleFlag)
        serch_genre = st.text_input(label="分析したい動画のジャンルを入力してください。", placeholder="例：エンタメ系", disabled = serch_visivleFlag)
        
        st.write("台本設定")
        senario_make = st.selectbox("台本の作成が必要かどうか。", ["作成する", "作成しない"])
        senario_visivleFlag = (senario_make == "作成しない" or serch_visivleFlag)
        senario_genre = st.text_input(label="作成する台本のジャンルを入力。", placeholder="例：技術系", disabled =senario_visivleFlag)
        #senario_stringnum = st.text_input("台本の文字数を入力。")
        senario_pattern = st.text_input(label="台本のパターン数を入力。", placeholder="例：2", disabled =senario_visivleFlag)
        
        st.write("キャラクター作成")
        character_make = st.selectbox("キャラクターの作成が必要かどうか。", ["作成する", "作成しない"])
        character_visivleFlag = (character_make == "作成しない")
        character_sex = st.selectbox("キャラクターの性別を選択してください。", ["男性", "女性", "その他"], disabled = character_visivleFlag)
        character_tribe = st.text_input(label="キャラクターの種族を入れてください。", placeholder="例：エルフ", disabled = character_visivleFlag)
        character_hairstyle = st.text_input(label="キャラクターのヘア-スタイルを入れてください。", placeholder="例：角刈り", disabled = character_visivleFlag)
        character_haircolors = st.text_input(label="キャラクターの髪の毛の色を入れてください。", placeholder="例：赤", disabled = character_visivleFlag)
        character_eyeshape = st.text_input(label="キャラクターの目の特徴を入れてください。", placeholder="例：つり目", disabled = character_visivleFlag)
        character_eyecolors = st.text_input(label="キャラクターの目の色を入れてください。", placeholder="例：青", disabled = character_visivleFlag)
        character_other = st.text_input(label="その他のキャラクターの特徴を入れてください。", placeholder="例：翼", disabled = character_visivleFlag)
        character_location = st.text_input(label="背景を入力してください。", placeholder="例：近未来都市", disabled = character_visivleFlag)
        character_environment = st.text_input(label="環境を入力してください。", placeholder="例：晴れた昼", disabled = character_visivleFlag)
        character_touch = st.text_input(label="画風を入力してください。", placeholder="例：アニメ風", disabled = character_visivleFlag)
        character_tone = st.text_input(label="全体のトーンを入力してください。", placeholder="例：明るくポップ", disabled = character_visivleFlag)
        
        st.write("動画作成")
        video_make = st.selectbox("動画の作成が必要かどうか。", ["作成する", "作成しない"])
        video_visivleFlag = (video_make == "作成しない")
        video_haveCharacter = st.selectbox("キャラクター画像を持っている", ["持っている", "持っていない"], disabled = video_visivleFlag)
        video_havesenario = st.selectbox("すでに台本を持っている", ["持っている", "持っていない"], disabled = video_visivleFlag)
        
        if st.button("既存の画面へ遷移"):
            st.session_state.analysis_flag = (serch_make == "分析する")
            st.session_state.analysis_contants = serch_type
            st.session_state.analysis_numbers = try_parse_method(serch_num)
            st.session_state.analysis_genre = serch_genre
            #台本作成設定の決定
            st.session_state.scenario_flag = (senario_make == "作成する" and st.session_state.analysis_flag)
            st.session_state.scenario_genre = senario_genre
            #st.session_state.scenario_stringnum = senario_stringnum
            st.session_state.scenario_pattern = try_parse_method(senario_pattern)
            # キャラクター設定の決定
            st.session_state.character_make = (character_make == "作成する")
            st.session_state.character_sex = character_sex
            st.session_state.character_tribe = character_tribe
            st.session_state.character_hairstyle = character_hairstyle
            st.session_state.character_haircolors = character_haircolors
            st.session_state.character_eyeshape = character_eyeshape
            st.session_state.character_eyecolors = character_eyecolors
            st.session_state.character_other = character_other
            st.session_state.character_location = character_location
            st.session_state.character_environment = character_environment
            st.session_state.character_touch = character_touch
            st.session_state.character_tone = character_tone
            #動画作成の決定
            st.session_state.video_make = (video_make == "作成する")
            st.session_state.video_haveCharacter = video_haveCharacter
            st.session_state.video_havesenario = video_havesenario
            
            st.session_state.page = 'main'
            st.rerun() # 画面を再描画して切り替える)

def show_main_page():
    container = st.chat_message("assistant")
    try:
        analysis = ""
        # AI返信を生成・表示
        with container:
            with st.spinner("AIが考え中..."):
                # 動画分析処理
                if st.session_state.transitionState == 0:
                    # 入力値が”分析しない場合は次の処理へ”
                    if st.session_state.analysis_flag == False:
                        st.session_state.transitionState += 1
                        st.rerun()
                    ## 最初の分岐。0：動画分析セクション。1：台本作成セクション
                    analysis = identifyUserNeeds(st.session_state.analysis_contants, st.session_state.analysis_numbers, st.session_state.analysis_genre)
                    st.session_state.analysisText = analysis          
                    st.session_state.transitionState += 1
                    st.rerun() # 画面を再描画して切り替える)
                # 分析結果から台本作成結果までの処理
                elif st.session_state.transitionState == 1:
                    # 入力にて台本作成を”作成しないにした場合は次の処理へ”
                    if st.session_state.scenario_flag == False:
                        st.session_state.transitionState += 2
                        st.rerun()
                    st.write(f"分析結果は：")
                    st.write(f"{st.session_state.analysisText}")
                    st.write(f"この分析結果で台本作成をしますか？")
                    # ユーザー入力フォーム
                    if prompt := st.chat_input("メッセージを入力してください...",key="input_1"):
                        st.write("ユーザー入力解析中")
                        container.empty()
                        re = jadgeAgent(prompt)
                        if re == "YES":
                            st.session_state.transitionState += 1
                            st.rerun()
                        elif re == "NO":
                            st.warning("修正が必要な場合は、要件入力フォームからやり直してください。")
                            st.session_state.transitionState = 0                            
                elif st.session_state.transitionState == 2:
                    contant = st.chat_message("sinario")
                    with contant:
                        st.success("台本を作成します...")
                        with st.spinner("台本執筆中..."):
                            response = senarioAgent(st.session_state.analysisText)
                            st.write(response)
                            
                            if st.button("キャラクタ作成へ", use_container_width=True, key="make_caractor"):
                                st.session_state.transitionState += 1
                                st.rerun()
                # キャラクター作成部分
                elif st.session_state.transitionState == 3:
                    if st.session_state.character_make == False:
                        st.session_state.transitionState += 1
                        st.rerun()
                    with st.spinner("キャラクター生成開始します..."):                    
                        create_image()
                        if st.button("動画作成へ進む。"):
                            st.session_state.transitionState += 1
                            st.rerun()
                # 動画作成部分
                elif st.session_state.transitionState == 4:
                    if st.session_state.video_make == False:
                        st.write("30秒後、フォーム画面に戻ります。")
                        time.sleep(30)
                        st.session_state.page == 'form'
                        st.rerun()
                    if len(st.session_state.scenario_export) <= 0:
                        userInputSenario = st.text_input("台本を入力してください。")
                    if st.session_state.character_image == []:
                        uploaded_file = st.file_uploader("画像をアップロードしてください", type=["jpg", "jpeg", "png"])
                        if st.button("実行", use_container_width=True, key="make_caractor"):
                            st.session_state.scenario_export = userInputSenario
                            st.session_state.character_image.append(uploaded_file)
                            st.rerun()
                    if len(st.session_state.scenario_export) != 0 and st.session_state.character_image != None:
                        with st.spinner("動画生成中・・・"):
                            create_video()
                        
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
        st.session_state.log = ""
    if "jsonList" not in st.session_state:
        st.session_state.jsonList = []
    if "analysisText" not in st.session_state:
        st.session_state.analysisText = ""
    # 入力トークン用
    if "gemini_input_token" not in st.session_state:
        st.session_state.gemini_input_token = 0
    # 出力トークン用
    if "gemini_output_token" not in st.session_state:
        st.session_state.gemini_output_token = 0
    # 合計トークン用
    if "gemini_total_token" not in st.session_state:
        st.session_state.gemini_total_token = 0
    # apifyトークン用
    if "apify_token" not in st.session_state:
        st.session_state.apify_token = 0
    # セッション状態の初期化
    if 'page' not in st.session_state:
        st.session_state.page = 'form'
    if 'user_input' not in st.session_state:
        st.session_state.user_input = ""
    #動画分析設定保存用
    if 'analysis_flag' not in st.session_state:
        st.session_state.analysis_flag = False
    if 'analysis_contants' not in st.session_state:
        st.session_state.analysis_contants = ""
    if 'analysis_numbers' not in st.session_state:
        st.session_state.analysis_numbers = ""
    if 'analysis_genre' not in st.session_state:
        st.session_state.analysis_genre = ""
    #台本作成設定保存用
    if 'scenario_flag' not in st.session_state:
        st.session_state.scenario_flag = False
    if 'scenario_genre' not in st.session_state:
        st.session_state.scenario_genre = ""
    if 'scenario_stringnum' not in st.session_state:
        st.session_state.scenario_stringnum = ""
    if 'scenario_pattern' not in st.session_state:
        st.session_state.scenario_pattern = ""
    if 'scenario_export' not in st.session_state:
        st.session_state.scenario_export = ""
    #キャラクター設定入力保存用
    if 'character_make' not in st.session_state:
        st.session_state.character_make = False
    if 'character_sex' not in st.session_state:
        st.session_state.character_sex = ""
    if 'character_tribe' not in st.session_state:
        st.session_state.character_tribe = ""
    if 'character_hairstyle' not in st.session_state:
        st.session_state.character_hairstyle = ""
    if 'character_haircolors' not in st.session_state:
        st.session_state.character_haircolors = ""
    if 'character_eyeshape' not in st.session_state:
        st.session_state.character_eyeshape = ""
    if 'character_eyecolors' not in st.session_state:
        st.session_state.character_eyecolors = ""
    if 'character_other' not in st.session_state:
        st.session_state.character_other = ""
    if 'character_location' not in st.session_state:
        st.session_state.character_location = ""
    if 'character_environment' not in st.session_state:
        st.session_state.character_environment = ""
    if 'character_touch' not in st.session_state:
        st.session_state.character_touch = ""
    if 'character_tone' not in st.session_state:
        st.session_state.character_tone = ""
    if 'character_image' not in st.session_state:
        st.session_state.character_image = []
    # 動画部分の変数
    if 'video_make' not in st.session_state:
        st.session_state.video_make = ""
    if 'video_haveCharacter' not in st.session_state:
        st.session_state.video_haveCharacter = ""
    if'video_havesenario' not in st.session_state:
        st.session_state.video_havesenario = ""
    
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