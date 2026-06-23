#!/bin/env python3

import datetime
import time
import zoneinfo

import options


cern_time_zone = zoneinfo.ZoneInfo('Europe/Zurich')


reset_time = time.time()

with open(options.run_start_time_filename, 'w') as f:
    f.write(str(reset_time) + '\n')

print(f'Reset tracker histograms at {datetime.datetime.fromtimestamp(reset_time).astimezone(cern_time_zone).ctime()}')
