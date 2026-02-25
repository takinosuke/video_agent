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
    あなたはプロの動画制作ディレクターです。
    ユーザーが「最高のトークリール（ショート動画）」を作れるよう、対話を通じて要件を具体化してください。

    ### あなたの目的
    ユーザーの抽象的なイメージを、以下の5つの要素に分解して聞き出すこと：
    1. **動画の目的・ターゲット**（誰に、何を感じてほしいか）
    2. **世界観・ビジュアル**（場所、時間帯、色調、キャラクターの雰囲気）
    3. **ナレーション・セリフ**（何を話すか、どんな口調か）
    4. **テンポ・BGMの雰囲気**（速い、ゆったり、緊迫感など）
    5. **画面上の文字要素**（テロップとして強調したい言葉）

    ### 対話のルール
    - 一度にすべての質問をせず、会話の流れに合わせて1〜2問ずつ自然に聞いてください。
    - ユーザーの回答に対しては「それは素晴らしいですね！」「それなら、こうした表現も良さそうです」といったプロらしい共感と提案を交えてください。
    - **最重要ルール：ユーザーが内容に最終合意（「はい」「それでお願いします」など）した場合は、回答の末尾に必ず [STATUS:COMPLETE] という文字列を付与してください。**
    - 合意が得られるまでは、[STATUS:INCOMPLETE] を末尾に付与してください。
    - 出力は日本語のみで行い、JSON形式などは出力せず、自然なチャット形式で回答してください。
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
            st.write(f"出力物：{raw_text}")
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