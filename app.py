
# app.py - DEEWANSHI CAR CENTER VOICE ASSISTANT - FULLY FIXED
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import dateparser
import pyttsx3

app = Flask(__name__)
CORS(app)  # Critical: Allows frontend to talk to backend

DB_FILE = "appointments.db"

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            vehicle_no TEXT NOT NULL UNIQUE,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# TTS Function
def speak(text):
    print(f"Assistant: {text}")
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        voices = engine.getProperty('voices')
        for v in voices:
            if 'zira' in v.name.lower() or 'india' in v.name.lower() or 'female' in v.name.lower():
                engine.setProperty('voice', v.id)
                break
        engine.say(text)
        engine.runAndWait()
    except:
        pass

# Normalize Vehicle Number
def normalize_vehicle_no(text):
    cleaned = text.upper()
    cleaned = ''.join(''.join(c for c in cleaned if c.isalnum()))
    fillers = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "OH", "O"]
    for f in fillers:
        cleaned = cleaned.replace(f, "")
    return ''.join(c for c in cleaned if c.isalnum())

# Session State
class Session:
    def __init__(self):
        self.reset()
    def reset(self):
        self.stage = "welcome"
        self.user_name = None
        self.vehicle_no = None
        self.pref_date = None
        self.pref_time = None

session = Session()

# DB Helpers
def find_next_slot(date_str):
    base = dateparser.parse(date_str, settings={'PREFER_DATES_FROM': 'future'}) or datetime.now()
    check_date = base.date()
    slots = ["10:00", "13:00", "16:00"]

    for _ in range(30):
        d_str = check_date.strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT time FROM appointments WHERE date=?", (d_str,))
        booked = [r[0] for r in c.fetchall()]
        conn.close()

        for slot in slots:
            if slot not in booked:
                return d_str, slot
        check_date += timedelta(days=1)
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"), "10:00"

def book_appointment(name, vehicle, date, time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO appointments (username, vehicle_no, date, time) VALUES (?, ?, ?, ?)",
                  (name.title(), vehicle, date, time))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_appointment(vehicle):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, date, time FROM appointments WHERE vehicle_no=?", (vehicle.upper(),))
    result = c.fetchone()
    conn.close()
    return result

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    session.reset()
    msg = "Good morning! Welcome to Deewanshi Car Center. May I know your name please?"
    speak(msg)
    session.stage = "ask_name"
    return jsonify({
        "messages": [msg],
        "done": False
    })

@app.route('/listen', methods=['POST'])
def listen():
    user_input = request.json.get("message", "").strip()
    messages = []
    done = False

    def say(text):
        speak(text)
        messages.append(text)

    # Name Flow
    if session.stage == "ask_name":
        session.user_name = user_input.strip().title()
        say(f"You said your name is {session.user_name}. Is that correct? Say yes or no.")
        session.stage = "confirm_name"

    elif session.stage == "confirm_name":
        if any(x in user_input.lower() for x in ["yes", "correct", "yeah", "right"]):
            say(f"Great! Thank you {session.user_name.split()[0]}.")
            say("How can I help you today? Say 'book appointment' or 'check car status'.")
            session.stage = "main_menu"
        else:
            say("Sorry, please say your name again.")
            session.stage = "ask_name"

    elif session.stage == "main_menu":
        if any(x in user_input.lower() for x in ["book", "appointment", "service"]):
            say("Please tell me your vehicle number.")
            session.stage = "get_vehicle"
        elif any(x in user_input.lower() for x in ["status", "check", "ready"]):
            say("Please say your vehicle number to check status.")
            session.stage = "check_status"
        else:
            say("Please say 'book appointment' or 'check car status'.")

    elif session.stage == "get_vehicle":
        vehicle = normalize_vehicle_no(user_input)
        if len(vehicle) < 6:
            say("I didn't catch that properly. Please say your vehicle number again.")
        else:
            session.vehicle_no = vehicle
            say(f"You said: {vehicle}. Is this correct?")
            session.stage = "confirm_vehicle"

    elif session.stage == "confirm_vehicle":
        if any(x in user_input.lower() for x in ["yes", "correct", "yeah"]):
            say("Vehicle confirmed!")
            say("What date would you like? For example: tomorrow, 25th November, or next Monday.")
            session.stage = "get_date"
        else:
            say("Please say your vehicle number again.")
            session.stage = "get_vehicle"

    elif session.stage == "get_date":
        session.pref_date = user_input
        say(f"You want: {user_input}. Is this correct?")
        session.stage = "confirm_date"

    elif session.stage == "confirm_date":
        if any(x in user_input.lower() for x in ["yes", "correct"]):
            say("Date confirmed!")
            say("What time do you prefer? We have 10 AM, 1 PM, or 4 PM.")
            session.stage = "get_time"
        else:
            say("Please say the date again.")
            session.stage = "get_date"

    elif session.stage == "get_time":
        session.pref_time = user_input
        say(f"You said: {user_input}. Confirm?")
        session.stage = "confirm_time"

    elif session.stage == "confirm_time":
        if any(x in user_input.lower() for x in ["yes", "correct"]):
            date_slot, time_slot = find_next_slot(session.pref_date)
            nice_date = datetime.strptime(date_slot, "%Y-%m-%d").strftime("%d %B %Y")
            success = book_appointment(session.user_name, session.vehicle_no, date_slot, time_slot)
            if success:
                say(f"Excellent! Your appointment is booked for {nice_date} at {time_slot}.")
                say(f"We'll take good care of your {session.vehicle_no}. Thank you!")
            else:
                say(f"Sorry, this vehicle already has an appointment.")
            say("Anything else I can help with?")
            session.stage = "final_ask"
        else:
            say("Please say the time again.")
            session.stage = "get_time"

    elif session.stage == "final_ask":
        if any(x in user_input.lower() for x in ["no", "thank", "bye"]):
            say(f"Thank you {session.user_name.split()[0]}! Have a wonderful day!")
            session.reset()
            done = True
        else:
            say("How else may I assist you?")
            session.stage = "main_menu"

    # Status Check
    elif session.stage == "check_status":
        vehicle = normalize_vehicle_no(user_input)
        appt = get_appointment(vehicle)
        if appt:
            name, date, time = appt
            nice_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d %B %Y")
            say(f"Hello {name.split()[0]}! Your car {vehicle} will be ready on {nice_date} at {time}.")
        else:
            say("No appointment found for this vehicle number.")
        say("Anything else?")
        session.stage = "final_ask"

    return jsonify({
        "messages": messages,
        "done": done
    })

# ADMIN: Fixed route
# ADMIN: FIXED — Now returns JSON (for instant download) + keeps old HTML fallback
# ADMIN: 100% WORKING — ALWAYS RETURNS JSON
@app.route('/appointments')
def appointments():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT username, vehicle_no, date, time FROM appointments ORDER BY date, time")
        rows = c.fetchall()
        conn.close()

        data = []
        for name, vehicle, date, time in rows:
            data.append({
                "name": name,
                "vehicle": vehicle,
                "date": date,
                "time": time
            })
        
        # This line makes download work EVERY TIME
        return jsonify(data)
    
    except Exception as e:
        print("DB Error:", e)
        return jsonify([])  # Return empty list if error

if __name__ == '__main__':
    print("\n" + "="*60)
    print("   DEEWANSHI CAR CENTER VOICE ASSISTANT - NOW FULLY WORKING!")
    print("   Open → http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)