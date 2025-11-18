import sounddevice as sd
import wavio
import whisper
import pyttsx3
import sqlite3
from datetime import datetime, timedelta
import dateparser
import re
import time
import os

# ------------------- SETTINGS -------------------
FILENAME = "recorded.wav"
FS = 44100
DURATION = 6
DB_FILE = "appointments.db"

# ------------------- FIX 1: Robust TTS Engine -------------------
# We rebuild the engine before EVERY speech to avoid the Windows freeze bug
def speak(text):
    print(f"Assistant: {text}")
    try:
        # Create a fresh engine instance every time (fixes Windows silence bug)
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.setProperty('volume', 1.0)
        
        # Optional: Try to set Indian English or best available voice
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'india' in voice.name.lower() or 'zira' in voice.name.lower() or 'david' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        # No need for time.sleep() when we recreate engine
    except Exception as e:
        print(f"TTS Error: {e}")

# ------------------- REST OF YOUR ORIGINAL CODE (with fixes) -------------------
print("Loading Whisper model...")
model = whisper.load_model("medium")  # or "base" for faster speed
print("Model loaded!")

# ------------------- FIX 2: Recreate DB properly -------------------
def init_db():
    # Delete old DB if structure changed (safe during development)
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("Old database deleted and will be recreated...")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            vehicle_no TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            UNIQUE(vehicle_no)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# ------------------- Recording & Transcription -------------------
def record_audio():
    print("   Listening... (speak now)")
    data = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype='int16')
    sd.wait()
    wavio.write(FILENAME, data, FS, sampwidth=2)

def listen_and_transcribe(prompt=None):
    if prompt:
        speak(prompt)
    
    for _ in range(3):
        record_audio()
        try:
            result = model.transcribe(FILENAME, language="en")
            text = result["text"].strip()
            if text:
                speak(f"You said: {text}")
                return text.lower()
            else:
                speak("I didn't hear anything clearly. Please speak again.")
        except Exception as e:
            print(f"Whisper error: {e}")
            speak("Sorry, there was a problem understanding you.")
    
    speak("I couldn't understand after a few tries. Let's continue anyway.")
    return ""

# ------------------- Confirmation Helper -------------------
def get_confirmed_input(prompt):
    while True:
        text = listen_and_transcribe(prompt)
        if not text:
            continue
        speak("Is this correct? Say yes or no.")
        confirm = listen_and_transcribe()
        if any(word in confirm for word in ["yes", "haan", "ji", "correct", "right"]):
            speak("Okay, confirmed!")
            return text
        else:
            speak("Alright, let's try again.")

# ------------------- Time Normalization -------------------
def normalize_time(t):
    parsed = dateparser.parse(t, settings={'PREFER_DAY_OF_MONTH': 'current'})
    return parsed.strftime("%H:%M") if parsed else None

def get_confirmed_time(prompt):
    while True:
        raw = get_confirmed_input(prompt)
        norm = normalize_time(raw)
        if norm:
            return norm
        speak("I didn't understand the time. Please say like 10 AM, 2 PM, or 11 30.")

# ------------------- Slot Finder -------------------
def find_next_available_slot(date_str, time_str):
    base = dateparser.parse(date_str) or datetime.now()
    check_date = base.date()
    
    for _ in range(30):
        date_key = check_date.strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT time FROM appointments WHERE date=?", (date_key,))
        booked = [row[0] for row in c.fetchall()]
        conn.close()
        
        slots = ["10:00", "13:00", "16:00"]
        for slot in slots:
            if slot not in booked:
                return date_key, slot
        check_date += timedelta(days=1)
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return tomorrow, "10:00"

# ------------------- DB Operations -------------------
def add_appointment(username, vehicle_no, date, time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO appointments (username, vehicle_no, date, time) VALUES (?, ?, ?, ?)",
                  (username.title(), vehicle_no.upper(), date, time))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        speak("This vehicle already has an appointment.")
        return False
    finally:
        conn.close()

def get_appointment(vehicle_no):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, date, time FROM appointments WHERE vehicle_no=?", (vehicle_no.upper(),))
    result = c.fetchone()
    conn.close()
    return result

# ------------------- Main Assistant -------------------
def car_center_assistant():
    init_db()  # This will fix the DB column issue
    
    speak("Good morning! Welcome to Deewanshi Car Center.")
    
    user_name = get_confirmed_input("May I know your name please?")
    
    while True:
        action = listen_and_transcribe(
            "How can I help you today? Say 'book appointment' or 'car status'."
        )
        
        if "book" in action or "appointment" in action:
            vehicle_no = get_confirmed_input("Please tell me your vehicle number.")
            pref_date = get_confirmed_input("What date would you like? For example, tomorrow or 20 November.")
            pref_time = get_confirmed_time("What time would you prefer?")
            
            avail_date, avail_time = find_next_available_slot(pref_date, pref_time)
            
            if add_appointment(user_name, vehicle_no, avail_date, avail_time):
                nice_date = datetime.strptime(avail_date, "%Y-%m-%d").strftime("%d %B %Y")
                speak(f"Excellent! Your appointment is booked for {nice_date} at {avail_time}.")
                speak(f"We will take good care of your car {vehicle_no.upper()}. Thank you!")
        
        elif "status" in action or "ready" in action or "car" in action:
            vehicle_no = get_confirmed_input("Please say your vehicle number.")
            appt = get_appointment(vehicle_no)
            if appt:
                name, date, time = appt
                nice_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d %B %Y")
                speak(f"Your car will be ready on {nice_date} at {time}. Have a great day!")
            else:
                speak("Sorry, no appointment found for this vehicle.")
        
        else:
            speak("Sorry, I didn't understand. Please say book appointment or car status.")
        
        again = listen_and_transcribe("Do you need any other help?")
        if "no" in again or "thank" in again or "bye" in again:
            speak(f"Thank you {user_name.title()}! Have a wonderful day!")
            break

# ------------------- RUN -------------------
if __name__ == "__main__":
    try:
        if os.path.exists(FILENAME):
            os.remove(FILENAME)
        car_center_assistant()
    except KeyboardInterrupt:
        speak("Thank you! Goodbye!")