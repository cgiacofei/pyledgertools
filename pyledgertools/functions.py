"""Useful functions."""

try:
    from math import gcd
except ImportError:
    from fractions import gcd


def amount_group(val):
    if val < 0:
        prefix = 'n'
    else:
        prefix = 'p'

    val = abs(val)
    if val >= 1000:
        return prefix + str(int(val / 1000) * 1000)
    if val >= 100:
        return prefix + str(int(val / 100) * 100)
    if val >= 10:
        return prefix + str(int(val / 10) * 10)
    else:
        return prefix + '0'


def GCD(dollars):
    """Find greatest common divisor of list of dollar ammounts.

    Works with integer and floats.

    Parameters:
        dollars (list): Values to find the common denominator.
    """

    # Convert dollar values to integers
    dollars = [int(d * 100) for d in dollars]

    res = dollars[0]

    for c in dollars[1::]:
        res = gcd(res, c)

    return res / 100
