# 画面用
import streamlit as st
# 動画生成用
import time
import random
from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv
from google import genai
import google.genai.types as types
import json

# 固定の返信（あなたのAI処理の代わり）
def get_ai_response(user_input):  
    re_value = ""
    st.session_state.transitionState += 1
    # ユーザー入力に”はい”が含まれているか。含まれていたら次のAIに投げる。
    match st.session_state.transitionState:
        case 0:
            aiResponse = perplexiy_serch(user_input)
            # re_value += f"""カテゴリは{aiResponse[0]["category_genre"]}\n"""
            # re_value += f"""時間は{aiResponse[0]["duration_seconds"]}\n"""
            # re_value += f"""動画の特徴は{aiResponse[0]["features"]}\n"""
            # re_value += f"""動画の構成は{aiResponse[0]["video_structure"]}"""
            # re_value += f"""ターゲット層は{aiResponse[0]["target_audience"]}"""
            re_value = json.dumps(aiResponse, indent=2, ensure_ascii=False)
        case 1:
            create_video_prompt(user_input)
            re_value = json.dumps(st.session_state.jsonList[1], indent=2, ensure_ascii=False)
        case 2:
            create_video()
            re_value = "動画作成完了！"
    # 再生から戻ってきたプロンプトに対しての後処理
    return f"AI: '{re_value}'"

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
                response = get_ai_response(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

    # クリアボタン
    if st.button("会話クリア", use_container_width=True):
        st.session_state.messages = []
        st.rerun()





#------------------------------------------------------------------------------------------
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

def perplexiy_serch(user_prompt):
    re_format = {
            "video_analysis": {
                "rank": 0,
                "category_genre": "",
                "duration_seconds": 0,
                "features": [
                    "",
                    ""
                ],
                "video_structure": [
                {
                    "time_stamp": "00:00",
                    "phase": "",
                    "description": ""
                }
                ],
                "target_audience": {
                    "demographics": "",
                    "user_needs": ""
                }
                }
            }
    # ----------------------------------------
    # Perplexity：トレンド調査プロンプト生成
    # ----------------------------------------
    response = client.chat.completions.create(
        model="sonar",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"""
            直近トレンドから、「実際に再生数が非常に伸びやすい動画の特徴」をかなり具体的に推測してください。
            人気ランキングを3位までで作成して下さい。
            下記のjsonフォーマットに従って返答ください。
            出力は必ず指定したJSON形式のみで行ってください。解説などの前置きは不要です。
            {json.dumps(re_format, indent=4, ensure_ascii=False)}
            
            また、下記はユーザーからの要望になります。これに沿った形で返答ください。
            {user_prompt}
            """}
        ],
    )
    st.session_state.jsonList.append(response.choices[0].message.content)
    return response.choices[0].message.content

# -------------------------------
#  動画台本作成
# -------------------------------
def create_video_prompt(user_input):
    outputPromptFormat = [
        {
            "sequence_control": {
                "segment_id": "01_of_05",
                "total_segments": 5,
                "current_time_range": "00:00 - 00:08",
                "is_last_segment": False,
                "consistency_key": "Blue_Cyber_Car_ID_01"
            },
            "visual_generation_prompt": {
                "primary_prompt_en": "Cinematic wide shot of a Blue_Cyber_Car_ID_01 racing through a neon Tokyo street at night. [Typography Focus: Large futuristic glowing text 'NEXT GEN' appears floating in the mid-ground]. High speed motion blur, 8k resolution.",
                "start_frame": "Car positioned at the left third of the frame, headlights on.",
                "end_frame": "Car reaches the center of the frame, passing under a bridge.",
                "camera_motion": "Low-angle tracking shot, fast zoom-in towards the car's emblem.",
                "subject_details": "Metallic blue finish, hexagonal glowing patterns on wheels, sleek aerodynamic body."
            },
            "post_production_layer": {
                "overlay_text": {
                    "content": "未来を、加速させる。",
                    "style": "Futuristic sans-serif, White with blue glow",
                    "position": "Center-Bottom",
                    "in_out_time": "00:02 - 00:06"
                },
                "audio_track": {
                    "narration_script": "加速する未来。その先に見える景色とは。",
                    "voice_profile": "Deep male voice, calm and professional",
                    "sound_fx": "00:00 - futuristic engine hum, 00:04 - digital glitch sound"
                }
            }
        }
    ]

    # 最初のメタプロンプト
    prompt = f"""
    下記のjsonからAIに動画生成をさせるためのプロンプトを
    作成してください。
    ただし、動画生成は1回につき8秒しか作成することができないため、
    動画の秒数は最大30とし、適切な場所で分割して、
    秒数ごとに動画生成をするプロンプトを作成してください。
    作る動画は1本でよいです。必ず日本語で作成してください。
    ↓入力json
    {st.session_state.jsonList[0]}
    
    出力に関しては下記のjsonフォーマットに従ってください。
    また、出力はjson以外のものは何も出力しないでください。
    ↓出力フォーマット
    {json.dumps(outputPromptFormat, indent=4, ensure_ascii=False)}
    """

    # 指数バックオフ付き API 呼び出し
    response = safe_generate_content(prompt)

    st.session_state.jsonList.append(response.text)

    # 最低限のクールダウン
    time.sleep(5)

# -------------------------------
#  動画生成パート（3分割）
# -------------------------------
def create_video():
    current_video = None
    counter = 0
    
    # 1. データの存在確認
    if not st.session_state.jsonList or len(st.session_state.jsonList) < 2:
        st.error("動画構成データが見つかりません。")
        return

    # 最新の構成データを取得（これがJSON形式の文字列であることを想定）
    moviePrompt = st.session_state.jsonList[-1] 

    # リスト形式でない場合はリスト化（ループを回すため）
    if not isinstance(moviePrompt, list):
        moviePrompt = [moviePrompt]

    total_parts = len(moviePrompt)
    st.write(f"🎬 全 {total_parts} パートの動画生成を開始します。")

    for prm in moviePrompt:
        counter += 1
        st.info(f"⏳ パート {counter}/{total_parts} を生成中...")

        # --- シンプルにJSON変数をプロンプトに埋め込む ---
        # ユーザー様のご指定通り、固定文字と変数を組み合わせたシンプルな形です
        prompt_text = f"""
            下記のjsonの要件を満たす動画を作成してください。
            なお、動画はすべて日本語で作成してください。
            ↓動画作成のためのインプット
            {prm}
            """
        
        try:
            # 安全な生成実行
            op = safe_generate_video(prompt_text, current_video)

            while not op.done:
                time.sleep(10)
                op = genai_client.operations.get(op)

            if op.response is None:
                st.error(f"❌ 生成失敗（パート {counter}）")
                return

            # 生成された動画情報の取得
            generated_video_info = op.response.generated_videos[0]
            video_object = generated_video_info.video
            
            # 保存処理
            try:
                # SDKの仕様に合わせてターゲットを特定
                target_file = video_object.name if hasattr(video_object, 'name') else video_object
                video_bytes = genai_client.files.download(file=target_file)
                
                output_path = f"output_part_{counter}.mp4"
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                
                st.success(f"✅ 保存完了: {output_path}")
                
                if counter == total_parts:
                    st.video(video_bytes)
                    
            except Exception as download_err:
                st.warning(f"保存エラー: {download_err}")

            # 次の動画のために引き継ぎ（これが重要です）
            current_video = video_object
            time.sleep(5)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            break

load_dotenv()
perpApiKey = os.getenv('PERPLE_API_KEY')
googleKey = os.getenv('GOOGLE_API_KEY')

# Perplexity API
client = OpenAI(api_key=perpApiKey, base_url="https://api.perplexity.ai")
veo_model = "veo-3.1-generate-preview"

genai_client = genai.Client(api_key=googleKey)
setup_app()
display_chat_history()
handle_chat()