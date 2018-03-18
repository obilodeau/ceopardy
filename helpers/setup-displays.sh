#!/bin/bash

xrandr --output HDMI1 --mode 1280x1024
xrandr --output HDMI1 --left-of eDP1
sleep 5
xrandr --output HDMI2 --mode 1280x1024
xrandr --output HDMI2 --left-of eDP1
#sleep 5
#xrandr --output HDMI1 --left-of eDP1
sleep 5
xrandr --output HDMI1 --same-as HDMI2
