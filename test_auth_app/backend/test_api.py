import os
from flask import flash, redirect, request, render_template, Response, make_response, send_file, url_for
import requests
import json
from copy import deepcopy
import time

lungweb_uri = 'https://testauth.fr.to'


def request_cases_list(app_label):
    app_list_ = request_app_list()
    if app_label not in app_list_:
        return []

    req_string = '{}/app/{}/cases_list/'.format(lungweb_uri, app_label)
    res = requests.get(req_string)
    cases_list = []
    if res.ok:
        res_json = res.json()
        # print('request_cases_list:\n\t{}'.format(json.dumps(res_json, indent=4)))
        for elem in res_json:
            cases_list.append(elem['case_id'])
    return cases_list


def request_app_list():
    req_string = '{}/app/app_list/'.format(lungweb_uri)
    res = requests.get(req_string)
    app_list = []
    if res.ok:
        res_json = res.json()
        # print('request_app_list:\n\t{}'.format(json.dumps(res_json, indent=4)))
        app_list = res_json['app_list']
    return app_list


def request_case_info(app_label, case_id):
    # app_list_ = request_app_list()
    # if app_label not in app_list_:
    #     return {}
    # cases_list_ = request_cases_list(app_label)
    # if case_id not in cases_list_:
    #     return {}
    req_string = '{}/app/{}/{}/'.format(lungweb_uri, app_label, case_id)
    res = requests.get(req_string)
    case_info = {}
    if res.ok:
        res_json = res.json()
        # print('request_case_info:\n\t{}'.format(json.dumps(res_json, indent=4)))
        case_info = res_json
    return case_info


def request_case_finished(app_label, case_id):
    case_info_ = request_case_info(app_label, case_id)
    if len(case_info_) > 0:
        if case_info_['is_finished']:
            return True
        else:
            return False
    return False


def request_case_submitted(app_label, case_id):
    case_info_ = request_case_info(app_label, case_id)
    if len(case_info_) > 0:
        if case_info_['is_submitted']:
            return True
        else:
            return False
    return False


def request_case_error(app_label, case_id):
    case_info_ = request_case_info(app_label, case_id)
    if len(case_info_) > 0:
        if case_info_['is_error']:
            return True
        else:
            return False
    return False


def request_case_result(app_label, case_id, out_filename):
    app_list_ = request_app_list()
    if app_label not in app_list_:
        return False
    cases_list_ = request_cases_list(app_label)
    if case_id not in cases_list_:
        return False
    case_info_ = request_case_info(app_label, case_id)
    result_uri = case_info_['proc_url']

    req_string = '{}/{}'.format(lungweb_uri, result_uri)
    res = requests.get(req_string)
    if res.ok:
        print('\twriting output to file {}\n'.format(out_filename))
        with open(out_filename, 'wb') as out_file:
            for chunk in res.iter_content(chunk_size=128):
                out_file.write(chunk)
        return True
    else:
        return False


def request_process_file_list(file_list, app_label):
    filenames_to_process = []
    for filename in file_list:
        if os.path.exists(filename):
            filenames_to_process.append(filename)
    case_ids_ = {}

    for in_filename in filenames_to_process:
        new_case_id_ = request_case_new(app_label, in_filename)
        if new_case_id_ is not None:
            out_filename = in_filename.replace('.nii.gz', '-{}.nii.gz'.format(app_label))
            case_ids_[new_case_id_] = [in_filename, out_filename]
    return case_ids_


def request_case_new(app_label, filename):
    app_list_ = request_app_list()
    new_case_id_ = None
    if app_label not in app_list_:
        return None
    if not os.path.exists(filename):
        return None
    req_string = '{}/{}'.format(lungweb_uri, '/app/{}/new_case/'.format(app_label))
    res = None
    request_body = [('file', (os.path.basename(filename), open(filename, 'rb'), 'application/octet-stream'))]
    res = requests.post(req_string, files=request_body)
    if res.ok:
        new_case_id_ = res.json()['case_id']
        print('Submitted case {} for app {}'.format(new_case_id_, app_label))
    return new_case_id_


def request_case_run(app_label, case_id):
    return


def request_all_finished(app_label=None):
    allowed_app_list = request_app_list()
    app_list = []
    if app_label is not None:
        if app_label in allowed_app_list:
            app_list.append(app_label)
        else:
            return
    else:
        app_list = allowed_app_list
    for app in app_list:
        cases_list = request_cases_list(app_label=app)
        print('{}:\n\t{}\n'.format(app, cases_list))
        for case_id in cases_list:
            case_is_finished = request_case_finished(app, case_id)
            print('\n\t{}:\n\tis_finished = {}'.format(case_id, case_is_finished))
            if case_is_finished:
                case_out_filename = './{}-{}-result.nii.gz'.format(case_id, app)
                result = request_case_result(app, case_id, case_out_filename)


def submit_directory(root_files_dirname, app_label, submitted_case_ids_filename):
    # 1.
    ### Submit the list of files to processing by web services
    ### Save the list of submitted cases to 'submitted_case_ids_filename'
    # As a result of submission we get 'submitted_case_ids', which is a 'dictionary' object.
    # Each element has format submitted_case_ids[case_id] == [input_filename, output_filename]
    # output_filename is generated from input_filename, adding '-[app_label]' at the end.
    filename_list = []
    for folder, subs, files in os.walk(root_files_dirname):
        for filename in sorted(files):
            if '.nii.gz' in filename:
                full_filename = os.path.join(folder, filename)
                filename_list.append(full_filename)

    submitted_case_ids = request_process_file_list(file_list=filename_list, app_label=app_label)
    with open(submitted_case_ids_filename, 'w', encoding='utf-8') as subm_file:
        json.dump(submitted_case_ids, subm_file, ensure_ascii=False, indent=4)


def refresh_finished(app_label, submitted_case_ids_filename, finished_case_ids_filename, error_case_ids_filename):
    # 2.
    ### Refresh list of finished cases. We may retrieve and consider cases for which some error occured during processing.
    ### Load 'submitted_case_ids' from 'submitted_case_ids_filename' file
    ### Save the list of finished cases to 'finished_case_ids_filename'
    finished_case_ids = {}
    error_case_ids = {}

    iteration = 0
    refresh_time_interval = 2

    with open(submitted_case_ids_filename, 'r') as subm_file:
        submitted_case_ids = json.load(subm_file)

    while len(error_case_ids) + len(finished_case_ids) != len(submitted_case_ids):
        print('{} sec: finished {}/{} cases'.format(iteration, len(finished_case_ids), len(submitted_case_ids)))
        iteration += 1
        for case_id in submitted_case_ids:
            is_finished = request_case_finished(app_label=app_label, case_id=case_id)
            is_error = request_case_error(app_label=app_label, case_id=case_id)
            if is_finished:
                finished_case_ids[case_id] = deepcopy(submitted_case_ids[case_id])
            if is_error:
                error_case_ids[case_id] = deepcopy(submitted_case_ids[case_id])
        time.sleep(refresh_time_interval)  # sleep refresh_time_interval seconds between update requests
    # print(finished_case_ids)
    with open(finished_case_ids_filename, 'w', encoding='utf-8') as finish_file:
        json.dump(finished_case_ids, finish_file, ensure_ascii=False, indent=4)
    with open(error_case_ids_filename, 'w', encoding='utf-8') as error_file:
        json.dump(error_case_ids, error_file, ensure_ascii=False, indent=4)


def retrieve_finished_results(app_label, finished_case_ids_filename):
    # 3.
    ### Retrieve finished cases
    ### First read finished_case_ids_filename and iterate over the cases, retrieve and save the results
    with open(finished_case_ids_filename, 'r') as finish_file:
        finished_case_ids = json.load(finish_file)
    for case_id in finished_case_ids:
        out_filename = finished_case_ids[case_id][1]
        request_case_result(app_label=app_label, case_id=case_id, out_filename=out_filename)


if __name__ == '__main__':
    app_label = 'lesions'  # application label.
    submitted_case_ids_filename = './submitted-{}.csv'.format(app_label)
    finished_case_ids_filename = './finished-{}.csv'.format(app_label)
    error_case_ids_filename = './error-{}.csv'.format(app_label)
    root_files_dirname = '/home/snezhko/work/testweb/test_auth_app/frontend/data/data_for_test/'  # root directory where .nii.gz (CT of lungs) files are

    submit_directory(root_files_dirname=root_files_dirname,
                     app_label=app_label,
                     submitted_case_ids_filename=submitted_case_ids_filename)

    refresh_finished(app_label=app_label,
                     submitted_case_ids_filename=submitted_case_ids_filename,
                     finished_case_ids_filename=finished_case_ids_filename,
                     error_case_ids_filename=error_case_ids_filename)

    retrieve_finished_results(app_label=app_label,
                              finished_case_ids_filename=finished_case_ids_filename)

    pass
