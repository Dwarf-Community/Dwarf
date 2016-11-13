"""General utilities used by Dwarf"""


def estimate_read_time(string):
    read_time = len(string) * 1000  # in milliseconds
    read_time /= 15  # Assuming 15 chars per second
    if read_time < 2400:
        read_time = 2400  # Minimum is 2.4 seconds
    return read_time


def set_digits(integer, number_of_digits):
    return '0' * (number_of_digits - len(str(integer))) + str(integer)
