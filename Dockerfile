FROM ubuntu:22.04 
# i will start with basic ubuntu linux computer

ENV DEBIAN_FRONTEND=noninteractive  
# proceeding with defaults

ENV DISPLAY=:98
# assigning screen number 98

RUN apt-get update && apt-get install -y \
    xvfb \
    xfce4 \
    xfce4-terminal \
    x11vnc \
    xdotool \
    imagemagick \
    dbus-x11 \
    fonts-liberation \
    libgtk-3-0 \
    wget \
    bzip2 \
    xz-utils \
    curl \
    ca-certificates \
    libdbus-glib-1-2 \
    libasound2 \
    && apt-get clean \ 
    && rm -rf /var/lib/apt/lists/*

# installing tools and cleaning package files and deleting package lists(saves space)

RUN apt-get update && apt-get install -y gnupg2 \
    && install -d -m 0755 /etc/apt/keyrings \
    && curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg \
       -o /etc/apt/keyrings/packages.mozilla.org.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" \
       > /etc/apt/sources.list.d/mozilla.list \
    && printf 'Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n' \
       > /etc/apt/preferences.d/mozilla \
    && apt-get update && apt-get install -y firefox \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# gnupg2 -> its needed to verify mozillas signing key
#we can use either wget or curl to download the signature 
# setting priority to 1000 tells apt to use snap instead of snap version
# now installing firefox from mozilla install -y firefox

COPY start.sh /start.sh
# copying start.sh to the container

RUN chmod +x /start.sh

#chmod +x gives file permission to execute

EXPOSE 5901
#labelling it with 5901 and opens the port when we execute docker run -p 5901:5901
CMD ["/start.sh"]






