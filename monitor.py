#!/bin/env python3

import csv
import datetime
import logging
from pathlib import Path
import shutil
import time

import numpy as np
import matplotlib.pyplot as plt

import options
import utils


tracker_file_directory = '/home/daq/SiTrackerData/ascii_dream_2026'
last_run_number_filename = 'run_number'
daq_monitor_path = Path('/home/daq/DAQMon/Monitor_out.txt')
backtrack = True
loop_delay = 1
x_min = 0
x_max = 10
x_bins = 50
x_label = '$x$ [cm]'
y_min = 0
y_max = 10
y_bins = 50
y_label = '$y$ [cm]'
z_min = 0
z_max = None
z_label = f'Events per {(x_max - x_min) / x_bins} cm $\\times$ {(y_max - y_min) / y_bins} cm'
histogram_plot_base_filename = 'beam_profile'
histogram_plot_base_title = 'Station '
missing_hits_base_filename = 'missing_hits'
histogram_plot_file_extension = '.png'
coordinate_dtype = np.float32
archive_histograms = True
histogram_archive_directory_name = 'histogram_archive'
debug = False
recent_file_time_threshold = 60
recent_file_write_check_interval = 0.1
one_d_histogram_y_axis_rescale_factor = 1.1

n_points = 3
n_coordinates_per_point = 2

last_run_number_file_byte_limit = 100
run_start_time_file_byte_limit = 100
run_start_time_min = 1e9
run_start_time_max = 1e10

run_start_time_path = Path(options.run_start_time_filename)
tracker_file_directory_path = Path(tracker_file_directory)

default_time = -1

run_start_time = default_time
last_run_start_update_time = default_time
last_tracker_file_directory_update_time = default_time
latest_tracker_file_mtime = default_time
tracker_file_mtimes = {}

bins = [x_bins, y_bins]
x_range = [x_min, x_max]
y_range = [y_min, y_max]
x_histogram_args = []
x_histogram_kwargs = {
    'bins': x_bins,
    'range': x_range,
}
y_histogram_args = []
y_histogram_kwargs = {
    'bins': y_bins,
    'range': y_range,
}
two_d_histogram_args = []
two_d_histogram_kwargs = {
    'bins': bins,
    'range': [x_range, y_range],
}
missing_hits_histogram_args = []
missing_hits_histogram_kwargs = {
    'bins': n_coordinates_per_point * n_points,
    'range': [0.5, n_coordinates_per_point * n_points + 0.5],
}

if debug:
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(level=logging_level)
noisy_loggers = ['matplotlib', 'PIL']
for logger in noisy_loggers:
    logging.getLogger(logger).setLevel(logging.WARNING)


def read_run_start_time(path):
    with open(path) as f:
        run_start_time = float(f.read(run_start_time_file_byte_limit))
    logging.debug(f'{run_start_time=}')
    if not run_start_time_min < run_start_time < run_start_time_max:
        return time.time()
    else:
        return run_start_time


def parse(path):
    logging.info(f'parse {path}')
    coordinates = []
    with open(path) as f:
        while True:
            l = f.readline()
            if not l:
                break
            if not l.strip():
                continue
            fields = l.split()
            coordinates.append(fields[:n_coordinates_per_point * n_points])
    logging.info(f'read {len(coordinates)} hits')
    if len(coordinates) == 0:
        coordinates = np.ndarray((0, n_coordinates_per_point * n_points), dtype=coordinate_dtype)
    else:
        coordinates = np.asarray(coordinates, dtype=coordinate_dtype)
    logging.debug(f'{coordinates=}')
    return coordinates


def create_histograms():
    logging.debug('create histograms')
    x_histograms = []
    y_histograms = []
    two_d_histograms = []
    for i in range(n_points):
        x_histograms.append(list(np.histogram([], *x_histogram_args, **x_histogram_kwargs)) + [0, 0])
        y_histograms.append(list(np.histogram([], *y_histogram_args, **y_histogram_kwargs)) + [0, 0])
        two_d_histograms.append(list(np.histogram2d([], [], *two_d_histogram_args, **two_d_histogram_kwargs)))
    missing_hits_histogram = list(np.histogram([], *missing_hits_histogram_args, **missing_hits_histogram_kwargs))
    logging.debug(f'{x_histograms=} {y_histograms=} {two_d_histograms=} {missing_hits_histogram=}')
    return [x_histograms, y_histograms, two_d_histograms, missing_hits_histogram]


def add_to_histograms(coordinates, histograms):
    logging.debug('add to histograms')
    for i in range(n_points):
        x = coordinates[:, n_coordinates_per_point * i]
        x_hist = np.histogram(x, *x_histogram_args, **x_histogram_kwargs)[0]
        logging.debug(f'{i=} {x_hist=}')
        histograms[0][i][0] += x_hist
        x_mask = (x >= x_min) & (x <= x_max)
        histograms[0][i][2] += x[x_mask].sum()
        histograms[0][i][3] += (x[x_mask] ** 2).sum()
        y = coordinates[:, n_coordinates_per_point * i + 1]
        y_hist = np.histogram(y, *y_histogram_args, **y_histogram_kwargs)[0]
        logging.debug(f'{i=} {y_hist=}')
        histograms[1][i][0] += y_hist
        y_mask = (y >= y_min) & (y <= y_max)
        histograms[1][i][2] += y[y_mask].sum()
        histograms[1][i][3] += (y[y_mask] ** 2).sum()
        H = np.histogram2d(x, y, *two_d_histogram_args, **two_d_histogram_kwargs)[0]
        logging.debug(f'{i=} {H=}')
        histograms[2][i][0] += H
    missing_hits_hist = np.histogram(np.nonzero(coordinates < 0)[1] + 1, *missing_hits_histogram_args, **missing_hits_histogram_kwargs)[0]
    logging.debug(f'{missing_hits_hist=}')
    histograms[3][0] += missing_hits_hist
    return histograms


def plot_histograms(histograms):
    logging.debug(f'plot {histograms=}')
    for i in range(n_points):
        plt.title(histogram_plot_base_title + str(i + 1) + ', $x$')
        plt.xlabel(x_label)
        plt.xlim(x_min, x_max)
        plt.ylabel(f'Events per {(x_max - x_min) / x_bins} cm')
        x_hist = histograms[0][i][0]
        x_bin_edges = histograms[0][i][1]
        x_n_events = histograms[0][i][0].sum()
        if x_n_events == 0:
            x_mean = float('nan')
            x_std = float('nan')
        else:
            x_mean = histograms[0][i][2] / x_n_events
            x_squared_mean = histograms[0][i][3] / x_n_events
            x_std = (x_squared_mean - x_mean ** 2) ** 0.5
        plt.stairs(x_hist, x_bin_edges, label=f'$\\mu$ = {x_mean:.2f} cm, $\\sigma$ = {x_std:.2f} cm')
        x_histogram_plot_filename = histogram_plot_base_filename + '_' + str(i + 1) + '_x' + histogram_plot_file_extension
        plt.ylim(0, one_d_histogram_y_axis_rescale_factor * plt.ylim()[1])
        plt.legend()
        logging.info(f'save {x_histogram_plot_filename}')
        plt.savefig(x_histogram_plot_filename)
        plt.close()

        plt.title(histogram_plot_base_title + str(i + 1) + ', $y$')
        plt.xlabel(y_label)
        plt.xlim(y_min, y_max)
        plt.ylabel(f'Events per {(y_max - y_min) / y_bins} cm')
        y_hist = histograms[1][i][0]
        y_bin_edges = histograms[1][i][1]
        y_n_events = histograms[1][i][0].sum()
        if y_n_events == 0:
            y_mean = float('nan')
            y_std = float('nan')
        else:
            y_mean = histograms[1][i][2] / y_n_events
            y_squared_mean = histograms[1][i][3] / y_n_events
            y_std = (y_squared_mean - y_mean ** 2) ** 0.5
        plt.stairs(y_hist, y_bin_edges, label=f'$\\mu$ = {y_mean:.2f} cm, $\\sigma$ = {y_std:.2f} cm')
        y_histogram_plot_filename = histogram_plot_base_filename + '_' + str(i + 1) + '_y' + histogram_plot_file_extension
        plt.ylim(0, one_d_histogram_y_axis_rescale_factor * plt.ylim()[1])
        plt.legend()
        logging.info(f'save {y_histogram_plot_filename}')
        plt.savefig(y_histogram_plot_filename)
        plt.close()

        H = histograms[2][i][0].T
        xedges = histograms[2][i][1]
        yedges = histograms[2][i][2]
        X, Y = np.meshgrid(xedges, yedges)
        plt.title(histogram_plot_base_title + str(i + 1))
        plt.pcolormesh(X, Y, H)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.colorbar(label=z_label)
        plt.clim(z_min, z_max)
        two_d_histogram_plot_filename = histogram_plot_base_filename + '_' + str(i + 1) + histogram_plot_file_extension
        logging.info(f'save {two_d_histogram_plot_filename}')
        plt.savefig(two_d_histogram_plot_filename)
        plt.close()

    plt.title('Missing hits')
    plt.xlabel('Module')
    plt.xlim(0.25, n_coordinates_per_point * n_points + 0.75)
    plt.ylabel(f'Events')
    plt.stairs(histograms[3][0], histograms[3][1])
    plt.ylim(0)
    missing_hits_histogram_plot_filename = missing_hits_base_filename + histogram_plot_file_extension
    logging.info(f'save {missing_hits_histogram_plot_filename}')
    plt.savefig(missing_hits_histogram_plot_filename)
    plt.close()


def copy_histograms(run_number=-1):
    histogram_archive_directory_path = Path(histogram_archive_directory_name)
    if not histogram_archive_directory_path.exists():
        logging.info(f'creating {histogram_archive_directory_path}')
        histogram_archive_directory_path.mkdir()
    for i in range(n_points):
        x_histogram_plot_filename = histogram_plot_base_filename + '_' + str(i + 1) + '_x' + histogram_plot_file_extension
        y_histogram_plot_filename = histogram_plot_base_filename + '_' + str(i + 1) + '_y' + histogram_plot_file_extension
        two_d_histogram_plot_filename = histogram_plot_base_filename + '_' + str(i + 1) + histogram_plot_file_extension
        x_histogram_plot_path = Path(x_histogram_plot_filename)
        y_histogram_plot_path = Path(y_histogram_plot_filename)
        two_d_histogram_plot_path = Path(two_d_histogram_plot_filename)
        for path in [x_histogram_plot_path, y_histogram_plot_path, two_d_histogram_plot_path]:
            if path.exists():
                new_histogram_plot_filename = datetime.datetime.now().isoformat(timespec='seconds')  + ('' if run_number < 0 else '_run' + str(run_number)) + '_' + path.name
                logging.info(f'copying {path} to {histogram_archive_directory_path / new_histogram_plot_filename}')
                shutil.copy(path, histogram_archive_directory_path / new_histogram_plot_filename)
    missing_hits_histogram_plot_filename = missing_hits_base_filename + histogram_plot_file_extension
    missing_hits_histogram_plot_path = Path(missing_hits_histogram_plot_filename)
    if missing_hits_histogram_plot_path.exists():
        new_histogram_plot_filename = datetime.datetime.now().isoformat(timespec='seconds') + ('' if run_number < 0 else '_run' + str(run_number)) + '_' + missing_hits_histogram_plot_path.name
        logging.info(f'copying {missing_hits_histogram_plot_path} to {histogram_archive_directory_path / new_histogram_plot_filename}')
        shutil.copy(missing_hits_histogram_plot_path, histogram_archive_directory_path / new_histogram_plot_filename)


def read_last_run_number():
    with open(last_run_number_filename) as f:
        last_run_number = int(f.read(last_run_number_file_byte_limit))
    logging.debug(f'{last_run_number=}')
    return last_run_number


def write_last_run_number(last_run_number):
    with open(last_run_number_filename, 'w') as f:
        f.write(str(last_run_number) + '\n')


def read_current_run_number():
    try:
        with open(daq_monitor_path) as f:
            l = f.readline()
            run_number = int(l.split(':')[1])
    except Exception as e:
        logging.warning(e)
        run_number = -1
    logging.debug(f'{run_number=}')
    return run_number


last_run_number = read_last_run_number()
logging.info('last run number: ' + str(last_run_number))
while True:
    logging.debug('main loop start')

    new_run_number = read_current_run_number()
    if new_run_number > last_run_number:
        logging.info('new run number: ' + str(new_run_number))
        utils.write_run_start_time(time.time())
        write_last_run_number(new_run_number)
        if archive_histograms:
            copy_histograms(last_run_number)
        last_run_number = new_run_number

    run_start_update_time = run_start_time_path.stat().st_mtime
    if run_start_update_time > last_run_start_update_time:
        new_run_start_time = read_run_start_time(run_start_time_path)
        if new_run_start_time != run_start_time:
            logging.info(f'read new run start time {datetime.datetime.fromtimestamp(new_run_start_time).astimezone(options.cern_time_zone).ctime()}')
            if archive_histograms:
                copy_histograms()
            histograms = create_histograms()
            plot_histograms(histograms)
            run_start_time = new_run_start_time
        last_run_start_update_time = run_start_update_time

    tracker_file_directory_update_time = tracker_file_directory_path.stat().st_mtime
    if tracker_file_directory_update_time > last_tracker_file_directory_update_time:
        next_latest_tracker_file_mtime = latest_tracker_file_mtime
        for fp in tracker_file_directory_path.iterdir():
            if not fp.is_file():
                continue
            mtime =  fp.stat().st_mtime
            if fp not in tracker_file_mtimes:
                need_to_parse = False
                if backtrack and mtime > run_start_time:
                    need_to_parse = True
                if mtime > latest_tracker_file_mtime:
                    if last_tracker_file_directory_update_time != default_time:
                        need_to_parse = True
                    next_latest_tracker_file_mtime = mtime
                if need_to_parse:
                    if mtime > tracker_file_directory_update_time - recent_file_time_threshold:
                        logging.debug(f'recent file: {fp}')
                        while True:
                            logging.debug(f'sleeping for {recent_file_write_check_interval} s')
                            time.sleep(recent_file_write_check_interval)
                            new_mtime = fp.stat().st_mtime
                            if new_mtime == mtime:
                                logging.debug('mtime unchanged')
                                break
                            else:
                                mtime = new_mtime
                    new_coordinates = parse(fp)
                    add_to_histograms(new_coordinates, histograms)
                tracker_file_mtimes[fp] = mtime
            elif mtime > tracker_file_mtimes[fp]:
                logging.warning(f'already parsed file has new mtime: {fp}')
        plot_histograms(histograms)
        latest_tracker_file_mtime = next_latest_tracker_file_mtime
        last_tracker_file_directory_update_time = tracker_file_directory_update_time

    logging.debug('main loop end')
    logging.debug(f'sleeping for {loop_delay} s')
    time.sleep(loop_delay)
