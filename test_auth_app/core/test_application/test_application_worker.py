# -*- coding: utf-8 -*-
__author__ = "eduard.snezhko@gmail.com"

from test_auth_app.core.analysis_worker import AnalysisWorker
from test_auth_app.core.worker import *

import os
import numpy as np
import cv2
import nibabel as nib
from copy import deepcopy
import shutil
import tempfile
import glob
import json
from scipy.ndimage import interpolation
from datetime import datetime, timezone
import magic

import test_auth_app.core.test_application.stable_test_app as stable_test_application
from test_auth_app.core.check_anatomy import AnatomyChecker
from test_auth_app.core.check_modality import ModalityChecker
from test_auth_app.core.check_orientation import OrientationChecker

from test_auth_app.core.pydcm2nii import pydcm2nii


class TestApplicationWorker(AnalysisWorker):
    def __init__(self):
        super().__init__()

        self.suffix = 'testapp'
        self.worker_name = '{}Worker'.format(self.suffix.title())

        self.resources_request_filename = '{}/{}'.format(os.path.dirname(os.path.abspath(__file__)), 'test_application_resources_request.json')
        self.resources_request = None
        if not os.path.exists(self.resources_request_filename):
            return
        with open(self.resources_request_filename, 'r') as resource_request_file:
            self.resources_request = json.load(resource_request_file)

    def check_self(self) -> bool:
        return True

    def prepare_inputs(self):
        if self.input_filename is None:
            print('{}Worker: input filename is not specified'.format(self.suffix.title()))
            return False
        else:
            print('{}Worker: input filename is {}'.format(self.suffix.title(), self.input_filename))

        case_dirname = os.path.abspath(os.path.dirname(self.input_filename))
        init_filename_txt = '{}/init_filename.txt'.format(case_dirname)
        init_filename_txt = os.path.abspath(init_filename_txt)

        init_test_app_filename = None

        tmp_dir = '{}/raw/'.format(case_dirname)
        if not os.path.exists(tmp_dir):
            print('test_app.prepare_inputs: Directory {} with raw data not exist'.format(tmp_dir))
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
            if os.path.exists(init_filename_txt):
                os.remove(init_filename_txt)

            result_nifti_filename = None
            max_nifti_depth = 0
            for nifti_filename in nifti_filenames:
                img_nii_shape = nib.load(nifti_filename).get_data().shape
                if img_nii_shape[-1] > max_nifti_depth:
                    max_nifti_depth = img_nii_shape[-1]
                    result_nifti_filename = nifti_filename
            shutil.copy(result_nifti_filename, case_dirname)

            with open(init_filename_txt, 'w') as init_filename_file:
                init_filename_file.write('{}'.format(os.path.basename(result_nifti_filename)))
            with open(init_filename_txt, 'r') as init_filename_file:
                init_basename = init_filename_file.read()
            init_test_app_filename = '{}/{}'.format(case_dirname, init_basename)
            init_test_app_filename = os.path.abspath(init_test_app_filename)
            self.set_input_filename(init_test_app_filename)

        shutil.rmtree(tmp_dir)

        if self.input_filename is not None:
            test_img = nib.load(self.input_filename)
            if len(test_img.shape) != 3:
                if len(test_img.shape) == 4:
                    test_img_affine = test_img.affine
                    print('Squeezing {}'.format(self.input_filename))
                    print('shape = {}'.format(test_img.shape))
                    test_img_vol = test_img.get_data()
                    test_img_vol = test_img_vol[:, :, :, 0]
                    test_img_vol = np.squeeze(test_img_vol)
                    nii_img = nib.Nifti1Image(test_img_vol, test_img_affine)
                    nib.save(nii_img, self.input_filename)

            return True
        else:
            return False

    def check_inputs(self) -> bool:
        if self.input_filename is None:
            print('{}Worker: input filename is None'.format(self.suffix.title()))
            return False
        if not os.path.exists(self.input_filename):
            print('{}Worker: input filename {} not exists'.format(self.suffix.title(), self.input_filename))
            return False
        filename_tokens = os.path.basename(self.input_filename).split('.')
        print('last tokens = {}'.format('.'.join(filename_tokens[-2:])))
        if len(filename_tokens) < 3:
            print('{}Worker: input filename {} is not in nii.gz format'.format(self.suffix.title(), self.input_filename))
            return False
        if not ('.'.join(filename_tokens[-2:]) == 'nii.gz'):
            print('{}Worker: input filename {} is not in nii.gz format'.format(self.suffix.title(), self.input_filename))
            return False
        self.case_id = '.'.join(filename_tokens[:-2])

        if not self.check_modality():
            return False
        if not self.check_anatomy():
            return False
        if not self.check_orientation():
            # TODO: try do reorientation
            pass



        return True

    def check_anatomy(self):
        anatomy_checker = AnatomyChecker()
        ret = anatomy_checker.check_anatomy(img_filename=self.input_filename, anatomy_label='lower limbs')
        return True

    def check_modality(self):
        modality_checker = ModalityChecker()
        ret = modality_checker.check_modality(img_filename=self.input_filename, modality_label='NMR')
        return True

    def check_orientation(self):
        orientation_checker = OrientationChecker()
        ret = orientation_checker.check_orientation(img_filename=self.input_filename)
        return True

    def set_input_filename(self, input_filename: str):
        self.input_filename = input_filename
        self.output_filename = input_filename.replace('.nii.gz', '-{}.nii.gz'.format(self.suffix))
        self.input_preview_filename = self.input_filename.replace('.nii.gz', '-preview.png')
        self.submitted_worker_filename = self.input_filename.replace('.nii.gz', '-{}-submitted.txt'.format(self.suffix))
        self.finished_worker_filename = self.input_filename.replace('.nii.gz', '-{}-finished.txt'.format(self.suffix))
        self.error_filename = self.input_filename.replace('.nii.gz', '-{}-error.txt'.format(self.suffix))
        self.result_zip_filename = self.input_filename.replace('.nii.gz', '-{}-result.zip'.format(self.suffix))

    def gen_input_preview(self):
        img_vol_nii = nib.load(self.input_filename)
        img_vol = img_vol_nii.get_data()
        img_vol_spacing = np.diagonal(img_vol_nii.affine)
        preview_vol = img_vol[:, :, img_vol.shape[2] // 2].astype(np.float32)
        preview_vol = np.flip(preview_vol, axis=1)
        preview_vol = np.transpose(preview_vol, (1, 0))

        max_spacing_value = np.max(img_vol_spacing[:2])
        resize_factor = [max_spacing_value / img_vol_spacing[0], max_spacing_value / img_vol_spacing[1]]
        resize_factor = np.fabs(resize_factor)
        preview_vol = interpolation.zoom(input=preview_vol, zoom=resize_factor, order=1, mode='nearest', prefilter=False)

        min_val = np.min(preview_vol)
        max_val = np.max(preview_vol)

        init_shape = preview_vol.shape
        resize_factor = 512.0 / np.max([init_shape[0], init_shape[1]])
        preview_vol_2 = interpolation.zoom(input=preview_vol, zoom=resize_factor, order=1, mode='nearest', prefilter=False)
        preview_vol = np.zeros((512, 512), np.int16)
        preview_vol[:] = min_val
        x_pos = (preview_vol.shape[0] - preview_vol_2.shape[0]) // 2
        y_pos = (preview_vol.shape[1] - preview_vol_2.shape[1]) // 2
        preview_vol[x_pos:x_pos + preview_vol_2.shape[0], y_pos:y_pos + preview_vol_2.shape[1]] = preview_vol_2

        preview_vol[preview_vol[:] < min_val] = min_val
        preview_vol[preview_vol[:] > max_val] = max_val
        preview_vol = 255. * (preview_vol - min_val) / (max_val - min_val)
        preview_vol = preview_vol.astype(np.uint8)
        cv2.imwrite(self.input_preview_filename, preview_vol)

    def gen_output_preview(self):
        pass

    def gen_output_raycast(self):
        pass

    def process(self) -> bool:
        if not self.prepare_inputs():
            return False
        if not self.check_self():
            return False
        if not self.check_inputs():
            return False
        if not self.check_resources():
            return False
        self.mark_submitted(submitted=False)
        self.mark_finished(finished=False)

        self.gen_input_preview()
        self.mark_submitted()

        is_success = False
        ret_val = True
        try:
            ret_val = 1
            # generate report
            is_success = True
        except:
            is_success = False

        if not is_success or not ret_val:
            self.mark_error()
            return False
        else:
            self.is_success = True

        self.gen_output_zip()
        self.mark_finished()
        return True

    def clean(self):
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)
        if os.path.exists(self.result_zip_filename):
            os.remove(self.result_zip_filename)
        if os.path.exists(self.submitted_worker_filename):
            os.remove(self.submitted_worker_filename)
        if os.path.exists(self.finished_worker_filename):
            os.remove(self.finished_worker_filename)
        if os.path.exists(self.error_filename):
            os.remove(self.error_filename)

    def finished(self) -> bool:
        return self.is_finished

    def mark_submitted(self, submitted=True):
        if os.path.exists(self.submitted_worker_filename):
            os.remove(self.submitted_worker_filename)
        if submitted:
            with open(self.submitted_worker_filename, 'w') as submitted_worker_file:
                submitted_worker_file.write('{}\n'.format(datetime.now(timezone.utc)))

    def mark_finished(self, finished=True):
        if os.path.exists(self.finished_worker_filename):
            os.remove(self.finished_worker_filename)
        if finished:
            self.is_finished = True
            with open(self.finished_worker_filename, 'w') as finished_worker_file:
                finished_worker_file.write('{}\n'.format(datetime.now(timezone.utc)))
        else:
            self.is_finished = False
            self.clean()

    def mark_error(self):
        if os.path.exists(self.error_filename):
            os.remove(self.error_filename)
        self.is_success = False
        with open(self.error_filename, 'w') as error_file:
            error_file.write('{}\n{} segmentation error occurred for case {}\n'.format(datetime.now(timezone.utc), self.suffix.title(), self.case_id))

    def gen_output_zip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            shutil.copy2(self.input_filename, tmp_dir)
            shutil.copy2(self.input_preview_filename, tmp_dir)
            shutil.copy2(self.output_filename, tmp_dir)

            print('going to zip {}'.format(tmp_dir))
            zip_filename = '{}/{}-{}-result.zip'.format('/tmp/', self.get_case_id(), self.suffix)
            shutil.make_archive('{}/{}-{}-result'.format('/tmp/', self.get_case_id(), self.suffix), 'zip', tmp_dir)

            if os.path.exists(self.result_zip_filename):
                os.remove(self.result_zip_filename)
            shutil.move(zip_filename, self.result_zip_filename)

    def get_case_id(self) -> str:
        return self.case_id
