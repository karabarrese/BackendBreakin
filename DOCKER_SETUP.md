This is just if you wanted to run the frontend of the website with the one Dockerfile... if the `docker compose up --build` works for you, ignore this file


## How to run (Windows):
--------------------------------------------------------------

1. Download docker:
https://docs.docker.com/desktop/setup/install/windows-install/

See which errors it gives you, mine said my computer wasn't setup to be a virtual machine:

Open a terminal as windows admin:

`wsl --install`
this does 3 important things Docker requires:
    - "Virtual Machine Platform"
    - "Windows Subsystem for Linux"  
    - downloads Ubuntu

Restart your computer to see the changes...

if you get weird virtualization disabled things, go to bios & turn virtualization on
win+r "msinfo32" should show virtualization as "running"

2. to see if DOCKER is working type into terminal `docker run hello-world`

* SKIP HERE IF DOCKER IS DOWNLOADED* 

3. build the image into a container:
`docker build -f Dockerfile.web -t breachlab-web .`

4. RUN IT!
`docker run --rm -p 5000:5000 breachlab-web`

(note that this will be isolated from the database)

-----------------------------------------------------------------
# Docker vocab: 

An `image` is a recipe/snapshot: “a Linux box with Python and your app installed.” It’s built once and doesn’t change.

A `container` is a running copy of that image (aka) the actual box doing work. You can start, stop, and throw away containers; the image stays.