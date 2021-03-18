# -*- coding: utf-8 -*-
__author__ = "eduard.snezhko@gmail.com"

from datetime import datetime
import shutil
import os
import sys
import glob
from test_auth_app.backend.api import test_auth_app_flask


#################################################
def dir_size_in_bytes(dirname_='.'):
    """
    from http://stackoverflow.com/questions/1392413/calculating-a-directory-size-using-python
    reqursively calculate size of files in directory
    :param dirname_: directory path
    :return: size in bytes
    """
    total_size = 0
    for dpath, dnames, fnames in os.walk(dirname_):
        for cur_filename in fnames:
            filename = os.path.join(dpath, cur_filename)
            total_size += os.path.getsize(filename)
    return total_size


def human_readable_size(size_in_bytes_):
    """
    from http://stackoverflow.com/questions/1392413/calculating-a-directory-size-using-python
    get size from bytes to human readable format
    :param size_in_bytes_: siz in bytes
    :return: human readable string
    """
    byte_label = "B"
    kbyte_label = "KB"
    mbyte_label = "MB"
    gbyte_label = "GB"
    tbyte_label = "TB"

    units = [byte_label, kbyte_label, mbyte_label, gbyte_label, tbyte_label]
    human_fmt = "%0.1f %s"
    human_radix = 1024.
    for u in units[:-1]:
        if size_in_bytes_ < human_radix:
            return human_fmt % (size_in_bytes_, u)
        size_in_bytes_ /= human_radix
    return human_fmt % (size_in_bytes_, units[-1])


def gen_unique_task_id(prefix=None):
    """
    unique id generator for various DLS tasks
    :param prefix: prefix for task type
    :return: unique string index (list of indexes can be sorted by date)
    """
    task_id = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if prefix is not None:
        ret_task_id = '%s-%s' % (prefix, task_id)
    else:
        ret_task_id = task_id
    return ret_task_id


def make_dir_if_not_exists(dirname_, clean_if_exists_=True):
    """
    create directory if directory is absent
    :param dirname_: path to directory
    :param clean_if_exists_: flag: clean directory if directory exists
    :return: None
    """
    if os.path.isdir(dirname_) and clean_if_exists_:
        shutil.rmtree(dirname_)
    if not os.path.isdir(dirname_):
        os.makedirs(dirname_)


if __name__ == '__main__':
    pass
