import os
import asyncio
import subprocess
from pyrogram import Client, filters
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

TMP = "downloads"
os.makedirs(TMP, exist_ok=True)

QUALITY_MAP = {
    "480p": "854:480",
    "720p": "1280:720",
    "1080p": "1920:1080",
    "2160p": "3840:2160"
}

user_state = {}

@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply("Send me any video.")

@app.on_message(filters.video)
async def get_video(_, msg):
    chat = msg.chat.id
    file_id = msg.video.file_id

    user_state[chat] = {"file_id": file_id}

    await msg.reply("Send new file name (without .mp4)")

@app.on_message(filters.text)
async def process_name(_, msg):
    chat = msg.chat.id
    if chat not in user_state:
        return

    if "name" not in user_state[chat]:
        user_state[chat]["name"] = msg.text + ".mp4"
        await msg.reply("Choose quality:\n480p / 720p / 1080p / 2160p")
        return

    if "quality" not in user_state[chat]:
        q = msg.text
        if q not in QUALITY_MAP:
            await msg.reply("Choose only: 480p / 720p / 1080p / 2160p")
            return

        user_state[chat]["quality"] = q
        await msg.reply("Send a thumbnail (photo) or type /skip")
        return

@app.on_message(filters.photo)
async def get_thumbnail(_, msg):
    chat = msg.chat.id
    if chat not in user_state:
        return

    path = os.path.join(TMP, f"thumb_{chat}.jpg")
    await msg.download(path)
    user_state[chat]["thumb"] = path

    await convert_and_send(chat, msg)

@app.on_message(filters.command("skip"))
async def skip_thumb(_, msg):
    chat = msg.chat.id
    await convert_and_send(chat, msg)

async def convert_and_send(chat, msg):
    state = user_state.get(chat)
    if not state:
        return

    file_path = os.path.join(TMP, f"in_{chat}.mp4")
    out_path = os.path.join(TMP, f"out_{chat}.mp4")

    await msg.reply("Downloading video...")

    await app.download_media(state["file_id"], file_path)

    width_height = QUALITY_MAP[state["quality"]]

    await msg.reply("Converting... Please wait...")

    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-vf", f"scale={width_height}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        out_path
    ]

    subprocess.run(cmd)

    await msg.reply("Uploading...")

    await app.send_video(
        chat_id=chat,
        video=out_path,
        file_name=state["name"],
        caption=f"Converted to {state['quality']}",
        thumb=state.get("thumb")
    )

    os.remove(file_path)
    os.remove(out_path)
    if state.get("thumb"):
        os.remove(state["thumb"])

    del user_state[chat]

app.run()
