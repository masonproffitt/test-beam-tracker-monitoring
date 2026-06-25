#!/bin/bash

cd /home/daq/SiTrackerData
while true
do
	echo Starting rsync at $(date)
	rsync -hhav --progress --files-from=<(find ascii_dream_2026 datadir_dream_2026 -newermt "2026-06-22 12:00 CEST") ./ /data/HG-DREAM/CERN/TrackerData/all
	echo Finished rsync at $(date)
	sleep 3600
done
