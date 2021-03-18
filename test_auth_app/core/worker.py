# -*- coding: utf-8 -*-
__author__ = "eduard.snezhko@gmail.com"

import os
import pydicom
import shutil
import requests
import json
from test_auth_app.core.resource_manager import ResourceManager


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


def request_case_info(service_origin_uri, app_label, case_uid, user_uid=None):
    if user_uid is None:
        return {}
    req_string = '{}/app/{}/{}/'.format(service_origin_uri, app_label, case_uid)
    res = requests.request(method='GET', url=req_string, headers={'X-uuid': '{}'.format(user_uid), 'X-internal': 'True'})
    case_info = {}
    if res.ok:
        res_json = res.json()
        # print('request_case_info:\n\t{}'.format(json.dumps(res_json, indent=4)))
        case_info = res_json
    return case_info


def request_case_finished(service_origin_uri, app_label, case_uid, user_uid):
    case_info_ = request_case_info(service_origin_uri, app_label, case_uid, user_uid)
    if len(case_info_) > 0:
        if case_info_['is_finished']:
            return True
        else:
            return False
    return False


def request_case_submitted(service_origin_uri, app_label, case_uid, user_uid):
    case_info_ = request_case_info(service_origin_uri, app_label, case_uid, user_uid)
    if len(case_info_) > 0:
        if case_info_['is_submitted']:
            return True
        else:
            return False
    return False


def request_case_error(service_origin_uri, app_label, case_uid, user_uid):
    case_info_ = request_case_info(service_origin_uri, app_label, case_uid, user_uid)
    if len(case_info_) > 0:
        if case_info_['is_error']:
            return True
        else:
            return False
    return False


class Worker(object):
    def __init__(self):
        self.service_origin_uri = None

        self.input_filename = None
        self.output_filename = None
        self.input_preview_filename = None
        self.submitted_worker_filename = None
        self.finished_worker_filename = None
        self.error_filename = None
        self.result_zip_filename = None

        self.case_id = None
        self.case_uid = None
        self.user_uid = None
        self.worker_name = 'basic worker'
        self.suffix = 'basic-worker'
        self.is_finished = False
        self.is_success = False

        self.resources_request_filename = None
        self.resources_request = None

    def check_self(self) -> bool:
        pass

    def prepare_inputs(self) -> bool:
        pass

    def check_inputs(self) -> bool:
        pass

    def check_resources(self) -> bool:
        r_manager = ResourceManager(storage_path=os.path.dirname(self.input_filename))
        can_run = r_manager.can_run(self.resources_request)
        if not can_run:
            self.mark_error()
            return False

        if self.resources_request['gpu']['required']['value'] > 0:
            print('Requesting GPU = {}'.format(self.resources_request['vram']['required']['value']))
            import tensorflow as tf
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                try:
                    tf.config.experimental.set_virtual_device_configuration(gpus[0],
                                                                            [tf.config.experimental.VirtualDeviceConfiguration(
                                                                                memory_limit=self.resources_request['vram']['required']['value'])])
                    logical_gpus = tf.config.experimental.list_logical_devices('GPU')
                    print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
                except RuntimeError as e:
                    # Virtual devices must be set before GPUs have been initialized
                    print(e)
        return True

    def check_anatomy(self) -> bool:
        pass

    def check_modality(self) -> bool:
        pass

    def check_orientation(self) -> bool:
        pass

    def set_service_uri(self, service_origin_uri: str):
        self.service_origin_uri = service_origin_uri

    def set_user_uid(self, user_uid: str):
        self.user_uid = user_uid

    def set_input_filename(self, input_filename: str):
        pass

    def gen_input_preview(self):
        pass

    def process(self) -> bool:
        pass

    def clean(self):
        pass

    def finished(self) -> bool:
        pass

    def mark_submitted(self, submitted=True):
        pass

    def mark_finished(self, finished=True):
        pass

    def mark_error(self):
        pass

    def gen_output_zip(self):
        pass

    def get_case_id(self) -> str:
        pass

    def get_case_uid(self) -> str:
        pass
