#!/bin/env python3

import datetime
import time

import options
import utils


reset_time = time.time()
utils.write_run_start_time(reset_time)
print(f'Reset tracker histograms at {datetime.datetime.fromtimestamp(reset_time).astimezone(options.cern_time_zone).ctime()}')
