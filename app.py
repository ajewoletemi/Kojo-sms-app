import os
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2.pool import SimpleConnectionPool

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this later

# --- DATABASE CONNECTION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
# IMPORTANT: Use pooler with pgbouncer=true
if DATABASE_URL and "pooler.supabase.com" in DATABASE_URL:
    if "?" not in DATABASE_URL:
        DATABASE_URL += "?pgbouncer=true&connection_limit=1"
    elif "pgbouncer" not in DATABASE_URL:
        DATABASE_URL += "&pgbouncer=true&connection_limit=1"

pool = SimpleConnectionPool(1, 10, DATABASE_URL)

def get_db():
    return pool.getconn()

def release_db(conn):
    pool.putconn(conn)

# --- ROUTES ---

@app.route('/')
def home():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, email, created_at FROM users ORDER BY id DESC")
    users = c.fetchall()
    release_db(conn)
    return render_template('index.html', users=users)

@app.route('/add_user', methods=['POST'])
def add_user():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        
        if not name or not email:
            flash("Name and Email are required!", "danger")
            return redirect(url_for('home'))

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))
        conn.commit()
        release_db(conn)
        flash("User added successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        print(f"DB ERROR: {e}") # Check Render Logs for this
    
    return redirect(url_for('home'))

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        release_db(conn)
        flash("User deleted!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
    
    return redirect(url_for('home'))

# Optional: if you want /signup to work
@app.route('/signup')
def signup():
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
