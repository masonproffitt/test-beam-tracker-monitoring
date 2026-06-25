#!/bin/bash

delay=60

while true
do
	echo Starting sort at $(date)
	./sort.py
	echo Finished sort at $(date)
	sleep $delay
done
