#!/bin/env python3

import time

import options


with open(options.run_start_time_filename, 'w') as f:
    f.write(str(time.time()) + '\n')
