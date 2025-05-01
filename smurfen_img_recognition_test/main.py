import discord
from discord.ext import commands
import pytesseract
from PIL import Image, ImageFilter, ImageOps
import os
import requests

TOKEN = 'MTM2NzQzODcyNTY4NDEzODEyNQ.GAlf8l.QXKBA2cdDbp3wRBmgSrUCVwuMwzShlPw5u1OZY'
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# === Preprocessing functie ===
def preprocess_image(img_path):
    img = Image.open(img_path).convert("L")  # Grayscale
    img = ImageOps.invert(img)               # Inverteer kleuren
    img = img.point(lambda x: 0 if x < 150 else 255)  # Binariseer
    img = img.filter(ImageFilter.SHARPEN)    # Verscherpen
    return img

# === OCR functie ===
def extract_text_from_image(image_path):
    preprocessed_img = preprocess_image(image_path)
    text = pytesseract.image_to_string(preprocessed_img, config="--psm 6 --oem 3")
    return text.strip()

# === Event: Bij afbeelding upload ===
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check of er een afbeelding in de bijlagen zit
    if message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
                file_path = f"temp_{attachment.filename}"
                await attachment.save(file_path)
                try:
                    await message.channel.send("🔍 Bezig met tekstherkenning...")
                    extracted_text = extract_text_from_image(file_path)
                    if extracted_text:
                        await message.channel.send(f"📝 Herkende tekst:\n```{extracted_text}```")
                    else:
                        await message.channel.send("❌ Geen leesbare tekst gevonden.")
                except Exception as e:
                    await message.channel.send(f"⚠️ Er ging iets mis: {e}")
                finally:
                    os.remove(file_path)

    await bot.process_commands(message)

# === Start de bot ===
@bot.event
async def on_ready():
    print(f"✅ Bot verbonden als {bot.user}")

bot.run(TOKEN)
