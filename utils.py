import options


def write_run_start_time(time):
    with open(options.run_start_time_filename, 'w') as f:
        f.write(str(time) + '\n')
