from multiprocessing import pool as pool
import multiprocessing
import time
from test_auth_app.core.worker import Worker
from test_auth_app.core.test_application.test_application_worker import TestApplicationWorker
import os
import requests


def url_ok(url):
    r = requests.head(url=url)
    return r.status_code == 200


def process_starter(app_label, init_filename, service_origin_uri, user_uid):
    p = multiprocessing.Process(target=worker_runner, args=(app_label, init_filename, service_origin_uri, user_uid))
    print('{}: Starting process: {} / {}'.format(service_origin_uri, app_label, init_filename))
    try:
        # print(p)
        p.start()
        # print('process started\n')
        p.join()
        p.kill()
    except Exception as e:
        print('excepted during starting worker: {}'.format(str(e)))


def worker_runner(app_label, input_filename, service_origin_uri, user_uid):
    if user_uid is None:
        print('E: user_uid is None')
        return
    print('Starting worker: {} -/- {}'.format(app_label, input_filename))
    current_worker = None
    if app_label == 'testapp':
        current_worker = TestApplicationWorker()
    if current_worker is not None:
        if service_origin_uri is not None:
            if service_origin_uri[:8] == 'https://':
                if url_ok(service_origin_uri):
                    current_worker.set_service_uri(service_origin_uri=service_origin_uri)
                    current_worker.set_user_uid(user_uid=user_uid)
                    if current_worker.check_self():
                        current_worker.set_input_filename(input_filename=input_filename)
                        print('Starting worker: {}'.format(current_worker.worker_name))
                        current_worker.process()
                        print('Finished worker: {}'.format(current_worker.worker_name))
                        del current_worker
                        current_worker = None
    else:
        print('worker({}, {}) is None'.format(app_label, input_filename))


class WorkerManager(object):
    def __init__(self, number_of_processors: int = 2, service_origin_uri: str = 'https://testauth.fr.to'):
        self.process_pool = None
        self.number_of_processors = number_of_processors
        self.service_origin_uri = service_origin_uri
        if self.number_of_processors > 0:
            self.process_pool = pool.ThreadPool(processes=self.number_of_processors)

    def append_worker(self, app_label: str = None, init_filename: str = None, user_uid: str = None):
        if app_label is None:
            return
        if init_filename is None:
            return
        if user_uid is None:
            return
        self.process_pool.apply_async(func=process_starter, args=(app_label, init_filename, self.service_origin_uri, user_uid))
        time.sleep(3)
        # TODO: fix this dirty time hack - file 'submitted' or 'error' should be awaited before redirection

    def clean(self):
        self.process_pool.terminate()
        pass
