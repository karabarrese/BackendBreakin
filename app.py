import os
import sqlite3
from flask import Flask, request, redirect, url_for, session, render_template
from dotenv import load_dotenv
from supabase import create_client, Client
import requests

# Load variables from the .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'temporary_secret_key'

# Fetch the hidden credentials from the environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

# supabase: Client = create_client(
#     os.environ.get("SUPABASE_URL"),
#     os.environ.get("SUPABASE_KEY")
# )

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If the user just clicked the "Submit/Login" button...
    if request.method == 'POST':
        # Grab whatever text they typed into the Username and Password
        username = request.form.get('username')
        password = request.form.get('password')

        # UNSECURE: without sanitizing, put user text into a search string
        vulnerable_query = f"CUSTOMERNAME=eq.{username}&CONTACTLASTNAME=eq.{password}"
        #CUSTOMERNAME=eq.{username}&CONTACTLASTNAME=eq.{password}

        # Make & work
        vulnerable_query = requests.utils.unquote(vulnerable_query)

        # Piece together the final web link
        target_url = f"{SUPABASE_URL}?apikey={SUPABASE_API_KEY}&{vulnerable_query}&select=*"

        # Attach the secret keys
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}"
        }
        
        
        try:
            # Send the search query over the internet
            response = requests.get(target_url)
            data = response.json()

            #  THE CHECKPOOL: Did the database find any records matching that query?
            # (If a normal user typed correct info, it returns 1 row. If an attacker 
            # uses SQL injection to force the logic to be True, it returns ALL rows!)
            if isinstance(data, list) and len(data) > 0:
                # Log them in! Save their name and search string in the browser's memory
                session['user'] = username
                session['active_query'] = vulnerable_query 
                return redirect(url_for('dashboard'))
            else:
                # No data came back, meaning the login details were wrong
                return "Login Failed! Go back and try again."
        except Exception as e:
            # If the internet drops or the database fails, catch the error here
            return f"Database connectivity error: {str(e)}"
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # SECURITY WALL: If they try to sneak into the dashboard without logging in, kick them back to the login page
    if 'user' not in session:
        return redirect(url_for('login'))

    # Re-build that exact same search link we stored during the login step
    target_url = f"{SUPABASE_URL}?{session['active_query']}&select=*"

    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}"
    }
    
    try:
        # Pull the live data rows from the database
        response = requests.get(target_url, headers=headers)
        user_data = response.json()
    except Exception:
        # If anything breaks, fallback to an empty list so the page doesn't crash
        user_data = []

    # Send the user data straight to dashboard.html to render nicely on screen
    return render_template('dashboard.html', user_data=user_data)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

