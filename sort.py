#!/bin/env python3

import datetime
from pathlib import Path
import logging
import shutil
import time

import options


hbook_file_directory = '/home/daq/SiTrackerData/datadir_dream_2026'
by_run_archive_directory = '/data/HG-DREAM/CERN/TrackerData/by_run'
minimum_run_start_time = datetime.datetime(2026, 6, 22, 8, tzinfo=options.cern_time_zone).timestamp()
loop_delay = 60
debug=False


if debug:
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(level=logging_level)

run_number_to_start_time_dict = {}
run_number_to_dat_path_dict = {}

while True:
    loop_start_time = time.perf_counter()
    for run_config_path in Path(options.daq_monitoring_directory).iterdir():
        if run_config_path.name.startswith(options.run_config_file_prefix) and run_config_path.name.endswith(options.run_config_file_extension):
            run_number = int(run_config_path.name.removeprefix(options.run_config_file_prefix).removesuffix(options.run_config_file_extension))
            if run_number in run_number_to_start_time_dict.keys():
                continue
            run_start_time = run_config_path.stat().st_mtime
            if run_start_time >= minimum_run_start_time:
                run_number_to_start_time_dict[run_number] = run_start_time
                run_number_to_dat_path_dict[run_number] = []

    after_run_loop_time = time.perf_counter()
    logging.info(f'{after_run_loop_time - loop_start_time=}')
    logging.debug(f'{run_number_to_start_time_dict=}')
    run_numbers = list(run_number_to_start_time_dict.keys())
    run_numbers.sort(reverse=True)

    for hbook_path in Path(hbook_file_directory).iterdir():
        if not hbook_path.name.endswith('.hbook'):
            continue
        dat_filename = hbook_path.name.removesuffix('.hbook') + '.dat'
        underscore_index = dat_filename.index('_') + 1
        dat_filename = dat_filename[:underscore_index] + '0' + dat_filename[underscore_index:]
        dat_path = Path(options.dat_file_directory) / dat_filename
        if not dat_path.is_file():
            logging.debug(f'missing file {dat_path}')
            continue
        if dat_path.stat().st_size == 0:
            logging.debug(f'skipping empty file {dat_path}')
            continue
        hbook_file_mtime = hbook_path.stat().st_mtime
        logging.debug(f'{hbook_path=} {hbook_file_mtime=}')
        for run_number in run_numbers:
            if hbook_file_mtime > run_number_to_start_time_dict[run_number]:
                run_number_to_dat_path_dict[run_number].append(dat_path)
                break

    after_hbook_loop_time = time.perf_counter()
    logging.info(f'{after_hbook_loop_time - after_run_loop_time=}')
    logging.debug(f'{run_number_to_dat_path_dict=}')

    for run_number in run_number_to_dat_path_dict.keys():
        if len(run_number_to_dat_path_dict[run_number]) == 0:
            continue
        run_directory_path = Path(by_run_archive_directory) / str(run_number)
        if not run_directory_path.is_dir():
            logging.info(f'creating {run_directory_path}')
            run_directory_path.mkdir()
        for dat_path in run_number_to_dat_path_dict[run_number]:
            if (run_directory_path / dat_path.name).is_file():
                if (run_directory_path / dat_path.name).stat().st_size != dat_path.stat().st_size:
                    logging.info(f'updating already existing file {run_directory_path / dat_path.name}')
                else:
                    logging.debug(f'skipping already existing file {run_directory_path / dat_path.name}')
                    continue
            logging.debug(f'copying {dat_path} to {run_directory_path}')
            shutil.copy2(dat_path, run_directory_path)

    loop_end_time = time.perf_counter()
    logging.info(f'{loop_end_time - after_hbook_loop_time=}')
    time.sleep(loop_delay)
