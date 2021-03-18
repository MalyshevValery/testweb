# -*- coding: utf-8 -*-
__author__ = "eduard.snezhko@gmail.com"

import os


class ModalityChecker(object):
    def __init__(self):
        self.possible_modality_options = ['CT', 'CXR', 'NMR', 'None']

    def guess_modality(self, img_filename):
        if img_filename is None:
            return self.possible_modality_options[-1]
        if not os.path.exists(img_filename):
            return self.possible_modality_options[-1]
        # TODO: insert modality guessing
        guessed_modality_label = 'NMR'
        return guessed_modality_label

    def check_modality(self, img_filename, modality_label):
        guessed_modality_label = self.guess_modality(img_filename=img_filename)
        if not (modality_label == guessed_modality_label):
            return False
        return True

    def modalities(self):
        print(self.possible_modality_options)


if __name__ == '__main__':
    pass
