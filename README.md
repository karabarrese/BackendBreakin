# BackendBreakin
*Coding Project For CSCI 180*

------------------------------



**Simple HTML Frontend with Flask Backend:**

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

Vulnurability Documentation


Working Logins:

u:Land of Toys Inc.
p:Yu

u:Reims Collectables
p:Henriot

u:Toys4GrownUps.com
p:Young


Malicious Payloads:

u:*&CONTACTLASTNAME=neq.0
p:

u:*&CUSTOMERNAME=eq.Lyon Souveniers
p:

u:*&or=(CUSTOMERNAME.not.is.null)
p:
