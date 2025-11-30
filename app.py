# app.py - DEEWANSHI CAR CENTER – FINAL FIXED (1 PM & 4 PM NOW WORK!)
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

# Lock today for testing (remove after 2025)
TODAY = datetime(2025, 11, 30)

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

# FIXED: Now respects preferred time properly!
def find_next_slot(preferred_date_str, preferred_time=None):
    base = dateparser.parse(preferred_date_str, settings={
        'PREFER_DATES_FROM': 'future',
        'DATE_ORDER': 'DMY',
        'RELATIVE_BASE': TODAY
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

        # If preferred time is free → book it!
        if preferred_time and preferred_time in slots and preferred_time not in booked:
            return d_str, preferred_time

        # Otherwise book first available
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
        return jsonify({"messages": ["I couldn't hear you. Try again."], "done": False})

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
        "1pm": "13:00", "1 pm": "13:00", "one": "13:00", "afternoon": "13:00",
        "4pm": "16:00", "4 pm": "16:00", "four": "16:00", "evening": "16:00"
    }

    def is_positive(w): return any(p in w for p in ["yes", "correct", "yeah", "ok", "right", "confirm", "it is"])
    def is_negative(w): return any(n in w for n in ["no", "not", "wrong", "incorrect", "nope"])

    # ... (all stages same until confirm_time) ...

    elif session.stage == "confirm_time":
        if is_positive(words) and not is_negative(words):
            # Use exact user-chosen date
            date_slot = session.pref_date

            # Get final time using fixed function
            final_date, final_time = find_next_slot(session.pref_date, session.pref_time)

            # If time changed
            if final_time != session.pref_time:
                nice_time = final_time.replace("10:00","10 AM").replace("13:00","1 PM").replace("16:00","4 PM")
                say(f"Your preferred time was taken, so I booked {nice_time} instead.")

            success = book_appointment(session.user_name, session.vehicle_no, final_date, final_time)
            nice_date = datetime.strptime(final_date, "%Y-%m-%d").strftime("%d %B %Y")
            nice_time = final_time.replace("10:00","10 AM").replace("13:00","1 PM").replace("16:00","4 PM")

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

    # ... rest of code same ...

    return jsonify({"messages": messages, "done": False})

# Keep all other routes same
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
