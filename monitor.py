#!/bin/env python3

import csv
import logging
from pathlib import Path
import time

import numpy as np
import matplotlib.pyplot as plt

import options


tracker_file_directory = 'tracker-data-dir'
backtrack = True
loop_delay = 1
x_min = 0
x_max = 10
x_bins = 20
x_label = '$x$ [cm]'
y_min = 0
y_max = 10
y_bins = 20
y_label = '$y$ [cm]'
z_min = 0
z_max = None
z_label = f'Events per {(x_max - x_min) / x_bins} cm $\\times$ {(y_max - y_min) / y_bins} cm'
histogram_plot_base_filename = 'test_plot_'
histogram_plot_base_title = 'Point '
histogram_plot_file_extension = '.png'
debug = False

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
histogram_args = []
histogram_kwargs = {
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
    coordinates = np.asarray(coordinates, dtype=np.float32)
    logging.debug(f'{coordinates=}')
    return coordinates


def create_histograms():
    logging.debug('create histograms')
    histograms = []
    for i in range(n_points):
        histograms.append(list(np.histogram2d([], [], *histogram_args, **histogram_kwargs)))
    logging.debug(f'{histograms=}')
    return histograms


def add_to_histograms(coordinates, histograms):
    logging.debug('add to histograms')
    for i in range(n_points):
        H = np.histogram2d(coordinates[:, n_coordinates_per_point * i], coordinates[:, n_coordinates_per_point * i + 1], *histogram_args, **histogram_kwargs)[0]
        logging.debug(f'{i=} {H=}')
        histograms[i][0] += H
    return histograms


def plot_histograms(histograms):
    logging.debug(f'plot {histograms=}')
    for i in range(n_points):
        H = histograms[i][0].T
        xedges = histograms[i][1]
        yedges = histograms[i][2]
        X, Y = np.meshgrid(xedges, yedges)
        plt.title(histogram_plot_base_title + str(i + 1))
        plt.pcolormesh(X, Y, H)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.colorbar(label=z_label)
        plt.clim(z_min, z_max)
        histogram_filename = histogram_plot_base_filename + str(i) + histogram_plot_file_extension
        logging.info(f'save {histogram_filename}')
        plt.savefig(histogram_filename)
        plt.close()


while True:
    logging.debug('main loop start')

    run_start_update_time = run_start_time_path.stat().st_mtime
    if run_start_update_time > last_run_start_update_time:
        new_run_start_time = read_run_start_time(run_start_time_path)
        if new_run_start_time != run_start_time:
            logging.info(f'read new run start time {time.ctime(new_run_start_time)}')
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
            if fp not in tracker_file_mtimes or mtime > tracker_file_mtimes[fp]:
                need_to_parse = False
                if backtrack and mtime > run_start_time:
                    need_to_parse = True
                if mtime > latest_tracker_file_mtime:
                    if last_tracker_file_directory_update_time != default_time:
                        need_to_parse = True
                    next_latest_tracker_file_mtime = mtime
                if need_to_parse:
                    new_coordinates = parse(fp)
                    add_to_histograms(new_coordinates, histograms)
                tracker_file_mtimes[fp] = mtime
        plot_histograms(histograms)
        latest_tracker_file_mtime = next_latest_tracker_file_mtime
        last_tracker_file_directory_update_time = tracker_file_directory_update_time

    logging.debug('main loop end')
    time.sleep(loop_delay)
