import asyncio
from pathlib import Path
from typing import Optional
import whisper
from openai import AsyncOpenAI
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.utils.i18n import gettext as _
from config.settings import settings


client = AsyncOpenAI(api_key=settings.OPENAI_API_TOKEN)
audio_router = Router()

model = whisper.load_model(settings.WHISPER_MODEL)

def get_user_temp_dir(user_id: int) -> Path:
    temp_dir = Path("temp") / str(user_id)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

async def download_file(bot, file_id: str, destination: Path) -> bool:
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination)
        return True
    except Exception as e:
        print(f"Download error: {e}")
        return False

async def convert_audio_to_text(file_path: Path) -> Optional[str]:
    try:
        result = model.transcribe(str(file_path))
        return result["text"]
    except Exception as e:
        print(f"Transcription error: {e}")
        return None

async def get_assistant_response(text: str) -> Optional[str]:
    try:
        assistant = await client.beta.assistants.create(
            instructions=settings.ASSISTANT_INSTRUCTIONS,
            name=settings.ASSISTANT_NAME,
            model=settings.OPENAI_MODEL,
        )

        thread = await client.beta.threads.create()
        await client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=text
        )
        
        run = await client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        while True:
            run_status = await client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            await asyncio.sleep(1)
        
        messages = await client.beta.threads.messages.list(thread.id)
        return messages.data[0].content[0].text.value
    except Exception as e:
        print(f"Assistant error: {e}")
        return None

async def text_to_speech(text: str, output_path: Path) -> bool:
    try:
        response = await client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )
        await response.astream_to_file(output_path)
        return True
    except Exception as e:
        print(f"TTS error: {e}")
        return False

@audio_router.message(Command("start"))
async def handle_start(message: Message):
    start_text = _(
        "🎉 Добро пожаловать! 🎧",
        "Отправьте голосовое сообщение или аудиофайл, и давайте пообщаемся!"
    )
    await message.answer(start_text)

@audio_router.message(F.voice | F.audio | F.document)
async def handle_audio(message: Message, bot):
    user_id = message.from_user.id
    temp_dir = get_user_temp_dir(user_id)
    
    if message.voice:
        file_id = message.voice.file_id
        filename = f"voice_{file_id}.ogg"
    elif message.audio:
        file_id = message.audio.file_id
        filename = message.audio.file_name or f"audio_{file_id}.mp3"
    elif message.document:
        if message.document.mime_type != "audio/mpeg":
            await message.reply("Пожалуйста, отправьте MP3 файл")
            return
        file_id = message.document.file_id
        filename = message.document.file_name or f"document_{file_id}.mp3"
    else:
        return

    input_path = temp_dir / filename
    output_path = temp_dir / "response.mp3"

    if not await download_file(bot, file_id, input_path):
        await message.reply("❌ Ошибка загрузки файла")
        return

    user_text = await convert_audio_to_text(input_path)
    if not user_text:
        await message.reply("❌ Ошибка расшифровки аудио")
        return

    assistant_response = await get_assistant_response(user_text)
    if not assistant_response:
        await message.reply("❌ Ошибка обработки запроса")
        return

    if not await text_to_speech(assistant_response, output_path):
        await message.reply("❌ Ошибка генерации аудио")
        return

    try:
        await message.reply_voice(FSInputFile(path=output_path))
    except Exception as e:
        print(f"Error sending audio: {e}")
        await message.reply(f"❌ Ошибка отправки")
    finally:
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)