import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.pool import SimpleConnectionPool

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey_change_me")

# --- DATABASE CONNECTION ---
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Add it to Render Environment Variables")

pool = SimpleConnectionPool(1, 10, DATABASE_URL)

def get_db():
    return pool.getconn()

def release_db(conn):
    pool.putconn(conn)

# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, email, created_at FROM users ORDER BY id DESC")
    users = c.fetchall()
    release_db(conn)
    return render_template('index.html', users=users, user_name=session.get('user_name'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        
        if not name or not email:
            flash("Name and Email are required!", "danger")
            return redirect(url_for('signup'))

        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id", (name, email))
            user_id = c.fetchone()[0]
            conn.commit()
            release_db(conn)
            flash("Account created! Please login.", "success")
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash("Email already exists!", "danger")
            return redirect(url_for('signup'))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, name, email FROM users WHERE email = %s", (email,))
        user = c.fetchone()
        release_db(conn)
        
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            flash(f"Welcome back, {user[1]}!", "success")
            return redirect(url_for('home'))
        else:
            flash("User not found! Please sign up.", "danger")
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
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


if __name__ == '__main__':
    app.run(debug=False)
