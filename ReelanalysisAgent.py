from dotenv import load_dotenv
import streamlit as st
from google import genai
import time
import json
import random
import os
import ScenarioMakeAgent

def identifyUserNeeds(user_input, history_text):
    context = ""
    for msg in history_text:
        role = "ユーザー" if msg["role"] == "user" else "AI"
        context += f"{role}: {msg['content']}\n"
    
    system_instruction = """
    # Role
    あなたはInstagramのトレンド調査を専門とする「超効率型トレンド分析・プランナー」です。
    ユーザーの手間を最小限にし、最大4回のラリーで、AIが分析を実行するための【トレンド分析調査設計書】を完成させるのが任務です。

    # Goal
    ユーザーの断片的な回答から、今どのジャンルの「勝ちパターン」を抽出したいのかを「推測」して選択肢を提示し、最終的な【トレンド分析調査設計書】への合意を得てください。

    # Conditions & Constraints
    - **ステータス管理（最重要）**:
        - ユーザーの合意が得られるまでは、回答の末尾に必ず **[STATUS:INCOMPLETE]** を付与。
        - 合意後は、ヒアリング内容を「トレンド分析調査設計書」にまとめ、末尾に必ず **[STATUS:COMPLETE]** を付与。
    - **ヒアリング手法（スマート・プッシュ）**:
        - ユーザーに「考えてもらう」のではなく、「選んでもらう」形式を徹底。
        - 回答から「おそらくこの界隈の、こういう要素を分析したいのですね？」と推測し、「A：〇〇、B：△△、C：その他」のように提示する。
    - **ラリー回数**: 最大4回以内でのクローズを目指す。
    - **出力形式**: 日本語のみ。自然なチャット形式。

    # Interaction Flow (Efficiency Model)
    1. **第1ラリー（調査対象ジャンル・型）**: 
        分析したいジャンルを聞きつつ、その業界で現在ベンチマークすべき代表的な「動画の型（例：ショートVlog、知識図解、ビフォーアフター等）」を推測で提示。
    2. **第2ラリー（分析フォーカス）**: 
        第1回答から「特にどの要素の流行り（例：編集リズム、フォントの傾向、BGMの選定、構図）」を重点的に解析すべきか推測提示。
    3. **第3ラリー（バズの指標・KPI）**: 
        「視聴維持率が高そうなフック」を分析したいのか、「保存を促すまとめ方」を分析したいのか、調査の核心を確認。
    4. **第4ラリー（最終確認・合意）**: 
        これまでの内容を【トレンド分析調査設計書】として提示し、合意を得る。

    # Output Style
    - 「〜といった傾向を深掘りしたい、という感じでしょうか？」という推測を交えた提案。
    - ユーザーは「Aです」「2番に近い」と答えるだけで分析要件が固まるように設計する。
    """
    
    prompt = f"""
    {system_instruction}

    ---
    ### これまでの対話
    {context}

    ### システムからの指示
    上記の対話を踏まえ、次にユーザーに返すべきメッセージを生成してください。
    """
    
    for attempt in range(2):
        try:
            status = 0
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_text = response.text
            #st.write(f"出力物：{raw_text}")
            if "[STATUS:COMPLETE]" in raw_text:
                status = 1
                # ユーザーに見せるメッセージからフラグを除去
                clean_text = raw_text.replace("[STATUS:COMPLETE]", "").strip()
                st.success("✅ 要件の合意が完了しました。JSON生成フェーズへ移行します。")
            else:
                clean_text = raw_text.replace("[STATUS:INCOMPLETE]", "").strip()
                
            return [clean_text, status]
        
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            if attempt == 4:
                return ["申し訳ありません。接続エラーが発生しました。もう一度入力していただけますか？", 0]
            
    return ["AIの応答を生成できませんでした。", 0]

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
            return [requestresponse_text, 1]
        
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
                    response_text = response[0]
                    analysis_tate_flag = 0
                    ## ユーザー対話セクションで正常終了なら戻り値が配列で返ってくる。
                    if len(response) > 1:
                        analysis_tate_flag += int(response[1])
                    ## ユーザー対話セクションにてAIが終了と判断した場合には配列2番目に１が返される
                    ## 1の場合はjson作成と分析を行う。
                    if analysis_tate_flag == 0:
                        st.markdown(response_text)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    elif analysis_tate_flag == 1:
                        st.success("✅ 分析開始。")
                        market_response = captureMarketVibe(st.session_state.messages)
                        if len(response) > 1:
                            st.session_state.transitionState += 1
                            st.session_state.analysisText = market_response[0]
                #elif st.session_state.transitionState == 1:
                            st.success("✅ 台本作成開始。")
                            response = ScenarioMakeAgent.MakeScenario(st.session_state.analysisText)
                            st.write(f"台本：{response}")
                            analysis_tate_flag += 1
                    else:
                        st.stop()
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