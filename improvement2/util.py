import math


def hue(signal):
    h = 0.7 * signal
    return h - math.floor(h)


def find_edge(edges, start=None, end=None):
    for edge in edges:
        if edge.start == start and edge.end == end:
            return edge
