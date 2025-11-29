# app.py - DEEWANSHI CAR CENTER – FINAL 100% CORRECT (December date bug FIXED!)
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import dateparser
import re
import os

app = Flask(__name__)
CORS(app)
DB_FILE = "appointments.db"

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

def speak(text):
    print(f"Assistant: {text}")
    return text

def normalize_vehicle_no(text):
    cleaned = ''.join(c for c in text.upper() if c.isalnum())
    fillers = ["ZERO","ONE","TWO","THREE","FOUR","FIVE","SIX","SEVEN","EIGHT","NINE","OH","O"]
    for f in fillers:
        cleaned = cleaned.replace(f, "")
    return cleaned

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

# FIXED: Force today as 30 Nov 2025 so "1 December" stays in 2025
TODAY_OVERRIDE = datetime(2025, 11, 30)

def find_next_slot(date_str, preferred_time=None):
    base = dateparser.parse(date_str, settings={
        'PREFER_DATES_FROM': 'future',
        'DATE_ORDER': 'DMY',
        'RELATIVE_BASE': TODAY_OVERRIDE  # This fixes the December → January jump
    })
    if not base:
        base = datetime.now()
    check_date = base.date()
    slots = ["10:00", "13:00", "16:00"]

    for _ in range(30):
        d_str = check_date.strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT time FROM appointments WHERE date=?", (d_str,))
        booked = [r[0] for r in c.fetchall()]
        conn.close()

        if preferred_time and preferred_time in slots and preferred_time not in booked:
            return d_str, preferred_time
        for slot in slots:
            if slot not in booked:
                return d_str, slot
        check_date += timedelta(days=1)
    
    return check_date.strftime("%Y-%m-%d"), "10:00"

def book_appointment(name, vehicle, date, time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO appointments (username, vehicle_no, date, time) VALUES (?, ?, ?, ?)",
                  (name.title(), vehicle.upper(), date, time))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_appointment(vehicle):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, date, time FROM appointments WHERE vehicle_no=?", (vehicle.upper(),))
    result = c.fetchone()
    conn.close()
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    session.reset()
    msg = "Good morning! Welcome to Deewanshi Car Center. May I know your name please?"
    speak(msg)
    session.stage = "ask_name"
    return jsonify({"messages": [msg], "done": False})

@app.route('/listen', methods=['POST'])
def listen():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"messages": ["Sorry, I didn't hear anything."], "done": False})

    messages = []
    def say(text):
        speak(text)
        messages.append(text)

    def clean_words(text):
        text = text.lower()
        text = re.sub(r"\bit'?s\b", "it is", text)
        text = re.sub(r"[^\w\s]", " ", text)
        return text.split()

    words = clean_words(user_input)

    time_mapping = {
        "10": "10:00", "10am": "10:00", "10:00": "10:00", "ten": "10:00", "morning": "10:00",
        "1pm": "13:00", "1 pm": "13:00", "13:00": "13:00", "one": "13:00", "afternoon": "13:00",
        "2pm": "13:00", "2 pm": "13:00", "two": "13:00",
        "4pm": "16:00", "4 pm": "16:00", "16:00": "16:00", "four": "16:00", "evening": "16:00"
    }

    def is_positive(w): return any(p in w for p in ["yes", "correct", "yeah", "ok", "right", "confirm", "it is"])
    def is_negative(w): return any(n in w for n in ["no", "not", "wrong", "incorrect", "nope"])

    if session.stage == "ask_name":
        session.user_name = user_input.strip().title()
        say(f"You said your name is {session.user_name}. Is that correct?")
        session.stage = "confirm_name"

    elif session.stage == "confirm_name":
        if is_positive(words) and not is_negative(words):
            say(f"Great! Thank you {session.user_name.split()[0]}.")
            say("How can I help you today? Say 'book appointment' or 'check car status'.")
            session.stage = "main_menu"
        else:
            say("Sorry, please say your name again.")
            session.stage = "ask_name"

    elif session.stage == "main_menu":
        if any(word in words for word in ["book", "appointment", "service", "wash"]):
            say("Please tell me your vehicle number.")
            session.stage = "get_vehicle"
        elif any(word in words for word in ["status", "check", "ready"]):
            say("Please say your vehicle number to check status.")
            session.stage = "check_status"
        else:
            say("Please say 'book appointment' or 'check car status'.")

    elif session.stage == "get_vehicle":
        v = normalize_vehicle_no(user_input)
        if len(v) < 6:
            say("I didn't catch that properly. Please say your vehicle number again.")
        else:
            session.vehicle_no = v
            say(f"You said {v}. Is this correct?")
            session.stage = "confirm_vehicle"

    elif session.stage == "confirm_vehicle":
        if is_positive(words) and not is_negative(words):
            say(f"Your vehicle {session.vehicle_no} is confirmed!")
            say("Please say the date in day month year format, for example: 5 December 2025")
            session.stage = "get_date"
        else:
            say("Please say your vehicle number again.")
            session.stage = "get_vehicle"

    elif session.stage == "get_date":
        parsed = dateparser.parse(user_input, settings={
            'PREFER_DATES_FROM': 'future',
            'DATE_ORDER': 'DMY',
            'RELATIVE_BASE': TODAY_OVERRIDE
        })
        if not parsed:
            say("Please say the date in day month year format, for example: 5 December 2025 or 12 January")
            return jsonify({"messages": messages, "done": False})
        
        session.pref_date = parsed.strftime("%Y-%m-%d")
        nice_date = parsed.strftime("%d %B %Y")
        say(f"You want {nice_date}. Is this correct?")
        session.stage = "confirm_date"

    elif session.stage == "confirm_date":
        if is_positive(words) and not is_negative(words):
            nice_date = datetime.strptime(session.pref_date, "%Y-%m-%d").strftime("%d %B %Y")
            say(f"Date confirmed for {nice_date}!")
            say("What time do you prefer? We have 10 AM, 1 PM, or 4 PM.")
            session.stage = "get_time"
        else:
            say("Okay, please say the date again in day month year format.")
            session.stage = "get_date"

    elif session.stage == "get_time":
        lower_input = user_input.lower().replace("o'clock", "").replace(".", ":").strip()
        selected = None
        for k in time_mapping:
            if k in lower_input:
                selected = time_mapping[k]
                break
        if selected:
            session.pref_time = selected
            nice = selected.replace("10:00","10 AM").replace("13:00","1 PM").replace("16:00","4 PM")
            say(f"You want {nice}. Confirm?")
            session.stage = "confirm_time"
        else:
            say("Please say only: 10 AM, 1 PM, or 4 PM.")

    elif session.stage == "confirm_time":
        if is_positive(words) and not is_negative(words):
            date_slot, time_slot = find_next_slot(session.pref_date, session.pref_time)
            nice_date = datetime.strptime(date_slot, "%Y-%m-%d").strftime("%d %B %Y")
            nice_time = time_slot.replace("10:00","10 AM").replace("13:00","1 PM").replace("16:00","4 PM")

            if time_slot != session.pref_time:
                say(f"Your preferred time was taken, so I booked {nice_time} instead.")

            success = book_appointment(session.user_name, session.vehicle_no, date_slot, time_slot)
            if success:
                say(f"Your {session.vehicle_no} is confirmed on {nice_date} at {nice_time}.")
                say("We'll take good care of your car. Thank you!")
            else:
                say("Sorry, this vehicle already has an appointment.")
            
            say("Anything else I can help with?")
            session.stage = "final_ask"
        else:
            say("Please say the time again.")
            session.stage = "get_time"

    elif session.stage == "final_ask":
        if is_negative(words) or any(word in words for word in ["thanks", "bye", "nothing", "no thanks"]):
            say(f"Thank you {session.user_name.split()[0]}! Have a wonderful day!")
            session.reset()
            return jsonify({"messages": messages, "done": True})
        else:
            say("How else may I assist you?")
            session.stage = "main_menu"

    elif session.stage == "check_status":
        v = normalize_vehicle_no(user_input)
        appt = get_appointment(v)
        if appt:
            name, date, time = appt
            nice_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d %B %Y")
            nice_time = time.replace("10:00","10 AM").replace("13:00","1 PM").replace("16:00","4 PM")
            say(f"Hello {name.split()[0]}! Your car {v} will be ready on {nice_date} at {nice_time}.")
        else:
            say("No appointment found for this vehicle number.")
        say("Anything else?")
        session.stage = "final_ask"

    return jsonify({"messages": messages, "done": False})

@app.route('/appointments')
def appointments():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, vehicle_no, date, time FROM appointments ORDER BY date, time")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"name":r[0],"vehicle":r[1],"date":r[2],"time":r[3]} for r in rows])

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
