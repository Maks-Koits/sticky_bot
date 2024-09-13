import logging
import os
import subprocess
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router

# Получаем переменную API_TOKEN из параметров окружения
API_TOKEN = os.getenv('API_TOKEN')

# Проверяем, что токен был передан
if not API_TOKEN:
    raise ValueError("API_TOKEN is missing. Please pass it via environment variables.")

# Задаем папки для загрузки и вывода файлов
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'

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


# Обработчик для получения фото
@router.message()
async def handle_photo(message: types.Message):
    if message.photo:
        file_id = message.photo[-1].file_id
        file = await bot.get_file(file_id)
        await file.download(f"{UPLOAD_FOLDER}/image.jpg")
        await message.reply("Фото получено. Пожалуйста, отправьте аудиофайл и название.")
    else:
        await message.reply("Пожалуйста, отправьте фото.")


# Обработчик для получения аудиофайла
@router.message()
async def handle_audio(message: types.Message):
    if message.audio:
        file_id = message.audio.file_id
        file = await bot.get_file(file_id)
        await file.download(f"{UPLOAD_FOLDER}/audio.mp3")
        await message.reply("Аудиофайл получен. Пожалуйста, отправьте название видео.")
    else:
        await message.reply("Пожалуйста, отправьте аудиофайл.")


# Обработчик для получения названия видео и создания видеофайла
@router.message()
async def handle_title(message: types.Message):
    if not os.path.exists(f"{UPLOAD_FOLDER}/image.jpg") or not os.path.exists(f"{UPLOAD_FOLDER}/audio.mp3"):
        await message.reply("Не все файлы загружены. Пожалуйста, отправьте фото, аудиофайл и название.")
        return

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


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())