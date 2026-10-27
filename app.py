import os
import psycopg2 #opens a connection to the database
from flask import Flask, request, redirect, url_for, session, render_template
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'temporary_secret_key'

DB_HOST = os.getenv("LAB_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("LAB_DB_PORT", "5432"))
DB_NAME = os.getenv("LAB_DB_NAME", "breach_lab")
DB_USER = os.getenv("LAB_DB_USER", "app_user")
DB_PASSWORD = os.getenv("LAB_DB_PASSWORD", "app_password")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD, connect_timeout=10,
    )

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

        #example of a vulnerable query that is susceptible to SQL injection attacks
        # vulnerable_query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}';"
        
        #the f"WHERE is most important because it's a format string, f strings make it so that when people input variables, they are treated as part of the real string
        vulnerable_query = (
            "SELECT id, username, password, email FROM users "
            f"WHERE username = '{username}' AND password = '{password}'" #vulnerable to SQL, username ex: ' OR '1'='1
            #the WHERE will return true and output everything if the user inputs ' OR '1'='1
            #would return every line in the table...
        )

        try:
            with get_connection() as conn:
                cur = conn.cursor() #cursor: object you run SQL queries through (Pointer to resule set)
                cur.execute(vulnerable_query) #sends the SQL string to posgress and runs it
                
                #SAFE: cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
                #UNSAFE: cur.execute(f"SELECT id, username, password, email FROM users WHERE username = '{username}' AND password = '{password}'")
                
                rows = cur.fetchall() #pulls back all matching rows as a list (if empty, nothing matched)
                if rows:
                    session['user'] = username
                    session['active_query'] = vulnerable_query
                    return redirect(url_for('dashboard'))
                else:
                    return "Login Failed :P Please try again..."

        except Exception as e:
            # If the internet drops or the database fails, catch the error here
            return f"Database connectivity error: {str(e)}"
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # SECURITY WALL: If they try to sneak into the dashboard without logging in, kick them back to the login page
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        # Grab the active query from the session and run it again to get the user data
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(session['active_query'])
            cols = [d.name for d in cur.description] # Get column names
            user_data = [dict(zip(cols, row)) for row in cur.fetchall()] # Convert rows to list of dicts
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
    app.run(host='0.0.0.0', debug=True) #dangerous to run debug mode true, especially on 0.0.0.0, but this site is just for testing purposes :P

