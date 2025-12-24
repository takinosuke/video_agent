from google import genai
from google.genai import types
import time

API_KEY = "AIzaSyBnghKQEeOLS2Fov7pwQVTjiPSnf1rU2ps"
 
client = genai.Client(api_key=API_KEY)

prompt = "森の中を走る犬を追いかける、シネマティックなドローンショットの動画。"

config = types.GenerateVideosConfig(
    number_of_videos=1,      # 生成する本数
    resolution="720p",       # "720p" / "1080p" など
    aspect_ratio="16:9",     # アスペクト比
    # その他: duration_seconds, reference_images, allow_adult などのフィールドがモデルでサポートされていれば指定
)

operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt=prompt,
    config=config,           # ← ここで渡す
)

while not operation.done:
    print("動画生成中...")
    time.sleep(10)
    operation = client.operations.get(operation)

video = operation.response.generated_videos[0]
client.files.download(file=video.video)
video.video.save("output.mp4")
