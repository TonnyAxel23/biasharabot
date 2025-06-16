from flask import Flask, render_template, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os
from datetime import datetime, date

app = Flask(__name__)

# ===========================
# 🗃️ Initialize Database
# ===========================
def init_db():
    conn = sqlite3.connect('sales.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT, quantity INTEGER, unit_price REAL, total REAL, date TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, amount REAL, reason TEXT, date TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        item TEXT PRIMARY KEY, quantity INTEGER)''')

    conn.commit()
    conn.close()

init_db()

# ===========================
# 🌍 Home Route
# ===========================
@app.route('/')
def index():
    return render_template('home.html')

# ===========================
# 🤖 WhatsApp Bot Endpoint
# ===========================
@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    incoming_msg = request.values.get('Body', '').lower()
    resp = MessagingResponse()
    msg = resp.message()

    if 'summary' in incoming_msg:
        today = date.today().strftime("%Y-%m-%d")
        conn = sqlite3.connect('sales.db')
        c = conn.cursor()
        c.execute("SELECT SUM(total) FROM sales WHERE date LIKE ?", (today + '%',))
        result = c.fetchone()
        total_today = result[0] if result[0] else 0
        conn.close()
        msg.body(f"📊 Total earned today ({today}): KES {total_today}")

    elif 'hello' in incoming_msg:
        msg.body("👋 Hello! I'm BiasharaBot. Type 'summary', 'sale 2 soap @50', or 'stock soap'.")

    else:
        msg.body("❓ Sorry, I didn’t understand that. Try: summary, stock soap, or sale...")

    return str(resp)

# ===========================
# ➕ Add Sale Page
# ===========================
@app.route('/add_sale_page')
def add_sale_page():
    return render_template('index.html')

@app.route('/add_sale', methods=['POST'])
def add_sale():
    item = request.form['item']
    quantity = int(request.form['quantity'])
    unit_price = float(request.form['unit_price'])
    total = quantity * unit_price
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('sales.db')
    c = conn.cursor()

    c.execute("INSERT INTO sales (item, quantity, unit_price, total, date) VALUES (?, ?, ?, ?, ?)",
              (item, quantity, unit_price, total, date_str))

    c.execute("SELECT quantity FROM stock WHERE item = ?", (item,))
    result = c.fetchone()

    alert = ""
    if result:
        new_qty = result[0] - quantity
        c.execute("UPDATE stock SET quantity = ? WHERE item = ?", (new_qty, item))
        if new_qty <= 5:
            alert = f"⚠️ LOW STOCK ALERT: {item} only has {new_qty} left!"

    conn.commit()
    conn.close()

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sale Recorded</title>
        <meta charset="UTF-8">
        <script>
            const message = "Sale recorded: {quantity} {item} at {unit_price} shillings each. Total is {total} Kenya shillings. {alert}";
            alert("✅ Sale recorded!\\n{quantity} {item} @ KES {unit_price} = KES {total}");
            const speak = new SpeechSynthesisUtterance(message);
            speak.lang = 'en-US';
            window.speechSynthesis.speak(speak);
            setTimeout(() => window.location.href = "/", 7000);
        </script>
    </head>
    <body>
        <h2>✅ Sale Recorded!</h2>
        <p>{quantity} × {item} @ KES {unit_price} = <strong>KES {total}</strong></p>
        <p>{alert}</p>
        <p>Redirecting to home...</p>
    </body>
    </html>
    '''

# ===========================
# 📊 Summary Page
# ===========================
@app.route('/summary')
def summary():
    today = date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect('sales.db')
    c = conn.cursor()
    c.execute("SELECT SUM(total) FROM sales WHERE date LIKE ?", (today + '%',))
    result = c.fetchone()
    total_today = result[0] if result[0] else 0
    conn.close()
    return f"📊 Total earned today ({today}): KES {total_today}"

# ===========================
# ⏰ Reminder
# ===========================
@app.route('/reminder', methods=['GET', 'POST'])
def reminder():
    if request.method == 'POST':
        name = request.form['name']
        amount = float(request.form['amount'])
        reason = request.form['reason']
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect('sales.db')
        c = conn.cursor()
        c.execute("INSERT INTO reminders (name, amount, reason, date) VALUES (?, ?, ?, ?)",
                  (name, amount, reason, date_str))
        conn.commit()
        conn.close()

        return f"📝 Reminder saved: {name} owes KES {amount} for {reason}"
    else:
        return render_template('reminder.html')

# ===========================
# 🧃 Restock
# ===========================
@app.route('/restock', methods=['GET', 'POST'])
def restock():
    if request.method == 'POST':
        item = request.form['item']
        quantity = int(request.form['quantity'])

        conn = sqlite3.connect('sales.db')
        c = conn.cursor()

        c.execute("SELECT quantity FROM stock WHERE item = ?", (item,))
        existing = c.fetchone()

        if existing:
            new_qty = existing[0] + quantity
            c.execute("UPDATE stock SET quantity = ? WHERE item = ?", (new_qty, item))
        else:
            c.execute("INSERT INTO stock (item, quantity) VALUES (?, ?)", (item, quantity))

        conn.commit()
        conn.close()

        return f"✅ Restocked {item}: +{quantity} items"
    else:
        return render_template('restock.html')

# ===========================
# 📋 Dashboard
# ===========================
@app.route('/dashboard')
def dashboard():
    today = date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect('sales.db')
    c = conn.cursor()

    c.execute("SELECT SUM(total) FROM sales WHERE date LIKE ?", (today + '%',))
    result = c.fetchone()
    total_today = result[0] if result[0] else 0

    c.execute("SELECT item, quantity FROM stock WHERE quantity <= 5")
    low_stock = c.fetchall()

    c.execute("SELECT name, amount, reason FROM reminders")
    reminders = c.fetchall()

    c.execute("SELECT item, quantity, unit_price, total, date FROM sales ORDER BY date DESC LIMIT 5")
    recent_sales = c.fetchall()

    conn.close()

    return render_template("dashboard.html",
                           total_today=total_today,
                           low_stock=low_stock,
                           reminders=reminders,
                           recent_sales=recent_sales)

# ===========================
# ▶️ Run the App
# ===========================
port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
