#!/bin/bash
echo Hello
echo I will now install Simple Flasher

sudo usermod -aG disk $USER
sudo cp ./flasher.py /bin
sudo cp ./flasher.desktop /usr/share/applications/
sudo cp ./usb.png /usr/share/pixmaps/

echo 
echo Successfully installed Simple Flasher
echo Bye Bye!
