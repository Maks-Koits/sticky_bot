import logging
import os
import subprocess
import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ContentType

API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    raise ValueError("API_TOKEN is missing. Please pass it via environment variables.")

BASE_UPLOAD = 'uploads'
OUTPUT_FOLDER = 'outputs'
MAX_FILE_SIZE_MB = 50

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

os.makedirs(BASE_UPLOAD, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def get_user_dir(user_id: int) -> str:
    user_dir = os.path.join(BASE_UPLOAD, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def cleanup_user_files(user_dir: str):
    try:
        for file in os.listdir(user_dir):
            os.remove(os.path.join(user_dir, file))
        os.rmdir(user_dir)
    except Exception as e:
        logging.warning(f"Cleanup error: {e}")


@router.message(Command(commands=["start"]))
async def start(message: Message):
    await message.answer("Здравствуйте! Отправьте фото, затем аудио/видео и название.")


@router.message(lambda message: message.photo)
async def handle_photo(message: Message):
    user_dir = get_user_dir(message.from_user.id)
    file_id = message.photo[-1].file_id
    file_path = os.path.join(user_dir, "image.jpg")

    await bot.download(file_id, file_path)
    await message.answer("Фото получено. Теперь отправьте аудио или видео.")


@router.message(lambda message: message.voice or message.audio or message.video or message.document)
async def handle_audio_or_video(message: Message):
    user_dir = get_user_dir(message.from_user.id)
    file = None
    extension = "bin"

    if message.voice:
        file = message.voice
        extension = "ogg"
    elif message.audio:
        file = message.audio
        extension = "mp3"
    elif message.video:
        file = message.video
        extension = "mp4"
    elif message.document:
        file = message.document
        mime = file.mime_type
        if mime:
            extension = mime.split("/")[-1]

    # Ограничение размера
    if file.file_size and file.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.answer(f"Файл слишком большой. Максимальный размер — {MAX_FILE_SIZE_MB}MB.")
        return

    input_path = os.path.join(user_dir, f"input.{extension}")
    await bot.download(file.file_id, input_path)

    # Конвертируем в mp3
    audio_mp3 = os.path.join(user_dir, "audio.mp3")
    convert_command = ['ffmpeg', '-y', '-i', input_path, audio_mp3]
    subprocess.run(convert_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    await message.answer("Аудио или видео получено. Теперь отправьте название видео.")


@router.message(lambda message: message.text)
async def handle_title(message: Message):
    user_dir = get_user_dir(message.from_user.id)
    image_path = os.path.join(user_dir, "image.jpg")
    audio_mp3 = os.path.join(user_dir, "audio.mp3")

    if not os.path.exists(image_path) or not os.path.exists(audio_mp3):
        await message.answer("Не все файлы загружены. Пожалуйста, отправьте фото, аудио/видео и название.")
        return

    title = message.text
    output_path = os.path.join(OUTPUT_FOLDER, f"{message.from_user.id}_{title}.mp4")

    # Сообщение об обработке
    processing_msg = await message.answer("⏳ Идёт обработка видео, пожалуйста, подождите...")

    command = [
        'ffmpeg',
        '-y',
        '-loop', '1',
        '-i', image_path,
        '-i', audio_mp3,
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        output_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        video = FSInputFile(output_path)
        await bot.send_video(message.chat.id, video, caption=f"🎬 Ваше видео: {title}.mp4")
    except Exception as e:
        await message.answer("⚠️ Не удалось отправить видео.")
        logging.error(f"Send video error: {e}")

    await processing_msg.delete()
    cleanup_user_files(user_dir)
    try:
        os.remove(output_path)
    except:
        pass


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
