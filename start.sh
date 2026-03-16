#!/bin/bash
Xvfb :98 -screen 0 1280x800x24 &
sleep 2

# display screen
# Line 1 tells linux to run this in bash shell
# &  tells that run in the background dont wait for it


x11vnc -display :98 -forever -nopw -listen 0.0.0.0 -rfbport 5901 &

# vnc server for us to watch

startxfce4 &
sleep 2
echo "Container ready! VNC → localhost:5901"
tail -f /dev/null

# launching desktop

# ordering -> xvfb first -> x11vnc -> xfce last