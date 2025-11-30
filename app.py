# app.py - DEEWANSHI CAR CENTER – TRULY FINAL VERSION (DATE + TIME FIXED FOREVER)
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import dateparser
import re
import os

app = Flask(__name__)
CORS(app)
DB_FILE = "appointments.db"

# Keep this line only for testing in 2025. Remove or comment after Dec 2025
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
    '')
    conn.commit()
    conn.close()
init_db()

class Session:
    def __init__(self): self.reset()
    def reset(self):
        self.stage = "welcome"
        self.user_name = None
        self.vehicle_no = None
        self.pref_date = None
        self.pref_time = None

session = Session()

def normalize_vehicle_no(text):
    return ''.join(c for c in text.upper() if c.isalnum())

# SUPER ROBUST TIME MAPPING – accepts almost everything
time_mapping = {
    "10": "10:00", "10am": "10:00", "10:00": "10:00", "ten": "10:00", "morning": "10:00",
    "1pm": "13:00", "1 pm": "13:00", "1:00pm": "13:00", "1:00 pm": "13:00", "one": "13:00", "afternoon": "13:00",
    "4pm": "16:00", "4 pm": "16:00", "4:00pm": "16:00", "4:00 pm": "16:00", "four": "16:00", "evening": "16:00"
}

def find_available_slot(chosen_date_str, preferred_time=None):
    # Parse the EXACT date user said
    parsed = dateparser.parse(chosen_date_str, settings={
        'PREFER_DATES_FROM': 'future',
        'DATE_ORDER': 'DMY',
        'RELATIVE_BASE': TODAY
    })
    if not parsed is None:
        parsed = datetime.now()
    date_obj = parsed.date()
    slots = ["10:00", "13:00", "16:00"]

    for _ in range(30):  # max 30 days ahead
        date_str = date_obj.strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT time FROM appointments WHERE date=?", (date_str,))
        booked = [row[0] for row in c.fetchall()]
        conn.close()

        # 1. Try user's preferred time first
        if preferred_time and preferred_time not in booked:
            return date_str, preferred_time

        # 2. Otherwise give any free slot on the SAME date
        for slot in slots:
            if slot not in booked:
                return date_str, slot

        # 3. Only go to next day if all 3 slots are full
        date_obj += datetime.timedelta(days=1)

    return date_obj.strftime("%Y-%m-%d"), "10:00"

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

@app.route('/')
def index(): return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    session.reset()
    session.stage = "ask_name"
    return jsonify({"messages": ["Good morning! Welcome to Deewanshi Car Center. May I know your name please?"], "done": False})

@app.route('/listen', methods=['POST'])
def listen():
    user_input = request.json.get("message", "").strip().lower()
    if not user_input:
        return jsonify({"messages": ["I couldn't hear you. Try again."], "done": False})

    messages = []
    def say(text): messages.append(text)

    def is_yes(): return any(x in user_input for x in ["yes","correct","yeah","ok","confirm","right","it is"])
    def is_no():  return any(x in user_input for x in ["no","not","wrong","incorrect"])

    # === ALL STAGES (shortened for clarity – only changes are in date & time) ===

    if session.stage == "ask_name":
        session.user_name = user_input.title()
        say(f"You said your name is {session.user_name}. Is that correct?")
        session.stage = "confirm_name"

    elif session.stage == "confirm_name":
        if is_yes():
            say(f"Great! Thank you {session.user_name.split()[0]}.")
            say("How can I help you today? Say 'book appointment' or 'check car status'.")
            session.stage = "main_menu"
        else:
            say("Sorry, please say your name again.")
            session.stage = "ask_name"

    elif session.stage == "main_menu":
        if any(x in user_input for x in ["book","appointment","service","wash"]):
            say("Please tell me your vehicle number.")
            session.stage = "get_vehicle"
        elif any(x in user_input for x in ["status","check","ready"]):
            say("Please say your vehicle number to check status.")
            session.stage = "check_status"

    elif session.stage == "get_vehicle":
        v = normalize_vehicle_no(user_input)
        if len(v) < 6:
            say("I couldn't catch that. Please say your vehicle number again.")
        else:
            session.vehicle_no = v
            say(f"You said {v}. Is this correct?")
            session.stage = "confirm_vehicle"

    elif session.stage == "confirm_vehicle":
        if is_yes():
            say(f"Your vehicle {session.vehicle_no} is confirmed!")
            say("Please say the date in day month year format, for example: 5 December 2025")
            session.stage = "get_date"
        else:
            say("Please say your vehicle number again.")
            session.stage = "get_vehicle"

    elif session.stage == "get_date":
        parsed = dateparser.parse(user_input, settings={'DATE_ORDER': 'DMY', 'RELATIVE_BASE': TODAY})
        if not parsed:
            say("Please say the date properly, like 3 December 2025")
            return jsonify({"messages": messages, "done": False})
        session.pref_date = parsed.strftime("%Y-%m-%d")
        nice = parsed.strftime("%d %B %Y")
        say(f"You want {nice}. Is this correct?")
        session.stage = "confirm_date"

    elif session.stage == "confirm_date":
        if is_yes():
            say(f"Date confirmed for {datetime.strptime(session.pref_date,'%Y-%m-%d').strftime('%d %B %Y')}!")
            say("What time do you prefer? We have 10 AM, 1 PM, or 4 PM.")
            session.stage = "get_time"
        else:
            say("Okay, please say the date again.")
            session.stage = "get_date"

    elif session.stage == "get_time":
        selected = None
        for key in time_mapping:
            if key in user_input:
                selected = time_mapping[key]
                break
        if selected:
            session.pref_time = selected
            nice = selected.replace("10:00","10 AM").replace("13:00","1 PM").replace("16:00","4 PM")
            say(f"You want {nice}. Confirm?")
            session.stage = "confirm_time"
        else:
            say("Please say only: 10 AM, 1 PM, or 4 PM.")

    elif session.stage == "confirm_time":
        if is_yes():
            final_date, final_time = find_available_slot(session.pref_date, session.pref_time)

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

    elif session.stage == "final_ask":
        if is_no() or any(x in user_input for x in ["thanks","bye","nothing"]):
            say(f"Thank you {session.user_name.split()[0]}! Have a wonderful day!")
            session.reset()
            return jsonify({"messages": messages, "done": True})
        else:
            session.stage = "main_menu"

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
