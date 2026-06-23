#!/bin/env python3

import datetime
import time
import zoneinfo

import options
import utils


cern_time_zone = zoneinfo.ZoneInfo('Europe/Zurich')


reset_time = time.time()
utils.write_run_start_time(reset_time)
print(f'Reset tracker histograms at {datetime.datetime.fromtimestamp(reset_time).astimezone(cern_time_zone).ctime()}')
