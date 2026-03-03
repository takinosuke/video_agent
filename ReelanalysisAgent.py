from dotenv import load_dotenv
import streamlit as st
from google import genai
import time
import json
import random
import os

def get_ai_response(user_input, history_text):
    context = ""
    for msg in st.session_state.messages:
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
                response = get_ai_response(prompt, st.session_state.messages)
                response_text = response[0]
                if(response[1] == 0):
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
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