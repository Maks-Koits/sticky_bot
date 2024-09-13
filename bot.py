import logging
import os
import subprocess
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router

# Получаем переменные окружения
API_TOKEN = os.getenv('API_TOKEN')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')

# Инициализация бота и диспетчера
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Создаем папки, если их еще нет
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)


@router.message(Command("start"))
async def start(message: types.Message):
    await message.reply("Здравствуйте! Отправьте фото, затем аудиофайл и название.")


@router.message(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    await file.download(f"{UPLOAD_FOLDER}/image.jpg")
    await message.reply("Фото получено. Пожалуйста, отправьте аудиофайл и название.")


@router.message(content_types=types.ContentType.AUDIO)
async def handle_audio(message: types.Message):
    file_id = message.audio.file_id
    file = await bot.get_file(file_id)
    await file.download(f"{UPLOAD_FOLDER}/audio.mp3")
    await message.reply("Аудиофайл получен. Пожалуйста, отправьте название видео.")


@router.message()
async def handle_title(message: types.Message):
    if os.path.exists(f"{UPLOAD_FOLDER}/image.jpg") and os.path.exists(f"{UPLOAD_FOLDER}/audio.mp3"):
        title = message.text
        output_file = f"{OUTPUT_FOLDER}/{title}.mp4"
        command = [
            'ffmpeg',
            '-loop', '1',
            '-i', f"{UPLOAD_FOLDER}/image.jpg",
            '-i', f"{UPLOAD_FOLDER}/audio.mp3",
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            output_file
        ]
        subprocess.run(command)

        video = FSInputFile(output_file)
        await bot.send_video(message.chat.id, video, caption=f"Вот ваше видео: {title}.mp4")

        # Удаление временных файлов
        os.remove(f"{UPLOAD_FOLDER}/image.jpg")
        os.remove(f"{UPLOAD_FOLDER}/audio.mp3")
        os.remove(output_file)
    else:
        await message.reply("Не все файлы загружены. Пожалуйста, отправьте фото, аудиофайл и название.")


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())