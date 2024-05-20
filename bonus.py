import logging

def num_string(n, noun, skip_one=True):
    if skip_one and n == 1:
        return noun
    res = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"][n]
    if noun:
        if n != 1:
            noun += "s"
        res += " " + noun
    return res


class Bonus(object):
    def __init__(self, points_per_cent, initial=0):
        assert isinstance(points_per_cent, int) or isinstance(points_per_cent, float), f"points_per_cent must be a number, but is {points_per_cent}"
        assert isinstance(initial, int) or isinstance(initial, float), f"initial must be a number, but is {initial}"
        self.points = self.initial = initial
        self.points_per_cent = points_per_cent

    def __bool__(self):
        return self.points_per_cent > 0

    def add_points(self, points):
        self.points += int(points)
        logging.debug('add bonus points %s (total = %s)', points, self.points)

    def dollars(self):
        if self.points_per_cent != 0:
            cents = max(0, round(self.points / self.points_per_cent))
            return cents / 100
        else:
            return 0

    def report_bonus(self, kind='current', points=False,):
        msg = f"Your {kind} bonus is ${self.dollars():.2f}"
        if points:
            msg += f" ({self.points} points)"
        return msg

    def describe_scheme(self):
        return "one cent for every " + num_string(self.points_per_cent, "point")

