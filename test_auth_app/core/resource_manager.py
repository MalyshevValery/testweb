# -*- coding: utf-8 -*-
__author__ = "eduard.snezhko@gmail.com"

import os
import psutil
import json
import numpy as np
import nvgpu
from jsonschema import validate as json_validate


class ResourceManager(object):
    def __init__(self, storage_path):
        self.storage_path = storage_path
        self.is_valid = False
        self.resources_schema = None
        self.resources_request_schema = None
        self.gpu_idx = None

        resources_schema_filename = '{}/{}'.format(os.path.dirname(os.path.abspath(__file__)), 'resources.schema.json')
        if not os.path.exists(resources_schema_filename):
            print('file {} not exists'.format(resources_schema_filename))
            return
        with open(resources_schema_filename, 'r') as resource_schema_file:
            self.resources_schema = json.load(resource_schema_file)
        if self.resources_schema is None:
            return

        resources_request_schema_filename = '{}/{}'.format(os.path.dirname(os.path.abspath(__file__)), 'resources_request.schema.json')
        if not os.path.exists(resources_request_schema_filename):
            print('file {} not exists'.format(resources_request_schema_filename))
            return
        with open(resources_request_schema_filename, 'r') as resource_request_schema_file:
            self.resources_request_schema = json.load(resource_request_schema_file)
        if self.resources_request_schema is None:
            return

        self.is_valid = True

    def valid(self):
        return self.is_valid

    def resources_total(self):
        pass

    def resources_available(self):
        res_available = {
            'cpu': {
                'total': {
                    'units': 'unit',
                    'value': self._cpu_total()
                },
                'available': {
                    'units': 'unit',
                    'value': self._cpu_available()
                }
            },
            'gpu': {
                'total': {
                    'units': 'unit',
                    'value': self._gpu_total()
                },
                'available': {
                    'units': 'unit',
                    'value': self._gpu_available()
                }
            },
            'ram': {
                'total': {
                    'units': 'MB',
                    'value': self._ram_total()
                },
                'available': {
                    'units': 'MB',
                    'value': self._ram_available()
                }
            },
            'vram': {
                'total': {
                    'units': 'MB',
                    'value': self._vram_total()
                },
                'available': {
                    'units': 'MB',
                    'value': self._vram_available()
                }
            },
            'storage': {
                'total': {
                    'units': 'MB',
                    'value': self._storage_total()
                },
                'available': {
                    'units': 'MB',
                    'value': self._storage_available()
                }
            }
        }
        return res_available

    def validate(self, json_object, json_schema):
        try:
            json_validate(instance=json_object, schema=json_schema)
        except ValueError as e:
            print(e)
            return False
        return True

    def can_run(self, worker_requirements):
        # check if resource schema is loaded correctly
        if not self.valid():
            print('Resource manager is not valid')
            return False
        # validate available resources description as json
        res_available = self.resources_available()
        try:
            json.loads(json.dumps(res_available))
        except ValueError as e:
            print('E: ResourceManager.can_run(): res_available is not a valid json')
            print(e)
            return False
        if not self.validate(json_object=res_available, json_schema=self.resources_schema):
            return False
        # validate passed worker requirements described as json
        try:
            json.loads(json.dumps(worker_requirements))
        except ValueError as e:
            print('E: ResourceManager.can_run(): worker_requirements is not a valid json')
            print(e)
            return False
        if not self.validate(json_object=worker_requirements, json_schema=self.resources_request_schema):
            return False
        # iterate over available resources and compare with worker requirements
        for resource_key in res_available:
            available_value = res_available[resource_key]['available']['value']
            requested_value = worker_requirements[resource_key]['required']['value']
            if requested_value > available_value:
                return False
        return True

    def _cpu_total(self):
        cpu_total = psutil.cpu_count()
        return int(cpu_total)

    def _cpu_available(self):
        cpu_available = int(psutil.cpu_count() * (1.0 - psutil.getloadavg()[0]/psutil.cpu_count()))
        return int(cpu_available)

    def _gpu_total(self):
        gpu_total = len(nvgpu.gpu_info())
        return int(gpu_total)

    def _gpu_available(self):
        vram_available = []
        gpu_info = nvgpu.gpu_info()
        if len(gpu_info) == 0:
            return None
        for g_info in gpu_info:
            vram_available.append(int(g_info['mem_total'] - g_info['mem_used'] - 100))
        max_vram_idx = np.argmax(vram_available)
        self.gpu_idx = '{}'.format(max_vram_idx)
        os.environ["CUDA_VISIBLE_DEVICES"] = '{}'.format(max_vram_idx)
        return int(1)

    def _gpu_idx(self):
        return self.gpu_idx

    def _ram_total(self):
        ram_total = int(psutil.virtual_memory().total / 1048576)
        return int(ram_total)

    def _ram_available(self):
        ram_available = int(psutil.virtual_memory().available / 1048576)
        return int(ram_available)

    def _vram_total(self):
        vram_total_list = []
        gpu_info = nvgpu.gpu_info()
        if len(gpu_info) == 0:
            return 0
        for g_info in gpu_info:
            vram_total_list.append(int(g_info['mem_total']))
        vram_total = np.sum(vram_total_list)
        return int(vram_total)

    def _vram_available(self):
        vram_available_list = []
        gpu_info = nvgpu.gpu_info()
        if len(gpu_info) == 0:
            return 0
        for g_info in gpu_info:
            vram_available_list.append(int(g_info['mem_total'] - g_info['mem_used'] - 100))

        max_vram_idx = np.argmax(vram_available_list)
        vram_available = vram_available_list[max_vram_idx]
        return int(vram_available)

    def _storage_total(self):
        disk_usage = psutil.disk_usage(self.storage_path)
        storage_total = int(disk_usage.total/1048576)
        return int(storage_total)

    def _storage_available(self):
        disk_usage = psutil.disk_usage(self.storage_path)
        storage_available = int(0.5*disk_usage.free/1048576)
        return int(storage_available)
