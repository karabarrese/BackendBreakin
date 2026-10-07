# BackendBreakin
*Coding Project For CSCI 180*

------------------------------



### Simple HTML Frontend with Flask Backend:

How to run (mac):

1. Create the virtual environment:

    `python3 -m venv venv`

2. Activate the environment:
    
    `source .venv/bin/activate`

3. Install Flask:

    `pip3 install -r requirements.txt`

4. Start the local server:

    `python3 app.py`


Now open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser to view the site.

To stop server, press `Ctrl + C` in the terminal


----------------------------------

### Working Logins for Testing 
(u = CUSTOMERNAME, p = CONTACTLASTNAME):

* u: `Land of Toys Inc.`  p: `Yu`

* u: `Reims Collectables` p: `Henriot`

* u: `Toys4GrownUps.com` p: `Young`

----------------------------------

### Why Parameter Injection Fails Here

Even though this code builds the request URL unsafely, you cannot bypass the login using HTTP Parameter Pollution (HPP). 

"Unsafe code": `vulnerable_query = f"CUSTOMERNAME=eq.{username}&CONTACTLASTNAME=eq.{password}"`

Injection Attempt: `Toys4GrownUps.com&or=(://toys4grownups.com)` 
* Trying to use the ampersand (&) to break out of the original URL structure and add a global or condition to bypass the password check.

* Why it didn't work: 
    - Supabase didn't let the injected "OR" command overwrite and replace the password check, it chained them both together with strict "AND" logic. 
    - Because a database row cannot match two conflicting instructions at the same time, the query automatically canceled itself out, returned zero data rows, and safely failed the login.


