# -*- coding: utf-8 -*-
__author__ = "eduard.snezhko@gmail.com"

import os


class AnatomyChecker(object):
    def __init__(self):
        self.is_valid = True
        self.possible_anatomy_options = ['lungs', 'head', 'neck', 'upper limbs', 'lower limbs', 'stomach', 'hip joint', 'None']

    def guess_anatomy(self, img_filename):
        if img_filename is None:
            return self.possible_anatomy_options[-1]
        if not os.path.exists(img_filename):
            return self.possible_anatomy_options[-1]
        # TODO: insert orientation guessing
        guessed_anatomy_label = 'lower limbs'
        return guessed_anatomy_label

    def check_anatomy(self, img_filename, anatomy_label):
        if anatomy_label not in self.possible_anatomy_options:
            return False
        if self.guess_anatomy(img_filename=img_filename) == anatomy_label:
            return True
        return False

    def anatomy_labels(self):
        print(self.possible_anatomy_options)

    def valid(self):
        return self.is_valid


if __name__ == '__main__':
    pass
