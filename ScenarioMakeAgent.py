from dotenv import load_dotenv
import streamlit as st
from google import genai
import time
import json
import random
import os

def MakeScenario(analysisText):
    # context = ""
    # for msg in history_text:
    #     role = "ユーザー" if msg["role"] == "user" else "AI"
    #     context += f"{role}: {msg['content']}\n"
    
    system_instruction = """
    # Role
    あなたは、InstagramやTikTokで数百万再生を連発する、超一流のショート動画クリエイター兼ディレクターです。
    提供された「動画分析データ」を元に、その成功パターン（勝てるロジック）を完全に継承した、新しいオリジナル動画の台本を作成してください。

    # Task
    1. 新しい動画のテーマを、分析結果の「改善・差別化のヒント」に基づいて1つ選定してください。
    2. そのテーマに沿って、15〜30秒のショート動画台本を制作してください。
    3. 台本は、以下の「構成フォーマット」に従って詳細に記述してください。

    # Constraints (厳守事項)
    分析結果に基づき、以下の数値をロジックに組み込むこと：
    - **冒頭フック:** 1.5秒以内に視覚的衝撃を与え、10-30文字のテロップで「知らなきゃ損」と思わせる。
    - **テンポ:** 10秒間に3〜5カットの切り替え。1要素につき2〜5秒で完結させる。
    - **視覚階層:** 重要情報のテロップはデザインとフォントの強弱を明確にする。
    - **音響戦略:** 効果音（SE）のピークをBGMより高く設定し、盛り上がり（Swell）を作る。
    - **視聴者維持:** Before/Afterの対比を明確にし、最後に「保存」や「コメント」を促す仕掛けを入れる。

    # Output Format
    ## 1. コンセプト案
    - **ターゲット:** - **選定したテーマ:** - **視聴者が得るベネフィット:** ## 2. 制作絵コンテ（タイムライン形式）
    | 秒数 | 映像（背景・動き） | テロップ内容（配置/演出） | 音響（BGM/SE） | ナレーション |
    | :--- | :--- | :--- | :--- | :--- |
    | 0-3s | [例]鮮やかな実演映像 | 【15文字以内のフック】 | アップテンポ開始/衝撃音 | 「これ、マジで凄いです」 |
    | ... | ... | ... | ... | ... |

    ## 3. 編集への指示書
    - **色味・トーン:** - **フォント・アニメーション:** - **視聴者参加型の仕掛け（問いかけ内容）:** # Response
    日本語で、具体的かつプロフェッショナルなトーンで出力してください。
    """
    
    prompt = f"""
    {system_instruction}

    ---
    # Input Data: 動画分析結果
    {analysisText}
    """
    
    for attempt in range(2):
        try:
            status = 0
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_text = response.text
                
            return raw_text
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"
            
    return "AIの応答を生成できませんでした。"

def captureMarketVibe(history_text):
    context = ""
    for msg in history_text:
        role = "ユーザー" if msg["role"] == "user" else "AI"
        context += f"{role}: {msg['content']}\n"
    
    system_instruction = """
    # Role
    あなたは、SNS（Instagram, TikTok等）の戦略立案に特化したデータアナリスト兼エンジニアです。

    # Task
    ユーザーとの対話ログを徹底的に分析し、そのジャンルで勝つための「攻略ガイド」をJSON形式で構造化してください。

    # Guidelines for JSON Generation
    1. **動的なスキーマ生成**: 
    固定のフォーマットに縛られないでください。ユーザーが「編集のコツ」を重視していれば編集に特化した階層を、「マネタイズ」を気にしていれば収益化の項目を、対話の内容に合わせて動的に生成してください。
    2. **階層構造の最適化**: 
    情報をフラットに並べるのではなく、関連する項目をネスト（階層化）して整理してください。
    3. **定量的・定性的の両立**: 
    「秒数」や「頻度」などの具体的な数値と、「世界観」「トーン」などの感性的な要素をバランスよく含めてください。
    4. **エンジニアリングへの配慮**: 
    このJSONをそのまま動画制作AIのプロンプトや、ダッシュボードの表示データとして利用可能な、論理的で明確なキー名（キャメルケースやスネークケース）を使用してください。
    """
    
    prompt = f"""
    {system_instruction}

    ---
    ### ユーザーからの要望(やり取り)
    {context}

    ### システムからの指示
    上記の対話を踏まえ、ユーザーの望む動画を分析するためのjsonを出力してください。
    """
    
    json_text = ""
    for attempt in range(2):
        try:
            status = 0
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            json_text = response.text
            st.write(f"出力物：{json_text}")                
            break
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"            
                
    prompt = f"""
    # Role
    あなたはSNS（Instagram/TikTok）のバズ動画を量産する「ヒット動画の演出家」です。
    難しい専門用語は使わず、動画制作の経験がない人でも「明日から真似できる！」と思えるほど具体的で分かりやすい言葉で、動画の構造を解剖します。

    # Input
    1. 分析定義データ (JSON)
    2. 対象動画のデータ (テキスト、映像説明、ハッシュタグ等)

    # Task
    視聴者が「ついつい最後まで見てしまった理由」を、以下の5ステップで分析してください。

    1. **ツカミの3秒（フック）**: 
    スマホをスクロールする指を止めさせた「最初の一言」や「最初の映像」の凄さを解説。
    2. **ストーリーの進め方（構成）**: 
    飽きさせないための情報の出し入れや、カットを切り替えるタイミングを解説。
    3. **見た目の工夫（視覚効果）**: 
    文字の大きさ、色、配置など「パッと見で内容が伝わる工夫」を解説。
    4. **音の効果（音響）**: 
    BGMの雰囲気や、音と映像がどうセットで感情を動かしているかを解説。
    5. **視聴者の心の動き（インサイト）**: 
    これを見た人がどんな気持ちになり、なぜ「保存」や「いいね」をしたくなったのかを分析。

    # Output Format
    新しい動画の「台本」の設計図になるように、以下の形式で出力してください。

    ### 1. この動画の「ここが天才！」（一言まとめ）
    - 誰に、どんな感情を届けたからバズったのか、キャッチコピー風に教えてください。

    ### 2. 真似できるポイント（構成要素の分解）
    | 項目 | 分析結果（初心者向け解説） |
    | :--- | :--- |
    | **映像の雰囲気** | (例: おしゃれなカフェ風の、少し暗めで落ち着いたトーン) |
    | **文字の出し方** | (例: 雑誌のタイトルみたいに、ドカンと真ん中に大きく出す) |
    | **音の役割** | (例: リズムに合わせてトントンと映像が変わる快感がある) |

    ### 3. 【台本に活かす】バズる仕掛けベスト3
    - 自分の動画を作る際に、そのままパクるべき具体的なテクニック。

    ### 4. もっと良くするための「ちょい足し」アイデア
    - もしあなたがこの動画をさらに伸ばすなら、どんな工夫を加えるか？（例：あと2秒短くする、最後に質問を入れる等）

    ---
    ### ユーザーからの要望
    {json_text}
    """
    for attempt in range(2):
        try:
            status = 0
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            requestresponse_text = response.text
            st.write(f"出力物：{requestresponse_text}")                
            return requestresponse_text
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return "申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？"            
           
    
    return "AIの応答を生成できませんでした。"

def setup_app(): 
    # ページ設定
    st.set_page_config(page_title="AIチャット", page_icon="🤖")
    st.title("🤖 AIチャット")

    # チャット履歴をセッション状態で保持（初回のみ実行）
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "transitionState" not in st.session_state:
        st.session_state.transitionState = -1
    if "log" not in st.session_state:
        st.session_state.log = []
    if "jsonList" not in st.session_state:
        st.session_state.jsonList = []

def display_chat_history():
    # 過去の会話を表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_chat():    
    # ユーザー入力フォーム
    if prompt := st.chat_input("メッセージを入力してください..."):
        # ユーザー入力を追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI返信を生成・表示
        with st.chat_message("assistant"):
            with st.spinner("AIが考え中..."):
                response = identifyUserNeeds(prompt, st.session_state.messages)
                response_text = response[0]
                if(response[1] == 0):
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
                    captureMarketVibe(st.session_state.messages)
                    st.markdown("処理終了。")
                    st.stop()

    # クリアボタン
    if st.button("会話クリア", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

load_dotenv()
googleKey = os.getenv('GOOGLE_API_KEY')
genai_client = genai.Client(api_key=googleKey)
setup_app()
display_chat_history()
handle_chat()