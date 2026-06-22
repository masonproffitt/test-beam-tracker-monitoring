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


tracker_file_directory = 'tracker-data-dir'
backtrack = True
loop_delay = 1
x_min = 0
x_max = 10
x_bins = 100
x_label = '$x$ [cm]'
y_min = 0
y_max = 10
y_bins = 100
y_label = '$y$ [cm]'
z_min = 0
z_max = None
z_label = f'Events per {(x_max - x_min) / x_bins} cm $\\times$ {(y_max - y_min) / y_bins} cm'
histogram_plot_base_filename = 'test_plot_'
histogram_plot_base_title = 'Station '
histogram_plot_file_extension = '.png'
coordinate_dtype = np.float32
archive_histograms = True
histogram_archive_directory_name = 'histogram_archive'
debug = False
recent_file_time_threshold = 60
recent_file_write_check_interval = 0.1

n_points = 3
n_coordinates_per_point = 2

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
        x_histograms.append(list(np.histogram([], *x_histogram_args, **x_histogram_kwargs)))
        y_histograms.append(list(np.histogram([], *y_histogram_args, **y_histogram_kwargs)))
        two_d_histograms.append(list(np.histogram2d([], [], *two_d_histogram_args, **two_d_histogram_kwargs)))
    logging.debug(f'{x_histograms=} {y_histograms=} {two_d_histograms=}')
    return [x_histograms, y_histograms, two_d_histograms]


def add_to_histograms(coordinates, histograms):
    logging.debug('add to histograms')
    for i in range(n_points):
        x_hist = np.histogram(coordinates[:, n_coordinates_per_point * i], *x_histogram_args, **x_histogram_kwargs)[0]
        logging.debug(f'{i=} {x_hist=}')
        histograms[0][i][0] += x_hist
        y_hist = np.histogram(coordinates[:, n_coordinates_per_point * i + 1], *y_histogram_args, **y_histogram_kwargs)[0]
        logging.debug(f'{i=} {y_hist=}')
        histograms[1][i][0] += x_hist
        H = np.histogram2d(coordinates[:, n_coordinates_per_point * i], coordinates[:, n_coordinates_per_point * i + 1], *two_d_histogram_args, **two_d_histogram_kwargs)[0]
        logging.debug(f'{i=} {H=}')
        histograms[2][i][0] += H
    return histograms


def plot_histograms(histograms):
    logging.debug(f'plot {histograms=}')
    for i in range(n_points):
        plt.title(histogram_plot_base_title + str(i + 1) + ', $x$')
        plt.xlabel(x_label)
        plt.ylabel(f'Events per {(x_max - x_min) / x_bins} cm')
        # x_profile = H.sum(axis=0)
        x_profile = histograms[0][i][0]
        x_bin_edges = histograms[0][i][1]
        x_dist = []
        for j in range(len(x_profile)):
            x_dist += [(x_bin_edges[j] + x_bin_edges[j + 1]) / 2] * int(x_profile[j])
        x_dist = np.asarray(x_dist)
        plt.stairs(x_profile, x_bin_edges, label=f'$\\mu$ = {x_dist.mean():.2f} $\\sigma$ = {x_dist.std():.2f}')
        x_histogram_plot_filename = histogram_plot_base_filename + str(i + 1) + '_x' + histogram_plot_file_extension
        plt.legend()
        logging.info(f'save {x_histogram_plot_filename}')
        plt.savefig(x_histogram_plot_filename)
        plt.close()

        plt.title(histogram_plot_base_title + str(i + 1) + ', $y$')
        plt.xlabel(y_label)
        plt.ylabel(f'Events per {(y_max - y_min) / y_bins} cm')
        y_profile = histograms[1][i][0]
        y_bin_edges = histograms[1][i][1]
        # y_profile = H.sum(axis=1)
        y_dist = []
        for j in range(len(y_profile)):
            y_dist += [(y_bin_edges[j] + y_bin_edges[j + 1]) / 2] * int(y_profile[j])
        y_dist = np.asarray(y_dist)
        plt.stairs(y_profile, y_bin_edges, label=f'$\\mu$ = {y_dist.mean():.2} $\\sigma$ = {y_dist.std():.2}')
        y_histogram_plot_filename = histogram_plot_base_filename + str(i + 1) + '_y' + histogram_plot_file_extension
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
        two_d_histogram_plot_filename = histogram_plot_base_filename + str(i + 1) + histogram_plot_file_extension
        logging.info(f'save {two_d_histogram_plot_filename}')
        plt.savefig(two_d_histogram_plot_filename)
        plt.close()


def copy_histograms():
    histogram_archive_directory_path = Path(histogram_archive_directory_name)
    if not histogram_archive_directory_path.exists():
        logging.info(f'creating {histogram_archive_directory_path}')
        histogram_archive_directory_path.mkdir()
    for i in range(n_points):
        x_histogram_plot_filename = histogram_plot_base_filename + str(i + 1) + '_x' + histogram_plot_file_extension
        y_histogram_plot_filename = histogram_plot_base_filename + str(i + 1) + '_y' + histogram_plot_file_extension
        two_d_histogram_plot_filename = histogram_plot_base_filename + str(i) + histogram_plot_file_extension
        x_histogram_plot_path = Path(x_histogram_plot_filename)
        y_histogram_plot_path = Path(y_histogram_plot_filename)
        two_d_histogram_plot_path = Path(two_d_histogram_plot_filename)
        for path in [x_histogram_plot_path, y_histogram_plot_path, two_d_histogram_plot_path]:
            if path.exists():
                new_histogram_plot_filename = datetime.datetime.now().isoformat(timespec='seconds') + '_' + path.name
                logging.info(f'copying {path} to {histogram_archive_directory_path / new_histogram_plot_filename}')
                shutil.copy(path, histogram_archive_directory_path / new_histogram_plot_filename)


while True:
    logging.debug('main loop start')

    run_start_update_time = run_start_time_path.stat().st_mtime
    if run_start_update_time > last_run_start_update_time:
        new_run_start_time = read_run_start_time(run_start_time_path)
        if new_run_start_time != run_start_time:
            logging.info(f'read new run start time {time.ctime(new_run_start_time)}')
            if archive_histograms:
                copy_histograms()
            histograms = create_histograms()
            run_start_time = new_run_start_time
            logging.debug(f'{run_start_time=}')
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
