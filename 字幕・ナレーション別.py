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
import re
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from google.cloud import texttospeech
import PIL.Image

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
            create_image()
            #create_video()
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
def safe_generate_content(prompt, retries=8):
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
                "user_name": "",
                "video_title": "",
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
            直近の日本国内でのトレンドから、「実際に再生数が非常に伸びやすい動画の特徴」をかなり具体的に推測して下記のjsonのフォーマットで出力して欲しいです。
            分析は1週間での再生数の多い流行りの動画から実在するもの1つ選択して動画についての構成を分析し、「user_name」タグに投稿主の名前、「video_title」タグに動画タイトルを入れてください。
            出力は必ず指定したJSON形式のみで行ってください。解説などの前置きは不要です。
            ↓出力時のjsonフォーマット
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
    outputPromptFormat = {
    "sequence_control": {
        "segment_id": "",
        "total_segments": "",
        "current_time_range": "",
        "is_last_segment": "",
        "continuation_token": ""
    },
    "visual_instruction": {
        "prompt_en": "",
        "start_frame_description": "",
        "end_frame_description": "",
        "camera_movement": "",
        "subject_consistency": ""
    },
    "text_and_display_settings": {
        "on_screen_display": {
        "display_text": "",
        "display_type": "",
        "design_notes": "",
        "language_priority": ""
        },
        "caption_overlay": [
        {
            "text": "",
            "display_timing": "",
            "style": "",
            "position": "",
            "font_color": "",
            "edge_color": ""
        }
        ]
    },
    "audio_and_speech": {
        "narration": {
        "script": "",
        "reading_guide": "",
        "voice_tone": "",
        "speech_speed": "",
        "pauses": ""
        },
        "audio_cue": [
        {"time": "", "effect": ""}
        ]
    }
    }

    # 最初のメタプロンプト
    prompt = f"""
    下記のjsonからAIに動画生成をさせるためのプロンプトを
    作成してください。
    ただし、動画生成は1回につき8秒しか作成することができないため、
    動画の秒数は最大30とし、適切な場所で分割して、
    秒数ごとに動画生成をするプロンプトを作成してください。
    作る動画は1本でよいです。日本人に向けた動画なので必ず日本語で作成してください。
    また暴力的な表現や公序良俗、著作権に反する表現は避けるように指示を作成してください。
    "image_generation_prompt"に関しては動画生成の補助のための画像を作成するものなので、動画を作るためのもとになる画像を作るプロンプトを入れてください。
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

def create_image():
    #image_model = genai.GenerativeModel('imagen-3')
    
    prompt_json = st.session_state.jsonList[-1]
    if len(prompt_json) <= 1:
        print("プロンプトが存在しないため、処理終了。")
        return
    
    # --- 修正後のコード ---
    for m in genai_client.models.list():
        # モデル名を取得（m.name が一般的ですが、念のため getattr を使用）
        model_name = getattr(m, 'name', '')
        # モデル名を表示（デバッグ用）
        print(f"チェック中のモデル: {model_name}")
        # 名前の中に 'imagen' が含まれているか、
        # または直接 'imagen-3' を指定して画像生成を試みる
        if 'imagen' in model_name.lower():
            print(f"画像生成モデルを見つけました: {model_name}")
            # ここで処理を続行
    
    current_image = None
    print("jsonのおおもとの中身は：")
    print(prompt_json)
    cleaned_json = prompt_json.replace("```json", "").replace("```", "").strip()
    data = json.loads(cleaned_json)
    for json_word in data:        
        # if current_image == None:
        #     image_response = genai_client.models.generate_images(
        #         model='models/imagen-4.0-fast-generate-001',
        #         prompt=img_prompt,
        #         config=types.GenerateImagesConfig(
        #             number_of_images=1,
        #         )
        #     )
        #     # 【修正箇所1】
        #     # image_response.generated_images[0].image は直接渡さず、
        #     # .image_bytes (バイナリ) を取得するか、BytesIO経由で処理します
        #     img_data = image_response.generated_images[0].image.image_bytes
            
        #     # Streamlitで表示
        #     st.image(img_data, caption="Generated Image", use_container_width=True)
            
        #     # current_image には後続のGeminiへの入力用にオブジェクトを保持
        #     current_image = image_response.generated_images[0].image
        # else:
        #     # 既存の画像がある場合の処理（Gemini 1.5 Flashを使用）
        #     image_response = genai_client.models.generate_content(
        #         model="gemini-1.5-flash",
        #         contents=[image_prompt, current_image]
        #     )
        #     # 【修正箇所2】
        #     # inline_data からバイナリデータを取得
        #     img_data = image_response.candidates[0].content.parts[0].inline_data.data
            
        #     st.image(img_data, caption="Iterated Image", use_container_width=True)
            
        #     # 次のループ用にフォーマットを整えて保持（必要に応じて）
        #     current_image = image_response.candidates[0].content.parts[0]
        prompt = F"""下記のjsonに定義された特徴を持った画像を生成AIを使って作成したいです。
        そのためのプロンプトを作成してください。
        ↓json
        """ + json.dumps(json_word, indent=4, ensure_ascii=False)
        
        response = safe_generate_content(prompt)

        # 最低限のクールダウン
        time.sleep(5)
        
        image_response = genai_client.models.generate_images(
            model='models/imagen-4.0-fast-generate-001',
            prompt=response.text,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            )
        )
        # 【修正箇所1】
        # image_response.generated_images[0].image は直接渡さず、
        # .image_bytes (バイナリ) を取得するか、BytesIO経由で処理します
        img_data = image_response.generated_images[0].image.image_bytes
        
        # Streamlitで表示
        st.image(img_data, caption="Generated Image", use_container_width=True)
        
        # current_image には後続のGeminiへの入力用にオブジェクトを保持
        current_image = image_response.generated_images[0].image




# -------------------------------
#  動画生成パート（3分割）
# -------------------------------
def create_video():
    current_video = None
    counter = 0
    # --- 変更点1: 成功した動画を保持するリスト ---
    completed_videos = []
    
    if not st.session_state.jsonList or len(st.session_state.jsonList) < 2:
        st.error("動画構成データが見つかりません。")
        return

    raw_json = st.session_state.jsonList[-1] 
    
    try:
        if isinstance(raw_json, str):
            # 文字列からJSONの塊を抽出するより堅牢なロジック
            video_prompts = []
            import json
            
            # JSONが始まる位置を探す
            content = raw_json.strip()
            # もし Markdown のコードブロック ```json などがあれば除去
            content = re.sub(r'```json\s*|```', '', content).strip()
            
            # 連続する JSON オブジェクトを一つずつ取り出す
            decoder = json.JSONDecoder()
            pos = 0
            while pos < len(content):
                # 空白を飛ばす
                match = re.search(r'\S', content[pos:])
                if not match:
                    break
                pos += match.start()
                
                try:
                    # 1つの完全な JSON オブジェクトをパース
                    obj, next_pos = decoder.raw_decode(content[pos:])
                    if isinstance(obj, dict) and "visual_instruction" in obj:
                        video_prompts.append(obj)
                    elif isinstance(obj, list):
                        # 配列で返ってきた場合、中身を統合
                        for item in obj:
                            if isinstance(item, dict) and "visual_instruction" in item:
                                video_prompts.append(item)
                    pos += next_pos
                except json.JSONDecodeError:
                    # パースできないゴミデータがあれば1文字飛ばして次を探す
                    pos += 1
            
            if not video_prompts:
                raise ValueError("有効な動画構成JSONが見つかりませんでした。")
        else:
            video_prompts = raw_json
    except Exception as e:
        st.error(f"JSONパースエラー (詳細): {e}")
        return

    if isinstance(video_prompts, dict):
        video_prompts = [video_prompts] if "visual_instruction" in video_prompts else list(video_prompts.values())

    total_parts = len(video_prompts)
    st.write(f"🎬 全 {total_parts} パートの動画生成を開始します。")

    # --- create_video 関数内のループ部分を以下のように微調整します ---

    for prm_data in video_prompts:
        counter += 1
        # プロンプトの組み立て
        prompt_text = f"""下記のJsonデータに定義されている特徴の動画を作成してください。
                        ”audio_and_speech”タグと”display_text”タグは無視してください。
                        ↓jsonデータ\n"""
        prompt_text += json.dumps(prm_data, indent=2, ensure_ascii=False)
        
        st.info(f"⏳ パート {counter}/{total_parts} を生成中...")
        
        try:
            # 1. 動画生成リクエストの送信
            op_initial = safe_generate_video(prompt_text, current_video)

            # 2. Operation IDを文字列として確実に取得
            # SDKの戻り値がオブジェクトなら .name、文字列ならそのまま使用
            op_id = getattr(op_initial, 'name', op_initial)
            if not isinstance(op_id, str):
                op_id = str(op_id)
            
            st.info(f"🔍 Operation ID: {op_id}")

            # 3. 待機ループ（ポーリング）
            actual_op = None
            while True:
                actual_op = genai_client.operations.get(op_id)
                
                # actual_op が辞書かオブジェクトかに関わらず 'done' を取得
                is_done = False
                if hasattr(actual_op, 'done'):
                    is_done = actual_op.done
                elif isinstance(actual_op, dict):
                    is_done = actual_op.get('done', False)
                
                if is_done:
                    break
                
                time.sleep(10)

            # 4. レスポンスの確認
            # 完了した actual_op から response を取得
            response = None
            if hasattr(actual_op, 'response'):
                response = actual_op.response
            elif isinstance(actual_op, dict):
                response = actual_op.get('response')

            if response is None:
                # エラー詳細の取得を試みる
                err_detail = "Unknown error"
                if hasattr(actual_op, 'error'):
                    err_detail = actual_op.error
                st.error(f"❌ パート {counter} の生成に失敗しました。理由: {err_detail}")
                show_available_videos(completed_videos)
                return

            # 5. 生成された動画リストの取得
            # response.generated_videos または response['generatedVideos']
            gen_videos = getattr(response, 'generated_videos', None)
            if gen_videos is None and isinstance(response, dict):
                gen_videos = response.get('generatedVideos')

            if not gen_videos:
                st.error(f"❌ パート {counter}: 動画データが空です。")
                show_available_videos(completed_videos)
                return

            # 成功時：最初の動画オブジェクトを取得
            generated_video_info = gen_videos[0]
            video_object = getattr(generated_video_info, 'video', generated_video_info)
            
            completed_videos.append(video_object)

            if counter == total_parts:            
                st.write("📥 最終動画を保存中...")
                # ファイル名の取得（文字列またはオブジェクトの .name 属性）
                target_file_name = getattr(video_object, 'name', video_object)
                video_bytes = genai_client.files.download(file=target_file_name)
                
                output_path = "final_output.mp4"
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                
                # 字幕・ナレーション合成
                # ※ st.session_state.jsonList[-1] はJSON文字列なので、一時ファイルに書き出すか
                # 　 関数側を dict 対応に修正する必要があります
                auto_add_subtitle_narration(output_path, st.session_state.jsonList[-1])
                
                st.success("✨ すべての生成が完了しました！")
                st.video(output_path)
            else:
                st.write(f"✅ パート {counter} 完了。")
            
            current_video = video_object
            time.sleep(10) 

        except Exception as e:
            st.error(f"予期せぬエラーが発生しました (パート {counter}): {e}")
            import traceback
            st.error(traceback.format_exc()) # デバッグ用にスタックトレースを表示
            show_available_videos(completed_videos)
            break

# --- 変更点1に付随する表示用補助関数 ---
def show_available_videos(video_list):
    if video_list:
        st.divider()
        st.subheader("⚠️ 生成済みのパートまでを表示します")
        for i, v_obj in enumerate(video_list):
            try:
                target = v_obj.name if hasattr(v_obj, 'name') else v_obj
                v_bytes = genai_client.files.download(file=target)
                st.write(f"パート {i+1}")
                st.video(v_bytes)
            except:
                st.write(f"パート {i+1} の表示に失敗しました。")

def auto_add_subtitle_narration(video_path, json_path):
    with open(json_path) as f:
        config = json.load(f)
    
    # TTSナレーション生成
    client = texttospeech.TextToSpeechClient()
    narration_text = config["audio_and_speech"]["narration"]["script"]
    # SSMLでtone/speed/pauses反映
    ssml = f'<speak><prosody rate="medium">{narration_text}</prosody></speak>'
    response = client.synthesize_speech(...)  # 前回コード参照
    audio = AudioFileClip("narration.mp3")
    
    # 動画合成
    video = VideoFileClip(video_path).set_audio(audio)
    
    # JSON caption_overlayで字幕追加
    subtitles = []
    for caption in config["text_and_display_settings"]["caption_overlay"]:
        txt_clip = (TextClip(caption["text"], 
                           fontsize=50, color=caption["font_color"])
                   .set_position(caption["position"])
                   .set_start(float(caption["display_timing"])))
        subtitles.append(txt_clip)
    
    final = CompositeVideoClip([video] + subtitles)
    final.write_videofile("output.mp4")

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