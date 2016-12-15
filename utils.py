"""A collection of different utilities and shortcuts."""


def estimate_read_time(string):
    read_time = len(string) * 1000  # in milliseconds
    read_time /= 15  # Assuming 15 chars per second
    if read_time < 2400.0:
        read_time = 2400.0  # Minimum is 2.4 seconds
    return read_time / 1000  # return read time in seconds
