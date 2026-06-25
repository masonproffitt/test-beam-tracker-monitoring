#!/bin/bash

cd /home/daq/SiTrackerData
while true
do
	rsync -hhav --progress --files-from=<(find ascii_dream_2026 datadir_dream_2026 -newermt "2026-06-22 12:00 CEST") ./ /data/HG-DREAM/CERN/TrackerData/all
	sleep 3600
done
