# -*- coding: utf-8 -*-
__author__ = "eduard.snezhko@gmail.com"

import os
from copy import deepcopy


class OrientationChecker(object):
    dimensions = 0
    guessed_axes = None
    required_axes = None
    is_valid = False

    def __init__(self, dimensions: int = None):
        self.is_valid = False
        if dimensions is None:
            self.dimensions = 3
        else:
            self.dimensions = dimensions

        if self.dimensions == 1 or self.dimensions > 3:
            # self.dimensions = 3
            self.is_valid = False
            return

        if self.dimensions == 3:
            self.required_axes = [{"name": "X", "index": 0, "direction": "+"},
                                          {"name": "Y", "index": 1, "direction": "+"},
                                          {"name": "Z", "index": 2, "direction": "+"}]

            self.is_valid = True

        if self.dimensions == 2:
            self.required_axes = [{"name": "X", "index": 0, "direction": "+"},
                                          {"name": "Y", "index": 1, "direction": "+"}]
            self.is_valid = True

    def guess_orientation(self, img_filename):

        # TODO: insert orientation guessing
        return self.guessed_axes

    def check_orientation(self, img_filename):
        if not self.valid():
            return False
        if img_filename is None:
            return False
        if not os.path.exists(img_filename):
            return False
        return True

    def fix_orientation(self, img_filename):
        pass

    def required_orientation(self):
        return self.required_axes

    def valid(self):
        return self.is_valid


if __name__ == '__main__':
    pass
