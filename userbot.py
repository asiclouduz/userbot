from telethon import TelegramClient, events
import google.generativeai as genai
from datetime import datetime
import pytz
import sqlite3
from googletrans import Translator
import locale

# Set up your API keys

# Configure the Gemini AI
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash-8b-latest")

# Set timezone to Tashkent time
tashkent_tz = pytz.timezone('Asia/Tashkent')

# Set locale to Uzbek for correct day names
locale.setlocale(locale.LC_TIME, 'uz_UZ.UTF-8')

# Create and connect to SQLite database
conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# Create the 'users' and 'blocked' tables
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    last_access_date TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS blocked (
    user_id INTEGER PRIMARY KEY,
    name TEXT
)''')

# Initialize the Telegram client
client = TelegramClient('userbot', api_id, api_hash)

# Initialize Google Translate API
translator = Translator()

# Store the last reply text for each user
last_reply = {}

# Function to generate a response using Gemini AI
def gemini_ai_response(prompt):
    try:
        print(f"[Gemini AI] Received prompt: {prompt}")
        response = model.generate_content(prompt)
        result = response.text.strip()
        print(f"[Gemini AI] Response: {result}")
        return result
    except Exception as e:
        print(f"[Gemini AI] Error occurred: {e}")
        return f"Error: {e}"

# Function to translate text
def translate_text(text, target_language="uz"):
    try:
        translation = translator.translate(text, dest=target_language)
        return translation.text
    except Exception as e:
        print(f"[Translate] Error occurred: {e}")
        return "Error: Translation failed."

# Event handler for incoming messages
@client.on(events.NewMessage)
async def handle_message(event):
    user_id = event.sender_id

    # Check if the message is from a group and if it's the '.ai' command
    if event.is_group and event.message.text.lower().startswith('.ai'):
        await event.reply("Siz faqat shaxsiy chatda foydalanasiz.")
        return  # If it's from a group, do nothing further for '.ai'

    cursor.execute("SELECT * FROM blocked WHERE user_id = ?", (user_id,))
    blocked_result = cursor.fetchone()
    if blocked_result:
        await event.reply("Siz bloklangansiz. Botdan foydalana olmaysiz.")
        return

    if event.sender:
        user_name = event.sender.username or "No username"
    else:
        user_name = "No username"

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result is None:
        cursor.execute("INSERT INTO users (user_id, name, last_access_date) VALUES (?, ?, ?)", 
                       (user_id, user_name, datetime.now(tashkent_tz).strftime('%Y-%m-%d')))
        conn.commit()
        print(f"Foydalanuvchi ID: {user_id} va ismi: {user_name} users jadvaliga qo'shildi.")
    else:
        print(f"Foydalanuvchi ID: {user_id} va ismi: {user_name} users jadvalida bor.")

    if event.message.text.lower() == "salom":
        await event.reply("Assalomu alekum!")

    elif event.message.text.lower() == '.time':
        current_time = datetime.now(tashkent_tz).strftime("%H:%M:%S, %d %b %Y")
        day_of_week = datetime.now(tashkent_tz).strftime("%A")
        await event.reply(f"Hozirgi vaqt: {current_time}\nHozirgi kun: {day_of_week}")
    
    elif event.message.text.lower().startswith('.ai'):
        user_input = event.message.text.split('.ai', 1)[1].strip()
        if user_input:
            response_message = await event.reply("Javob qidiryapman...")
            response = gemini_ai_response(user_input)
            last_reply[user_id] = response
            await event.client.edit_message(response_message, response)
        else:
            await event.reply("Iltimos, AI ga so'rov yuboring. Masalan: .ai Yangi yil haqida gapir.")
    
    elif event.message.text.lower().startswith('.block'):
        if str(user_id) == owner:
            blocked_user_id = event.message.text.split('.block', 1)[1].strip()
            cursor.execute("INSERT OR IGNORE INTO blocked (user_id, name) VALUES (?, ?)", (blocked_user_id, user_name))
            conn.commit()
            await event.reply(f"{blocked_user_id} endi bloklandi.")
        else:
            await event.reply("Siz faqat egasi bloklashi mumkin.")
    
    if event.message.text.lower() == ".uz":
        if user_id in last_reply:
            text_to_translate = last_reply[user_id]
            translated_text = translate_text(text_to_translate, target_language="uz")
            await event.reply(f"Tarjima: {translated_text}")
        else:
            await event.reply("Sizning javobingiz mavjud emas. Iltimos, botdan javob kuting va keyin .uz yozing.")
    
# Start the client
print("Starting Telegram Userbot...")
with client:
    try:
        print("[Client] Running userbot. Waiting for events...")
        client.run_until_disconnected()
    except Exception as e:
        print(f"[Client] Error occurred: {e}")
