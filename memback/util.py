import math


def hue(signal):
    h = 0.7 * signal
    return h - math.floor(h)
