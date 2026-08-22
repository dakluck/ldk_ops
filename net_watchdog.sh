#!/bin/bash
# Network Watchdog for OpenClaw Server

TARGET="8.8.8.8"
CONNECTION="We Love Butter"
LOG_FILE="/home/dailey/.openclaw/workspace/net_watchdog.log"

# Check connectivity
if ! ping -c 3 $TARGET > /dev/null 2>&1; then
    echo "$(date): Network connection lost. Attempting recovery..." >> $LOG_FILE
    
    # Attempt to bring up the connection
    sudo nmcli connection up "$CONNECTION" > /dev/null 2>&1
    
    # Verify if it worked
    sleep 10
    if ping -c 1 $TARGET > /dev/null 2>&1; then
        echo "$(date): Connection successfully restored." >> $LOG_FILE
    else
        echo "$(date): Recovery failed. Attempting to restart NetworkManager..." >> $LOG_FILE
        sudo systemctl restart NetworkManager > /dev/null 2>&1
        sleep 15
        if ping -c 1 $TARGET > /dev/null 2>&1; then
            echo "$(date): Connection restored via NetworkManager restart." >> $LOG_FILE
        else
            echo "$(date): CRITICAL: Network still down after all attempts." >> $LOG_FILE
        fi
    fi
fi
