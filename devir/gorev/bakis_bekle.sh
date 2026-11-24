#!/bin/bash
# /root/is/bakis/ozet.txt en az $1 satır olana dek bekler (en çok $2 sn)
t=0
while [ "$(wc -l < /root/is/bakis/ozet.txt)" -lt "$1" ] && [ $t -lt "$2" ]; do sleep 30; t=$((t+30)); done
cat /root/is/bakis/ozet.txt
