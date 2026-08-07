from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os
os.environ["DATABASE_URL"] = "postgresql://postgres.kvbbegaabylyzfhvqznl:Mikkymouses1!@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

import uuid
from functools import wraps
import psycopg2
from psycopg2 import pool

app = Flask(__name__)
app.secret_key = 'kojo_secret_key_123_change_this'

# Create connection pool for Supabase
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    os.environ["DATABASE_URL"]
)

def get_db():
    return db_pool.getconn()

def release_db(conn):
    db_pool.putconn(conn)

PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
NOWPAYMENTS_API_KEY = os.environ.get('NOWPAYMENTS_API_KEY')
NGN_TO_USD_RATE = 1500 # ₦15,000 = $10 so $1 = ₦1500
