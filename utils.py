import logging
import options
from pathlib import Path


def write_run_start_time(time):
    logging.debug(f'writing {time} to {options.run_start_time_filename}')
    with open(options.run_start_time_filename, 'w') as f:
        f.write(str(time) + '\n')


def look_up_run_start_time(run_number):
    try:
        run_config_file_path = Path(options.daq_monitoring_directory) / Path(options.run_config_file_prefix + str(run_number) + options.run_config_file_extension)
        run_start_time = run_config_file_path.stat().st_mtime
        logging.debug(f'read {run_start_time} from {run_config_file_path}')
    except Exception as e:
        logging.warning(e)
        run_start_time = -1
    return run_start_time
