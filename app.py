from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os
os.environ["DATABASE_URL"] = "postgresql://postgres.kvbbegaabylyzfhvqznl:Mikkymouses1!@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

import uuid
from functools import wraps
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor # makes data return as dict instead of tuple

app = Flask(__name__)
app.secret_key = 'kojo_secret_key_123_change_this_to_something_random'

# Create connection pool for Supabase
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    os.environ["DATABASE_URL"]
)

def get_db():
    """Get database connection from pool"""
    return db_pool.getconn()

def release_db(conn):
    """Release database connection back to pool"""
    db_pool.putconn(conn)

def init_db():
    """Run this once to create tables in Supabase"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            password VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    release_db(conn)

PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
NOWPAYMENTS_API_KEY = os.environ.get('NOWPAYMENTS_API_KEY')
NGN_TO_USD_RATE = 1500 # ₦15,000 = $10 so $1 = ₦1500

# ===== EXAMPLE ROUTES - REPLACE WITH YOURS =====
@app.route('/')
def home():
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT * FROM users ORDER BY id DESC")
    users = c.fetchall()
    release_db(conn)
    return render_template('index.html', users=users)

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form['name']
    email = request.form['email']
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))
        conn.commit()
        flash("User added successfully!")
    except psycopg2.IntegrityError:
        conn.rollback()
        flash("Email already exists!")
    finally:
        release_db(conn)
    
    return redirect(url_for('home'))

# ===== LOGIN DECORATOR EXAMPLE =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

if __name__ == '__main__':
    # init_db() # Uncomment this line once to create tables, then comment it again
    app.run(debug=True)
