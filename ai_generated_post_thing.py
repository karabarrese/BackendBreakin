import os
from flask import Flask, render_template, jsonify
import requests
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

app = Flask(__name__)

# Fetch the hidden credentials from the environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

@app.route('/')
def home():
    # Renders your initial login/home page
    return render_template('index.html') 

@app.route('/api/sales', methods=['GET'])
def get_sales_data():
    """Route that calls your teammate's Supabase API backend"""
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        return jsonify({"error": "Missing API configuration in environment"}), 500

    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}"
    }

    try:
        # Call your teammate's API
        response = requests.get(SUPABASE_URL, headers=headers)
        
        # If successful, return the data straight to your frontend
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": f"Supabase returned error code {response.status_code}"}), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Connection failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
