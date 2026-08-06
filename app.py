from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123" # Change this to anything random

# DATABASE SETUP
def init_db():
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, balance REAL DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# HOME PAGE
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# SIGNUP PAGE - THIS IS WHERE WE ADDED NAME
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name'] # <-- NEW LINE
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?,?,?)", (name, email, hashed_password)) # <-- ADDED NAME
            conn.commit()
            flash("Account created successfully! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists!", "danger")
        finally:
            conn.close()
    return render_template('signup.html')


# LOGIN PAGE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email =?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password): # user[3] is password, user[1] is name
            session['user_id'] = user[0]
            session['user_name'] = user[1] # <-- SAVE NAME TO SESSION
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")
    return render_template('login.html')


# DASHBOARD PAGE
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()

    return render_template('dashboard.html', balance=balance, name=session['user_name']) # <-- SEND NAME TO DASHBOARD


# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# PLACEHOLDER ROUTES
@app.route('/fund_wallet')
def fund_wallet():
    return "Paystack Integration Coming Soon"

@app.route('/buy_number')
def buy_number():
    return "Buy Number Page Coming Soon"


if __name__ == '__main__':
    app.run(debug=True)
