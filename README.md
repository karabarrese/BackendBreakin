# BackendBreakin
*Coding Project For CSCI 180*

------------------------------
How to run (mac):

0. Install PostgreSQL (one time): 
    (assuming you have homebrew installed)

    `brew install postgresql@16`

    Then start it:

    `brew services start postgresql@16`

1. Create the virtual environment:

    `python3 -m venv venv`

2. Activate the environment:
    
    `source .venv/bin/activate`

3. Install Dependencies:

    `pip3 install -r requirements.txt`

4. Intialize database:
    `psql -d postgres -f setup_lab.sql`

5. Start the local server:

    `python3 app.py`


Now open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser to view the site.

To stop server, press `Ctrl + C` in the terminal


----------------------------------

How to run (Windows):

0. Install PostgreSQL (one time):

    Download the installer from https://www.postgresql.org/download/windows/
    and run it. Accept the default port **5432**, and set a password for the
    `postgres` user when prompted — you'll need it in step 4. Afterward
    PostgreSQL runs automatically as a background Windows service.

    to add it to your path:
    `Get-ChildItem "C:\Program Files\PostgreSQL"`
    then, see what version you are on (mine is 18)

    set environment variable (then restart vscode)
    `[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Program Files\PostgreSQL\18\bin", "User")`

1. Create the virtual environment:

    `python -m venv venv`

2. Activate the environment (PowerShell):

    `.\venv\Scripts\Activate.ps1`

    > If PowerShell blocks the script with a "running scripts is disabled"
    > error, run this once in the same window, then retry the line above:
    > `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
    >
    > On Command Prompt (cmd) instead of PowerShell, use:
    > `venv\Scripts\activate.bat`

3. Install the requirements:

    `pip install -r requirements.txt`

4. Create the lab database (one time — requires PostgreSQL installed):

    `psql -U postgres -d postgres -f attack/setup_lab.sql`

    > Enter the password you set for the `postgres` user when you installed
    > PostgreSQL. This builds the `breach_lab` database the site logs into.

5. Start the local server:

    `python app.py`


Now open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser to view the site.

To stop server, press `Ctrl + C` in the terminal


----------------------------------

Vulnurability Documentation


# SQL INJECTION:

In line 52 of app.py, we can see this section:

#SAFE: cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
#UNSAFE: cur.execute(f"SELECT id, username, password, email FROM users WHERE username = '{username}' AND password = '{password}'")
(in the actual code, input is written as a vulnerable_query variable)                
we can see that the unsafe example treats the input as a format string, and embeds the username and password inside of itself. This makes the code vulnerable to SQL injections because it doesn't know what is written by the user and what is in the original string

for example, passing the username and password in as:
' OR '1'='1
...returns the entire database