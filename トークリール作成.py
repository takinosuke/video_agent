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
import requests

# 固定の返信（あなたのAI処理の代わり）
def get_ai_response(user_input):  
    re_value = ""
    st.session_state.transitionState += 1
    # ユーザー入力に”はい”が含まれているか。含まれていたら次のAIに投げる。
    
    video_prompt = "json\n[\n    {\n        \"sequence_control\": {\n            \"segment_id\": \"S1\",\n            \"total_segments\": \"4\",\n            \"current_time_range\": \"00:00 - 00:07\",\n            \"is_last_segment\": false,\n            \"continuation_token\": null\n        },\n        \"visual_instruction\": {\n            \"prompt_en\": \"A captivating close-up shot of a fresh egg and a classic glass bottle of Coca-Cola on a clean, bright science lab bench. The background is slightly blurred. Dynamic lighting creates a sense of intrigue. The camera slowly zooms in.\",\n            \"start_frame_description\": \"画面中央にピカピカの新鮮な卵。その隣に冷えたクラシックなコーラの瓶。背景は明るく清潔感のある実験台で、少しぼかされている。照明はドラマチックで、これから始まる実験への期待感を高める。\",\n            \"end_frame_description\": \"卵とコーラにスポットライトが当たり、これから始まる実験への期待感を高める。カメラがゆっくりとズームインし、両者が画面いっぱいに広がる。\",\n            \"camera_movement\": \"Slow zoom in, slight pan to emphasize both subjects. Smooth and steady.\",\n            \"subject_consistency\": \"Consistent appearance of a fresh, white egg and a full, glass Coca-Cola bottle with its classic label.\"\n        },\n        \"text_and_display_settings\": {\n            \"on_screen_display\": {\n                \"display_text\": \"まさかの結果に驚愕！\\nコーラに卵を漬けると…？\",\n                \"display_type\": \"Title card / Call to action overlay\",\n                \"design_notes\": \"ポップで好奇心を刺激するフォントを使用。文字色は明るい黄色で、太い黒の縁取りを施す。テキストは画面中央にダイナミックなアニメーションで登場し、視線を引きつける。\",\n                \"language_priority\": \"Japanese\"\n            },\n            \"caption_overlay\": [\n                {\n                    \"text\": \"この二つで、一体何が起こると思いますか？\",\n                    \"display_timing\": \"00:03 - 00:07\",\n                    \"style\": \"読みやすいゴシック体、太字。\",\n                    \"position\": \"画面下部中央\",\n                    \"font_color\": \"white\",\n                    \"edge_color\": \"black\"\n                }\n            ]\n        },\n        \"audio_and_speech\": {\n            \"narration\": {\n                \"script\": \"皆さん、こんにちは！今日は、身近な材料『コーラ』と『卵』を使って、とんでもない実験に挑戦します！\",\n                \"reading_guide\": \"明るく、好奇心を煽るようなトーンで。少し間をおいて「とんでもない実験」を強調し、視聴者の期待を高める。\",\n                \"voice_tone\": \"Upbeat, inquisitive, slightly mysterious.\",\n                \"speech_speed\": \"Normal to slightly faster.\",\n                \"pauses\": \"After \\\"コーラと卵を使って\\\"\"\n            },\n            \"audio_cue\": [\n                {\n                    \"time\": \"00:00\",\n                    \"effect\": \"Upbeat, light-hearted background music begins, setting an energetic and curious mood.\"\n                },\n                {\n                    \"time\": \"00:03\",\n                    \"effect\": \"Short, subtle 'ding' sound to emphasize the appearance of the on-screen text.\"\n                }\n            ]\n        }\n    },\n    {\n        \"sequence_control\": {\n            \"segment_id\": \"S2\",\n            \"total_segments\": \"4\",\n            \"current_time_range\": \"00:07 - 00:14\",\n            \"is_last_segment\": false,\n            \"continuation_token\": \"Continue from lab bench setup with egg and cola. Transition to preparation phase.\"\n        },\n        \"visual_instruction\": {\n            \"prompt_en\": \"A person's clean hands carefully placing the fresh egg into a clear glass jar. Then, slowly pouring Coca-Cola from the bottle to completely submerge the egg. Close-up shots of the liquid filling the jar, showing subtle effervescence.\",\n            \"start_frame_description\": \"清潔な手が、S1に登場した新鮮な卵を透明なガラス瓶の中にそっと置く。瓶はシンプルで、内部がよく見えるデザイン。\",\n            \"end_frame_description\": \"コーラが卵を完全に覆うまで丁寧に注がれる様子。瓶の中の液体が満たされていくクローズアップ映像。微細な泡立ちが見える。\",\n            \"camera_movement\": \"Medium shot showing hands performing actions, then smooth close-up transitions to the jar and the pouring action. Controlled and steady movements.\",\n            \"subject_consistency\": \"The same fresh egg and Coca-Cola bottle/brand as S1. A new clear, medium-sized glass jar with a lid is introduced.\"\n        },\n        \"text_and_display_settings\": {\n            \"on_screen_display\": {\n                \"display_text\": \"材料はたったこれだけ！\\nシンプルな準備\",\n                \"display_type\": \"Informational overlay\",\n                \"design_notes\": \"ミニマルで分かりやすいデザイン。半透明の白背景に黒文字を使用し、情報の伝達を優先する。画面上部に表示。\",\n                \"language_priority\": \"Japanese\"\n            },\n            \"caption_overlay\": [\n                {\n                    \"text\": \"用意するのは、卵とコーラ、そしてフタ付きの瓶だけ。\",\n                    \"display_timing\": \"00:08 - 00:12\",\n                    \"style\": \"読みやすいゴシック体。\",\n                    \"position\": \"画面下部中央\",\n                    \"font_color\": \"white\",\n                    \"edge_color\": \"black\"\n                },\n                {\n                    \"text\": \"あとは、コーラが卵を浸すように注ぎ込むだけです。\",\n                    \"display_timing\": \"00:12 - 00:14\",\n                    \"style\": \"読みやすいゴシック体。\",\n                    \"position\": \"画面下部中央\",\n                    \"font_color\": \"white\",\n                    \"edge_color\": \"black\"\n                }\n            ]\n        },\n        \"audio_and_speech\": {\n            \"narration\": {\n                \"script\": \"準備はとっても簡単！卵を瓶に入れ、コーラを注ぎ込むだけ。さあ、この状態で数日間待ちます。\",\n                \"reading_guide\": \"明瞭で分かりやすく、手順を説明するトーン。視聴者が簡単に真似できることを強調する。\",\n                \"voice_tone\": \"Instructive, clear, slightly anticipating.\",\n                \"speech_speed\": \"Normal.\",\n                \"pauses\": \"After \\\"注ぎ込むだけ。\\\"\"\n            },\n            \"audio_cue\": [\n                {\n                    \"time\": \"00:08\",\n                    \"effect\": \"Gentle 'clink' sound as the egg is placed into the glass jar.\"\n                },\n                {\n                    \"time\": \"00:09\",\n                    \"effect\": \"Realistic pouring liquid sound as Coca-Cola fills the jar.\"\n                }\n            ]\n        }\n    },\n    {\n        \"sequence_control\": {\n            \"segment_id\": \"S3\",\n            \"total_segments\": \"4\",\n            \"current_time_range\": \"00:14 - 00:22\",\n            \"is_last_segment\": false,\n            \"continuation_token\": \"Continue from the jar with egg submerged in cola. Initiate time-lapse sequence.\"\n        },\n        \"visual_instruction\": {\n            \"prompt_en\": \"A fast-forward, time-lapse sequence showing the glass jar with the egg submerged in Coca-Cola over several days. Subtle visual changes of the liquid and egg surface, such as slight discoloration of the liquid or formation of small bubbles around the egg. The background subtly changes light to suggest passage of time (e.g., natural light shifting from day to night cycles).\",\n            \"start_frame_description\": \"コーラに浸された卵の入った瓶。初期の状態が映し出される。時間は速送りされている。\",\n            \"end_frame_description\": \"数日後の卵とコーラの変化（コーラの色がわずかに濃くなる、卵の表面に微細な泡や薄い膜が見えるなど）。時間の経過を表現するために、背景の光がゆっくりと変化し、日の移ろいを暗示する。\",\n            \"camera_movement\": \"Static shot of the jar, with subtle time-lapse visual effects applied to the contents and slight environmental lighting changes in the background.\",\n            \"subject_consistency\": \"The same glass jar, egg, and Coca-Cola. The visual effects should emphasize the passage of time on these elements.\"\n        },\n        \"text_and_display_settings\": {\n            \"on_screen_display\": {\n                \"display_text\": \"数日後…\\n変化の兆し\",\n                \"display_type\": \"Time-lapse indicator / Progress update\",\n                \"design_notes\": \"時間経過を示すシンプルなテキスト。グラデーションの背景に白文字を使用し、神秘的な雰囲気を出す。画面上部にフェードイン・アウトで表示。\",\n                \"language_priority\": \"Japanese\"\n            },\n            \"caption_overlay\": [\n                {\n                    \"text\": \"そして数日が経過しました…\",\n                    \"display_timing\": \"00:15 - 00:18\",\n                    \"style\": \"読みやすいゴシック体。\",\n                    \"position\": \"画面下部中央\",\n                    \"font_color\": \"white\",\n                    \"edge_color\": \"black\"\n                },\n                {\n                    \"text\": \"何か変化が起こっているようです…！\",\n                    \"display_timing\": \"00:19 - 00:22\",\n                    \"style\": \"読みやすいゴシック体。\",\n                    \"position\": \"画面下部中央\",\n                    \"font_color\": \"white\",\n                    \"edge_color\": \"black\"\n                }\n            ]\n        },\n        \"audio_and_speech\": {\n            \"narration\": {\n                \"script\": \"そして数日後…見た目はあまり変わりませんが、果たして卵はどうなっているのでしょうか？\",\n                \"reading_guide\": \"期待感を高めるような、少し引っ張るトーンで語りかける。視聴者の好奇心を刺激する。\",\n                \"voice_tone\": \"Anticipatory, curious, building suspense.\",\n                \"speech_speed\": \"Normal.\",\n                \"pauses\": \"After \\\"果たして卵はどうなっているのでしょうか？\\\"\"\n            },\n            \"audio_cue\": [\n                {\n                    \"time\": \"00:14\",\n                    \"effect\": \"Time-lapse 'whoosh' sound effect begins, then subtly fades into background.\"\n                },\n                {\n                    \"time\": \"00:19\",\n                    \"effect\": \"Subtle 'bubbling' or 'chemical reaction' sound effects fade in then out, hinting at internal changes.\"\n                }\n            ]\n        }\n    },\n    {\n        \"sequence_control\": {\n            \"segment_id\": \"S4\",\n            \"total_segments\": \"4\",\n            \"current_time_range\": \"00:22 - 00:30\",\n            \"is_last_segment\": true,\n            \"continuation_token\": \"Continue from the time-lapsed jar. Focus on revealing and examining the transformed egg.\"\n        },\n        \"visual_instruction\": {\n            \"prompt_en\": \"A close-up shot of a hand carefully removing the egg from the Coca-Cola jar. The egg now appears translucent, rubbery, and the shell is completely gone, revealing the membrane. A slow, gentle rotation of the transformed egg to show its texture and elasticity. The egg is lightly squeezed to demonstrate its rubbery bounce. Dramatic lighting to highlight the extraordinary result.\",\n            \"start_frame_description\": \"コーラからゆっくりと、注意深く取り出される卵。元の形からは想像できないほど変形し、殻が溶けて半透明でゴムのような質感になっている。\",\n            \"end_frame_description\": \"透明でプルプル、ゴムのような質感になった卵が、指で軽く弾かれたり、優しく握られたりして、その弾力性や変形能力が強調される。視聴者が驚くような、視覚的にインパクトの強い結果を最大限にアピールする。\",\n            \"camera_movement\": \"Close-up of hands removing the egg, then a very tight close-up on the egg itself. Slow, deliberate rotation and gentle squeezing/bouncing actions to highlight its new texture and elasticity. Dynamic, focused lighting.\",\n            \"subject_consistency\": \"The dramatically transformed egg, clearly showing the profound effect of the Coca-Cola. The hand should be consistent with previous segments.\"\n        },\n        \"text_and_display_settings\": {\n            \"on_screen_display\": {\n                \"display_text\": \"この結果、まさか…！\\n驚きのプルプル卵！\\nあなたも挑戦！\",\n                \"display_type\": \"Reveal / Call to action\",\n                \"design_notes\": \"驚きと興奮を表現するダイナミックな太字フォント。文字色は鮮やかな黄色と白を使い分け、強い影付きで視認性を高める。最後にチャンネル登録や共有を促すテキストも含む。\",\n                \"language_priority\": \"Japanese\"\n            },\n            \"caption_overlay\": [\n                {\n                    \"text\": \"見てください！殻が溶けて、こんなにプルプルに！\",\n                    \"display_timing\": \"00:23 - 00:27\",\n                    \"style\": \"太字のゴシック体、感嘆符を強調。\",\n                    \"position\": \"画面中央下\",\n                    \"font_color\": \"yellow\",\n                    \"edge_color\": \"black\"\n                },\n                {\n                    \"text\": \"まさかの科学反応！あなたもぜひ試してみてね！\",\n                    \"display_timing\": \"00:27 - 00:30\",\n                    \"style\": \"太字のゴシック体、親しみやすいトーン。\",\n                    \"position\": \"画面中央下\",\n                    \"font_color\": \"white\",\n                    \"edge_color\": \"darkblue\"\n                }\n            ]\n        },\n        \"audio_and_speech\": {\n            \"narration\": {\n                \"script\": \"見てください！なんと卵の殻が溶けて、こんなにプルプルのゴムみたいになりました！まさに科学の力！皆さんもぜひ、お家でこの不思議な実験に挑戦してみてくださいね！\",\n                \"reading_guide\": \"驚きと興奮を込めて、視聴者にも呼びかけるように。語尾を上げ、発見の喜びを表現する。\",\n                \"voice_tone\": \"Excited, amazed, encouraging, friendly.\",\n                \"speech_speed\": \"Slightly faster, energetic.\",\n                \"pauses\": \"After \\\"ゴムみたいになりました！\\\" and \\\"科学の力！\\\"\"\n            },\n            \"audio_cue\": [\n                {\n                    \"time\": \"00:22\",\n                    \"effect\": \"Dramatic 'reveal' sound or a distinct 'whoosh' sound to mark the climax of the experiment.\"\n                },\n                {\n                    \"time\": \"00:24\",\n                    \"effect\": \"Subtle 'squishy' or 'rubbery' sound effects as the egg is gently handled and squeezed.\"\n                },\n                {\n                    \"time\": \"00:27\",\n                    \"effect\": \"Upbeat, conclusive background music swells to a peak, then smoothly fades out with a friendly jingle.\"\n                }\n            ]\n        }\n    }\n]\n"
    match st.session_state.transitionState:
        case 0:
            aiResponse = perplexiy_serch(user_input)            
            re_value = json.dumps(aiResponse, indent=2, ensure_ascii=False)
            # invoke_shotstack("対象動画.mp4", video_prompt)
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
                "user_name": "投稿主の名前",
                "video_title": "動画のタイトルまたは内容の要約",
                "analysis_results": {
                    "trend_context": "現在の国内トレンド（例：リアルな本音、お悩み解決、論破系など）との関連性",
                    "talk_structure": {
                        "hook_0_3s": "冒頭の具体的なセリフと視覚演出の意図",
                        "body_flow": "中盤のトーク展開（例：PREP法、疑問提示→解決、対話形式など）とカット編集の速さ",
                        "retention_tricks": "視聴を離脱させないための工夫（テロップ配置、強調エフェクト、表情の寄りなど）",
                        "cta_ending": "ラストの結末とコメント欄への誘導ロジック"
                    },
                    "success_factors": [
                        {
                            "factor": "言語化の鋭さ",
                            "detail": "視聴者が言語化できていない感情をどう表現しているか"
                        },
                        {
                            "factor": "オーディオ・ビジュアル戦略",
                            "detail": "音声の聞き取りやすさや、視覚的な情報密度の制御について"
                        }
                    ]
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
            あなたは「バズるトークリール」を専門に分析するプロフェッショナルなリサーチエージェントです。
            現在、日本国内で再生数が急上昇している実在の「トークリール（顔出し、または音声メインのショート動画）」を1つ選び、その成功要因を以下のJSON形式で分析してください。

            【分析の重点事項】
            1. トーク特化型のフック：冒頭1〜3秒で「何を言ったか」だけでなく「どう見せたか」を重視すること。
            2. 視聴維持の編集：テロップのタイミング、カットの速さ、BGMの有無など、トークを飽きさせない工夫。
            3. トレンド性：2026年現在の日本における「共感」や「議論」の種をどう扱っているか。
            4. 値は全て日本語で出力すること。

            【出力時のJSONフォーマット】
            {re_format}

            ※解説や前置きは一切不要です。指定したJSON形式のみで出力してください。
            ※ユーザーからの追加要望：{user_prompt}
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
    あなたはプロのAI動画ディレクターです。
    下記の入力データ（JSON）に基づき、**トークリール動画（縦型SNS向けのナレーションベース動画）**を生成するための詳細な台本プロンプトを構成してください。

    業務ルール
    1.動画全体の長さは最大30秒とします。
    2.動画生成AIの制約上、1回につき最大8秒しか生成できないため、全体を「4つ程度のセグメント（パート）」に分割してください。
    3.各セグメントごとに、下記のJSONフォーマットに準拠したデータを作成してください。
    4.最終的な出力は、それらすべてのセグメントを格納した「1つのJSON配列（リスト形式）」としてください。
    5.日本人向け動画のため、テキストや説明は必ず日本語で作成してください。
    6.公序良俗に反する表現や暴力的な表現は厳禁です。
    7.特定のインフルエンサーや実在するユーザーアカウント名など、個人を特定する内容は入れないでください。
    8.  本プロンプトはアバターや人物映像を使用しない、背景とテキスト・ナレーションのみで構成されたトークリール専用の台本にしてください。
    9.以下の点を特に重視して構成してください：
    　・ナレーションが視聴者に直接語りかけるような自然で親しみやすい口調にする
    　・背景映像はナレーション内容に合わせて変化させる（例：場面転換・色味・雰囲気）
    　・各セグメントには「ナレーション台詞」「背景演出」「テロップ案」を含める
    　・会話テンポを意識して、1文は短く区切る
    　・冒頭で視聴者の興味を引く一言（フック）を入れる

    ### 出力フォーマット（必ずこの「JSON配列」の形式を守ること）
    {json.dumps(outputPromptFormat, indent=4, ensure_ascii=False)}
    
    ↓入力json
    {st.session_state.jsonList[0]}
    """

    # 指数バックオフ付き API 呼び出し
    response = safe_generate_content(prompt)

    st.session_state.jsonList.append(response.text)

    # 最低限のクールダウン
    time.sleep(5)

## shotstackの起動
def invoke_shotstack(video_file_path, text_prompt):
    api_key = 'CmaP2Iev22KX3DFfhgmSnIccypQsBKVA6qt2hbe2'
    sandbox_url = 'https://api.shotstack.io/edit/v1'
    ingest_url = 'https://api.shotstack.io/ingest/v1'

    HEADERS = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    filename = video_file_path.split("/")[-1]
    res_url = requests.post(f"{ingest_url}/upload", headers=HEADERS, json={"filename": filename})
    print(res_url.json())  # エラー時に内容を確認するために追加

    # if res_url.status_code != 201:
    #     print(f"アップロードURLの取得に失敗しました: {res_url.text}")
    #     return
    if res_url.status_code not in [200, 201]:
        st.error(f"アップロードURLの取得に失敗しました: {res_url.text}")
        return

    upload_data = res_url.json()["data"]
    upload_url = upload_data["attributes"]["url"]
    source_id = upload_data["id"]
    
    # 実際のファイルをアップロード
    with open(video_file_path, "rb") as f:
        requests.put(upload_url, data=f)
        
    # --- 実務的な待機 (Polling) ---
    st.info("動画のインジェスト状況を確認中...")
    video_url = None
    
    while True:
        source_res = requests.get(f"{ingest_url}/sources/{source_id}", headers=HEADERS)
        
        # デバッグ用：レスポンスの中身に何が入っているか確認
        res_json = source_res.json()
        if "data" not in res_json:
            st.error(f"予期せぬレスポンス: {res_json}")
            return
            
        source_data = res_json["data"]["attributes"]
        source_status = source_data.get("status") # .getを使うことでKeyErrorを防止
        
        if source_status == "ready":
            # attributes の直下ではなく、proxy 等のフィールドを確認してください
            video_url = source_data.get("source") or source_data.get("url")
            st.success("動画の準備が完了しました。")
            break
        elif source_status == "failed":
            st.error("動画のインジェストに失敗しました。")
            return
        
        st.write(f"処理待ち... ステータス: {source_status}")
        time.sleep(3) # 少し長めに待機
       
    # フォントのアップロード
    filename = "./NotoSansJP-Regular.ttf".split("/")[-1]
    res_url = requests.post(f"{ingest_url}/upload", headers=HEADERS, json={"filename": filename})
    print(res_url.json())  # エラー時に内容を確認するために追加

    # if res_url.status_code != 201:
    #     print(f"アップロードURLの取得に失敗しました: {res_url.text}")
    #     return
    if res_url.status_code not in [200, 201]:
        st.error(f"アップロードURLの取得に失敗しました: {res_url.text}")
        return

    upload_data = res_url.json()["data"]
    upload_url = upload_data["attributes"]["url"]
    source_id = upload_data["id"]
    
    # 実際のファイルをアップロード
    with open("./NotoSansJP-Regular.ttf", "rb") as f:
        requests.put(upload_url, data=f)
        
    # --- 実務的な待機 (Polling) ---
    st.info("動画のインジェスト状況を確認中...")
    font_url = None
    
    while True:
        source_res = requests.get(f"{ingest_url}/sources/{source_id}", headers=HEADERS)
        
        # デバッグ用：レスポンスの中身に何が入っているか確認
        res_json = source_res.json()
        if "data" not in res_json:
            st.error(f"予期せぬレスポンス: {res_json}")
            return
            
        source_data = res_json["data"]["attributes"]
        source_status = source_data.get("status") # .getを使うことでKeyErrorを防止
        
        if source_status == "ready":
            # attributes の直下ではなく、proxy 等のフィールドを確認してください
            font_url = source_data.get("source") or source_data.get("url")
            st.success("動画の準備が完了しました。")
            break
        elif source_status == "failed":
            st.error("動画のインジェストに失敗しました。")
            return
        
        st.write(f"処理待ち... ステータス: {source_status}")
        time.sleep(3) # 少し長めに待機
       
        
    # 2. 字幕付き動画のレンダリング指示 (Edit)
    print("Step 2: レンダリングをリクエスト中...")
    st.write(f"video_urlは：{video_url}")
    st.write(f"font_urlは：{font_url}")
    shotstack_json = {
    "timeline": {
        "tracks": [
        {
            "clips": [
            {
                "asset": {
                "type": "title",
                "text": "この二つで、一体何が起こると思いますか？",
                "style": "minimal"
                },
                "start": 3.0,
                "length": 4.0
            },
            {
                "asset": {
                "type": "title",
                "text": "用意するのは、卵とコーラ、そしてフタ付きの瓶だけ。",
                "style": "minimal"
                },
                "start": 8.0,
                "length": 4.0
            }
            ]
        },
        {
            "clips": [
            {
                "asset": {
                "type": "text-to-speech",
                "text": "皆さん、こんにちは！今日は、身近な材料『コーラ』と『卵』を使って、とんでもない実験に挑戦します！",
                "voice": "Kazuha",
                "language": "ja-JP"
                },
                "start": 0.0,
                "length": "auto"
            },
            {
                "asset": {
                "type": "text-to-speech",
                "text": "準備はとっても簡単！卵を瓶に入れ、コーラを注ぎ込むだけ。さあ、この状態で数日間待ちます。",
                "voice": "Kazuha",
                "language": "ja-JP"
                },
                "start": 7.0,
                "length": "auto"
            }
            ]
        },
        {
            "clips": [
            {
                "asset": {
                "type": "video",
                "src": {video_url}
                },
                "start": 0.0,
                "length": 30.0
            }
            ]
        }
        ]
    },
    "output": {
        "format": "mp4",
        "resolution": "hd"
    }
    }
    
    ## geminiに対して、動画生成のプロンプトを投げてshotstackの編集用のプロンプトを作らせる ##
    ##
    prompt = f"""
    # 役割
    あなたはShotstack Edit APIのエキスパートです。
    提供された動画の台本から、動画に表示する字幕（titleアセット）のリストを作成してください。

    # 指示
    字幕情報を、Shotstackの「Track 0（字幕レイヤー）」として機能するJSON形式で出力してください。
    出力は純粋なJSONのみとし、一切の解説やMarkdownの囲いを含めないでください。

    # 🛠 字幕の仕様（厳守）
    1. **asset**: `"type": "title"` を使用。
    2. **style**: `"minimal"` 固定。
    3. **position**: `"bottom"` 固定。
    4. **タイミング**: `start`（開始時間）と `length`（表示秒数）を台本に基づいて秒単位で設定してください。

    # 入力データ
    - 動画の台本とタイムスケジュール：{text_prompt}

    # 出力フォーマット
    {{
    "clips": [
        {{
        "start": 0.0,
        "length": 3.0,
        "asset": {{
            "type": "title",
            "text": "ここに字幕の内容",
            "style": "minimal"
        }},
        "position": "bottom"
        }}
    ]
    }}
    """

    ## 指数バックオフ付き API 呼び出し
    response = safe_generate_content(prompt)
    st.write(f"字幕・ナレーション生成プロンプト：{response.text}")
    ## 受け取ったプロンプトを渡す。
    edit_json_str = response.text.replace("shotstack", video_url)
    
    # --- 1. Geminiの出力を辞書に変換 ---
    try:
        clean_json_str = edit_json_str.replace('```json', '').replace('```', '').strip()
        ai_generated_data = json.loads(clean_json_str)

        # Geminiが "timeline" キーを含めて出力している場合の抽出
        if "timeline" in ai_generated_data:
            ai_tracks = ai_generated_data["timeline"]["tracks"]
        else:
            ai_tracks = ai_generated_data["tracks"] if "tracks" in ai_generated_data else ai_generated_data

        # --- 2. 背景動画トラックの定義 ---
        # 背景動画を一番下のレイヤー（リストの最後）に追加
        video_track = {
            "clips": [
                {
                    "asset": {
                        "type": "video",
                        "src": str(video_url) 
                    },
                    "start": 0.0,
                    "length": 30.0  # 台本の合計（約30秒）に合わせる
                }
            ]
        }

        # --- 3. 最終的な送信用JSONを組み立てる ---
        final_payload = {
            "timeline": {
                "tracks": [ai_tracks, video_track],
                "fonts": [{"src":font_url}]
            },
            "output": {
                "format": "mp4",
                "resolution": "hd"
            }
        }

        # デバッグ用に送信直前の構造をログ出力（重要）
        print("Final Payload Tracks Count:", len(final_payload["timeline"]["tracks"]))

    except Exception as e:
        st.error(f"JSON組み立てに失敗しました: {e}")
        return
    
    st.write(f"最終的なshotstackへの入力：{final_payload}")

    # 3. 修正された辞書オブジェクトを json= 引数に渡す
    # (requestsが自動的に適切なJSON文字列に変換して送信します)
    render_res = requests.post(f"{sandbox_url}/render", headers=HEADERS, json=final_payload)
    
    if render_res.status_code not in [200, 201]:
        st.error(f"レンダリングリクエスト失敗: {render_res.text}")
        return

    render_id = render_res.json()["response"]["id"]
    st.warning(f"動画生成中 (ID: {render_id})...")

    # 4. 完了確認と表示
    while True:
        status_res = requests.get(f"{sandbox_url}/render/{render_id}", headers=HEADERS)
        status = status_res.json()["response"]["status"]
        
        if status == "done":
            video_final_url = status_res.json()["response"]["url"]
            st.success("動画が完成しました！")
            
            # --- Streamlitに表示 ---
            st.video(video_final_url)
            
            # ダウンロードボタンも設置しておくと親切です
            st.download_button("動画をダウンロード", requests.get(video_final_url).content, file_name="output.mp4")
            break
        elif status == "failed":
            # レスポンス全体を取得
            res_data = status_res.json().get("response", {})
            
            # エラーメッセージを取得（Shotstackの構造に合わせる）
            error_msg = res_data.get("error", "不明なエラー")
            
            st.error(f"レンダリング失敗: {error_msg}")
            
            # 開発者用にログにも詳細を出す
            print(f"Full Error Response: {status_res.json()}")
            break
        
        time.sleep(5)
    

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
        prompt_text = f"""
        # 役割: 
        あなたは純粋な映像クリエイターです。提供されたデータから音声などの音を含まない「映像（視覚的特徴）visual_instruction」のみを抽出して動画を生成してください。
        下記の事項を最優先で満たすようにしてください。
        
        # 絶対遵守事項:
        1. 画面内に「文字」「字幕」「タイトル」「テキスト」を一切含めないでください。
        2. 音声（BGM、効果音、ナレーション、環境音）を一切生成せず、無音の映像のみを構成してください。
        3. 提供されたデータに含まれる音声やテキストに関する記述は、動画生成において完全に無視してください。

        # 抽出対象データ:
        {json.dumps(prm_data, indent=2, ensure_ascii=False)}

        # 生成指示:
        上記のデータの内容を忠実に再現した、高品質な無音の実写映像を生成してください
        """
        
        st.info(f"⏳ パート {counter}/{total_parts} を生成中...")
        
        try:
            # 1. 動画生成リクエストの送信
            operation = safe_generate_video(prompt_text, current_video)
            op_display_id = getattr(operation, 'name', "processing")
            # 2. Operation IDを文字列として確実に取得
            while not operation.done:
                st.info(f"⏳ 生成中... (Operation: {op_display_id})")
                time.sleep(10)
                # 文字列ではなくオブジェクトをそのまま渡して更新
                operation = genai_client.operations.get(operation=operation)

            # 3. 完了後のレスポンス取得
            actual_op = operation
            while not actual_op.done:
                st.info(f"⏳ 生成中... (Operation: {actual_op})")
                time.sleep(10)
                # SDKの仕様に基づき、オブジェクトを渡して更新
                actual_op = genai_client.operations.get(operation=actual_op)

            # 4. レスポンスの確認
            # 完了した actual_op から response を取得
            if hasattr(actual_op, 'error') and actual_op.error:
                st.error(f"❌ 生成失敗 (APIエラー): {actual_op.error}")
                return

            # response 属性からデータを取得
            response = getattr(actual_op, 'response', None)
            
            # --- 修正：動画リストの取得をより確実に ---
            gen_videos = None
            if response:
                # オブジェクト形式でのアクセスを試行
                gen_videos = getattr(response, 'generated_videos', None)
                # もし辞書形式なら
                if gen_videos is None and isinstance(response, dict):
                    gen_videos = response.get('generatedVideos')

            if not gen_videos:
                # 動画が空の場合、詳細情報を表示
                st.error(f"❌ パート {counter}: 動画が生成されませんでした。")
                st.warning("考えられる理由: プロンプトが安全フィルター（Safety）に接触したか、モデルの制限です。")
                # 生のレスポンスをデバッグ出力
                st.json(str(actual_op)) 
                show_available_videos(completed_videos)
                return

            # 成功時：動画オブジェクトの取得
            generated_video_info = gen_videos[0]
            # generated_video_info は GeneratedVideo オブジェクト
            video_object = getattr(generated_video_info, 'video', None)
            
            if not video_object:
                st.error("❌ 動画オブジェクト（video）が見つかりません。")
                return
            
            completed_videos.append(video_object)

            if counter == total_parts:            
                st.write("📥 最終動画を保存中...")
                # ファイル名の取得（文字列またはオブジェクトの .name 属性）
                target_file_name = getattr(video_object, 'name', video_object)
                video_bytes = genai_client.files.download(file=target_file_name)
                
                output_path = "final_output.mp4"
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                
                # --- 【ここを修正】 ---
                # JSONの中身を一時ファイルとして保存する
                temp_json_path = "temp_video_config.json"
                json_content = st.session_state.jsonList[-1]

                # 1. 前後の余計な空白や改行を消す
                json_content = json_content.strip()

                # 2. Markdownのマークアップ（```json や ```）を徹底的に除去
                if json_content.startswith("```"):
                    # 最初の行（```jsonなど）を消す
                    lines = json_content.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    # 最後の行（```）を消す
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    json_content = "\n".join(lines).strip()

                # 3. もし冒頭に "json" という単語だけ残っていたら消す
                if json_content.lower().startswith("json"):
                    json_content = json_content[4:].strip()

                # 4. ファイルに書き出す
                with open(temp_json_path, "w", encoding="utf-8") as f:
                    f.write(json_content)

                # 書き出した中身が空でないかデバッグ確認（ターミナルに表示されます）
                print(f"DEBUG: Saved JSON length: {len(json_content)}")
                if len(json_content) == 0:
                    print("DEBUG ERROR: JSON content is empty!")

                # 保存した「パス」を渡す
                auto_add_subtitle_narration(output_path, temp_json_path)
                
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
veo_model = "veo-3.1-fast-generate-preview"

genai_client = genai.Client(api_key=googleKey)
setup_app()
display_chat_history()
handle_chat()