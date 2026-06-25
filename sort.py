from pathlib import Path
import logging

import options


hbook_directory = '/home/daq/SiTrackerData/datadir_dream_2026'
by_run_archive_directory = '/data/HG-DREAM/CERN/TrackerData/by_run'
debug=False


if debug:
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(level=logging_level)

run_number_to_start_time_dict = {}
run_number_to_dat_file_dict = {}
for run_config_path in Path(options.daq_monitoring_directory).iterdir():
    if run_config_path.name.startswith(options.run_config_file_prefix) and run_config_path.name.endswith(options.run_config_file_extension):
        run_number = int(run_config_path.name.removeprefix(options.run_config_file_prefix).removesuffix(options.run_config_file_extension))
        run_number_to_start_time_dict[run_number] = run_config_path.stat().st_mtime
        run_number_to_tracker_dat_file_dict[run_number] = []

run_numbers = list(run_number_to_start_time_dict.keys())
run_numbers.sort()

for hbook_path in Path(hbook_file_directory).iterdir():
    if not hbook_path.name.endswith('.hbook'):
        continue
    dat_filename = hbook_path.name.removesuffix('.hbook') + '.dat'
    dat_path = Path(options.dat_file_directory) / dat_filename
    if not dat_path.is_file():
        logging.warning(f'missing file {dat_path}')
    else:
        hbook_file_mtime = hbook_path.stat().st_mtime
        logging.debug(f'{hbook_path=} {hbook_file_mtime=}')
        for run_number in run_numbers:
            if hbook_file_mtime > run_number_to_start_time_dict[run_number]:
                run_number_to_dat_path_dict[run_number].append(dat_path)
                break

logging.debug(f'{run_number_to_dat_path_dict=}')

for run_number in run_number_dat_file_dict.keys():
    run_directory_path = Path(by_run_archive_directory) / str(run_number)
    if not run_directory_path.is_dir():
        logging.info(f'creating {run_directory_path}')
        run_directory_path.mkdir()
    for dat_path in run_number_to_dat_path_dict[run_number]:
        if (run_directory_path / dat_path.name).is_file():
            logging.debug(f'skipping already existing file {run_directory_path / dat_path.name}')
        else:
            logging.info(f'copying {dat_path} to {run_directory_path}')
            shutil.copy2(dat_path, run_directory_path)
