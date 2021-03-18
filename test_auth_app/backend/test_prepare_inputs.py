import os
import numpy as np
import cv2
import nibabel as nib
from copy import deepcopy
import shutil
import tempfile
import requests
import glob
import json
from scipy.ndimage import interpolation
from datetime import datetime, timezone
import magic
import pydicom

from test_auth_app.core.pydcm2nii import pydcm2nii


# import test_auth_app.backend.utils as app_utils


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


def load_series_uids_from_filelist(dcmfiles):
    init_slices = [pydicom.read_file(s) for s in dcmfiles]
    slices = [s for s in init_slices if hasattr(s, 'ImagePositionPatient')]
    series_slices = {}

    for s in slices:
        if s.SeriesInstanceUID not in series_slices:
            series_slices[s.SeriesInstanceUID] = []
        series_slices[s.SeriesInstanceUID].append(1)

    return series_slices


def prepare_inputs(case_dirname):
    init_test_auth_filename_txt = '{}/init_filename.txt'.format(case_dirname)
    init_test_auth_filename_txt = os.path.abspath(init_test_auth_filename_txt)

    init_test_auth_filename = None

    tmp_dir = '{}/raw/'.format(case_dirname)
    if not os.path.exists(tmp_dir):
        print('test_auth_app.prepare_inputs: Directory {} with raw data not exist'.format(tmp_dir))
        return True

    nifti_filenames = []
    nifti_dirname = '{}/nifti/'.format(tmp_dir)
    make_dir_if_not_exists(nifti_dirname, clean_if_exists_=True)

    all_filenames = glob.glob('{}/*'.format(tmp_dir))

    for cur_filename in all_filenames:
        if not os.path.isfile(cur_filename):
            continue
        file_type = magic.from_file(cur_filename).split(' ')[0]
        if file_type == 'gzip':
            if file_type == 'gzip':
                shutil.move(cur_filename, nifti_dirname)
        else:
            os.remove(cur_filename)

    nifti_filenames = glob.glob('{}/*'.format(nifti_dirname))

    if len(nifti_filenames) > 0:
        if os.path.exists(init_test_auth_filename_txt):
            os.remove(init_test_auth_filename_txt)

        result_nifti_filename = None
        max_nifti_depth = 0
        for nifti_filename in nifti_filenames:
            img_nii_shape = nib.load(nifti_filename).get_data().shape
            if img_nii_shape[-1] > max_nifti_depth:
                max_nifti_depth = img_nii_shape[-1]
                result_nifti_filename = nifti_filename
        shutil.copy(result_nifti_filename, case_dirname)

        with open(init_test_auth_filename_txt, 'w') as test_auth_filename_file:
            test_auth_filename_file.write('{}'.format(os.path.basename(result_nifti_filename)))
        with open(init_test_auth_filename_txt, 'r') as test_auth_filename_file:
            test_auth_basename = test_auth_filename_file.read()
        init_test_auth_filename = '{}/{}'.format(case_dirname, test_auth_basename)
        init_test_auth_filename = os.path.abspath(init_test_auth_filename)

    shutil.rmtree(tmp_dir)

    if init_test_auth_filename is not None:
        test_img = nib.load(init_test_auth_filename)
        if len(test_img.shape) != 3:
            if len(test_img.shape) == 4:
                test_img_affine = test_img.affine
                print('Squeezing {}'.format(init_test_auth_filename))
                print('shape = {}'.format(test_img.shape))
                test_img_vol = test_img.get_data()
                test_img_vol = test_img_vol[:, :, :, 0]
                test_img_vol = np.squeeze(test_img_vol)
                nii_img = nib.Nifti1Image(test_img_vol, test_img_affine)
                nib.save(nii_img, init_test_auth_filename)

        return True
    else:
        return False


if __name__ == '__main__':
    case_dirname = '/tmp/111/'
    prepare_inputs(case_dirname=case_dirname)
    pass
