# -*- coding: utf-8 -*-
__author__ = "eduard.snezhko@gmail.com"

import os
from test_auth_app.backend import test_auth_app_flask
from test_auth_app.backend import utils as utils
from test_auth_app.backend import test_auth_app_manager
from test_auth_app.backend import test_auth_app_db
from test_auth_app.backend.db_models import get_default_roles, get_default_applications
# from test_auth_app.backend.forms import LoginForm, RegistrationForm
from test_auth_app.core.test_application.test_application_worker import TestApplicationWorker

from test_auth_app.core.pydcm2nii import pydcm2nii

import json
from flask import flash, redirect, request, render_template, Response, make_response, send_file, url_for
from werkzeug.utils import secure_filename
from flask_login import current_user, login_user, logout_user, login_required
from test_auth_app.backend.db_models import User, Role, Application

from uuid import uuid1
import glob
from copy import deepcopy
import shutil
import pydicom
import nibabel as nib
import numpy as np
import tempfile


##########################################
def allowed_nifti_file(filename):
    filename_tokens = filename.split('.')
    print('last tokens = {}'.format('.'.join(filename_tokens[-2:])))
    if len(filename_tokens) < 3:
        return False
    if '.'.join(filename_tokens[-2:]) == 'nii.gz':
        return True
    return False


def get_app_labels():
    app_labels = {'testapp'}
    return app_labels


def allowed_app_label(app_label=None):
    app_labels = get_app_labels()
    if app_label is None:
        return False
    if app_label not in app_labels:
        return False
    return True


def save_uploaded_file(output_dirname, f_, same_):
    if not os.path.isdir(output_dirname):
        os.makedirs(output_dirname)
    file_extension = f_.filename.split('.')[-1]
    file_name = f_.filename

    output_filename = '{}/{}'.format(output_dirname, file_name)
    print('Saving output_filename to {}'.format(output_filename))
    f_.save(output_filename)


def load_series_uid(path):
    dcmfiles = [os.path.join(root, name)
                for root, dirs, files in os.walk(path)
                for name in files
                if name.endswith(".dcm")]

    init_slices = [pydicom.read_file(s) for s in dcmfiles]
    slices = [s for s in init_slices if hasattr(s, 'ImagePositionPatient')]
    series_slices = {}

    for s in slices:
        if s.SeriesInstanceUID not in series_slices:
            series_slices[s.SeriesInstanceUID] = []
            series_slices[s.SeriesInstanceUID].append(1)

    return series_slices


def dir_data():
    return test_auth_app_flask.config['DIR_DATA']


def get_response(retcode=0, errorstr='', result=None):
    return {
        'ret_code': retcode,
        'error_string': errorstr,
        'response': result
    }


def get_number_of_pages(session_id=None, app_label=None, user_uid=None):
    if session_id is None:
        return []
    if app_label is None:
        return []
    if user_uid is None:
        return []
    if not allowed_app_label(app_label=app_label):
        return []

    cases_per_page = 12

    # sessionId = request.session.session_key
    root_data_dir = test_auth_app_flask.config['DIR_DATA']

    if user_uid is None:
        cases_dir_list = glob.glob('{}/case-*/'.format(root_data_dir))
    else:
        cases_dir_list = glob.glob('{}/{}/case-*/'.format(root_data_dir, user_uid))

    num_pages = len(cases_dir_list) // cases_per_page
    num_pages += (int(len(cases_dir_list)) % cases_per_page > 0)
    # print('num_pages = {}'.format(num_pages))

    return num_pages


def get_cases_list(session_id=None, app_label=None, page_id=None, user_uid=None):
    if session_id is None:
        return []
    if app_label is None:
        return []
    if user_uid is None:
        return []
    if not allowed_app_label(app_label=app_label):
        return []
    if page_id is None:
        page_id = 1
    try:
        page_id = int(page_id)
    except:
        return []

    cases_per_page = 12
    # print('page_id = {}'.format(page_id))

    # sessionId = request.session.session_key
    root_data_dir = test_auth_app_flask.config['DIR_DATA']
    if user_uid is None:
        cases_dir_list = glob.glob('{}/{}/case-*/'.format(root_data_dir, app_label))
    else:
        cases_dir_list = glob.glob('{}/{}/{}/case-*/'.format(root_data_dir, user_uid, app_label))

    lower_case_id = 0
    upper_case_id = len(cases_dir_list)

    num_pages = len(cases_dir_list) // cases_per_page
    num_pages += int(len(cases_dir_list) % cases_per_page)
    if page_id > num_pages:
        page_id = num_pages

    if page_id == 0:
        lower_case_id = 0
        upper_case_id = len(cases_dir_list)
    else:
        lower_case_id = (page_id - 1) * cases_per_page
        upper_case_id = np.min([len(cases_dir_list), page_id * cases_per_page])

    # for i in range(len(cases_dir_list)):
    actual_cases_dir_list = []
    for i in range(lower_case_id, upper_case_id):
        actual_cases_dir_list.append(os.path.abspath(cases_dir_list[i]))

    counter = 0
    ret = []
    for cur_dir in actual_cases_dir_list:
        case_id = cur_dir.split('/')[-1]
        case_id = '-'.join(case_id.split('-')[1:])

        init_test_auth_filename_txt = '{}/init_filename.txt'.format(cur_dir)
        init_test_auth_filename_txt = os.path.abspath(init_test_auth_filename_txt)

        if not os.path.exists(init_test_auth_filename_txt):
            continue

        with open(init_test_auth_filename_txt, 'r') as test_auth_filename_file:
            test_auth_basename = test_auth_filename_file.read()

        # check case_id
        init_test_auth_filename = '{}/{}'.format(cur_dir, test_auth_basename)
        init_test_auth_filename = os.path.abspath(init_test_auth_filename)

        input_filename = init_test_auth_filename
        proc_filename = input_filename.replace('.nii.gz', '-{}.nii.gz'.format(app_label))
        input_preview_filename = input_filename.replace('.nii.gz', '-preview.png')

        zip_result_filename = input_filename.replace('.nii.gz', '-{}-result.zip'.format(app_label))
        error_filename = input_filename.replace('.nii.gz', '-{}-error.txt'.format(app_label))

        submitted_task_filename = input_filename.replace('.nii.gz', '-{}-submitted.txt'.format(app_label))
        finished_task_filename = input_filename.replace('.nii.gz', '-{}-finished.txt'.format(app_label))

        is_finished = False
        is_error = False
        is_submitted = False
        error_text = ''

        if os.path.exists(submitted_task_filename):
            is_submitted = True
        if os.path.exists(finished_task_filename):
            is_finished = True
        if os.path.exists(error_filename):
            is_error = True

        if not is_submitted:
            is_finished = False
            is_error = False
        else:
            if not is_finished:
                is_error = False

        if os.path.isfile(input_filename):
            web_dirname = '/data/{}/{}/case-{}'.format(user_uid, app_label, case_id)
            input_url = ''
            proc_url = ''
            input_preview_url = ''
            proc_preview_url = ''
            zip_result_url = ''
            proc_rgb_url = ''
            proc_raycast_url = ''
            annotation_url = ''

            if not is_submitted or is_error:
                input_url = '{}/{}'.format(web_dirname, test_auth_basename)
                input_preview_url = input_url.replace('.nii.gz', '-preview.png')
                if is_error:
                    try:
                        with(open(error_filename, 'r')) as err_file:
                            error_text = err_file.read().replace('\n', '<br>')
                    except:
                        error_text = 'Unknown Error<br>'
            else:
                if is_finished:
                    input_url = '{}/{}'.format(web_dirname, test_auth_basename)
                    proc_url = input_url.replace('.nii.gz', '-{}.nii.gz'.format(app_label))
                    proc_rgb_url = input_url.replace('.nii.gz', '-{}-rgb.nii.gz'.format(app_label))
                    proc_raycast_url = input_url.replace('.nii.gz', '-{}-raycast.nii.gz'.format(app_label))
                    input_preview_url = input_url.replace('.nii.gz', '-preview.png')
                    proc_preview_url = input_url.replace('.nii.gz', '-{}-preview.png'.format(app_label))
                    zip_result_url = input_url.replace('.nii.gz', '-{}-result.zip'.format(app_label))
                    annotation_url = input_url.replace('.nii.gz', '-{}-annotation.png'.format(app_label))
                else:
                    input_url = '{}/{}'.format(web_dirname, test_auth_basename)
                    input_preview_url = input_url.replace('.nii.gz', '-preview.png')

            case_info = {'case_id': case_id,
                         'case_name': test_auth_basename,
                         'app_label': app_label,
                         'input_preview_url': input_preview_url,
                         'proc_preview_url': proc_preview_url,
                         'zip_result_url': zip_result_url,
                         'input_url': input_url,
                         'proc_url': proc_url,
                         'proc_rgb_url': proc_rgb_url,
                         'proc_raycast_url': proc_raycast_url,
                         'annotation_url': annotation_url,
                         'w': 200,
                         'h': 200,
                         'is_finished': is_finished,
                         'is_submitted': is_submitted,
                         'is_error': is_error,
                         'error_text': error_text}
            ret.append(case_info)
        counter += 1
    return ret


def get_case(session_id=None, app_label=None, case_id=None, user_uid=None):
    if case_id is None:
        return []
    if session_id is None:
        return []
    if app_label is None:
        return []
    if user_uid is None:
        return []
    if not allowed_app_label(app_label=app_label):
        return []
    # sessionId = request.session.session_key
    root_data_dir = test_auth_app_flask.config['DIR_DATA']

    ret = []

    if user_uid is None:
        cur_dir = '{}/{}/case-{}/'.format(root_data_dir, app_label, case_id)
    else:
        cur_dir = '{}/{}/{}/case-{}/'.format(root_data_dir, user_uid, app_label, case_id)
    if not os.path.exists(cur_dir):
        return []

    init_test_auth_filename_txt = '{}/init_filename.txt'.format(cur_dir)
    init_test_auth_filename_txt = os.path.abspath(init_test_auth_filename_txt)

    with open(init_test_auth_filename_txt, 'r') as test_auth_filename_file:
        test_auth_basename = test_auth_filename_file.read()

    # check case_id
    init_test_auth_filename = '{}/{}'.format(cur_dir, test_auth_basename)
    init_test_auth_filename = os.path.abspath(init_test_auth_filename)

    input_filename = init_test_auth_filename
    proc_filename = input_filename.replace('.nii.gz', '-{}.nii.gz'.format(app_label))
    input_preview_filename = input_filename.replace('.nii.gz', '-preview.png')

    zip_result_filename = input_filename.replace('.nii.gz', '-{}-result.zip'.format(app_label))
    error_filename = input_filename.replace('.nii.gz', '-{}-error.txt'.format(app_label))

    submitted_task_filename = input_filename.replace('.nii.gz', '-{}-submitted.txt'.format(app_label))
    finished_task_filename = input_filename.replace('.nii.gz', '-{}-finished.txt'.format(app_label))

    is_finished = False
    is_error = False
    is_submitted = False
    error_text = ''

    if os.path.exists(submitted_task_filename):
        is_submitted = True
    if os.path.exists(finished_task_filename):
        is_finished = True
    if os.path.exists(error_filename):
        is_error = True

    if not is_submitted:
        is_finished = False
        is_error = False
    else:
        if not is_finished:
            is_error = False

    if os.path.isfile(input_filename):
        web_dirname = '/data/{}/{}/case-{}'.format(user_uid, app_label, case_id)
        input_url = ''
        proc_url = ''
        input_preview_url = ''
        zip_result_url = ''

        if not is_submitted or is_error:
            input_url = '{}/{}'.format(web_dirname, test_auth_basename)
            input_preview_url = input_url.replace('.nii.gz', '-preview.png')
            if is_error:
                try:
                    with(open(error_filename, 'r')) as err_file:
                        error_text = err_file.read().replace('\n', '<br>')
                except:
                    error_text = 'Unknown Error<br>'
        else:
            if is_finished:
                input_url = '{}/{}'.format(web_dirname, test_auth_basename)
                proc_url = input_url.replace('.nii.gz', '-{}.nii.gz'.format(app_label))
                input_preview_url = input_url.replace('.nii.gz', '-preview.png')
                zip_result_url = input_url.replace('.nii.gz', '-{}-result.zip'.format(app_label))
            else:
                input_url = '{}/{}'.format(web_dirname, test_auth_basename)
                input_preview_url = input_url.replace('.nii.gz', '-preview.png')

        case_info = {'case_id': case_id,
                     'case_name': test_auth_basename,
                     'app_label': app_label,
                     'input_preview_url': input_preview_url,
                     'zip_result_url': zip_result_url,
                     'input_url': input_url,
                     'proc_url': proc_url,
                     'w': 200,
                     'h': 200,
                     'is_finished': is_finished,
                     'is_submitted': is_submitted,
                     'is_error': is_error,
                     'error_text': error_text}
        ret.append(case_info)

    return ret


@test_auth_app_flask.route('/api/')
def api_page():
    return render_template('testweb_api.html')


# login
@test_auth_app_flask.route('/login/', methods=['GET', 'POST'])
def page_login():
    if current_user.is_authenticated and current_user.is_validated() and not current_user.email == 'empty@email.org':
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        user_email = User.query.filter_by(email=form.email.data).first()
        if user_email is None or not user_email.check_password(form.password.data):
            flash('Invalid username or password: user = {}'.format(form.email.data))
            print('Invalid username or password: user = {}'.format(form.email.data))
            return redirect(url_for('page_login'))
        else:
            validated = user_email.is_validated()
            if not validated:
                flash('User {} not validated yet'.format(user_email))
                print('User {} not validated yet'.format(user_email))
                return redirect(url_for('page_login'))
            print('Password passed')
        login_user(user=user_email, remember=form.remember_me.data)
        # flash('You logged as {}'.format(form.email.data, form.remember_me.data))
        return redirect('/')
    return render_template('login.html', title='Log in', form=form)


# logout
@test_auth_app_flask.route('/logout/')
def page_logout():
    logout_user()
    return redirect('/')


# register
@test_auth_app_flask.route('/register/', methods=['GET', 'POST'])
def page_register():
    # if current_user.is_authenticated:
    #     return redirect('/')
    # form = RegistrationForm()
    # if form.validate_on_submit():
    #     user_uid = str(uuid1())
    #
    #     new_user = User(email=form.email.data, user_uid=user_uid)
    #     new_user.set_password(form.password.data)
    #     new_roles = get_default_roles()
    #     for role in new_roles:
    #         new_user.roles.append(role)
    #     new_apps = get_default_applications()
    #     for app in new_apps:
    #         new_user.applications.append(app)
    #     new_user.set_validated(False)
    #     test_auth_app_db.session.add(new_user)
    #     test_auth_app_db.session.commit()
    #     if os.path.exists('./validation_request.txt'):
    #         with open('./validation_requests.txt', 'a+') as req_file:
    #             req_file.write('{}, requested for registration\n'.format(new_user.username))
    #     else:
    #         with open('./validation_requests.txt', 'w') as req_file:
    #             req_file.write('{}, requested for registration\n'.format(new_user.username))
    #     return redirect('/login/')
    # return render_template('register.html', title='Register', form=form)
    pass


##########################################
@test_auth_app_flask.route('/')
@test_auth_app_flask.route('/index/')
@test_auth_app_flask.route('/home/')
def index():
    user = {'nickname': 'unknown'}
    return render_template("index.html", title='Home', user=user)


@test_auth_app_flask.errorhandler(401)
def page_not_logged_in(error):
    # print('User is not logged in')
    return redirect('/login/')


@test_auth_app_flask.errorhandler(404)
def page_not_found(error):
    return redirect('/')


@test_auth_app_flask.errorhandler(500)
def page_internal_server(error):
    return 'Internal server error', 500


##########################################

@test_auth_app_flask.route('/app/<app_label>/', methods=['GET'])
def app_page(app_label):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    cases_list = []
    number_of_pages = 0
    if current_user is not None:
        print('current_user is not None')
        if current_user.is_authenticated:
            print('current_user is authenticated')
            cases_list = get_cases_list(session_id='dummy_session_id', app_label=app_label, user_uid=current_user.user_uid)
            number_of_pages = get_number_of_pages(session_id='dummy_session_id', app_label=app_label, user_uid=current_user.user_uid)
        else:
            print('current_user is not authenticated')
    else:
        print('current_user is None')

    return render_template('app_{}.html'.format(app_label), uploadedImages=cases_list, numberOfPages=number_of_pages, currentPageID=1)


@test_auth_app_flask.route('/app/<app_label>/<page_id>', methods=['GET'])
def app_page_by_id(app_label, page_id):
    # check app_label
    print('Entered to app_page_by_id')
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    cases_list = []
    number_of_pages = 0
    if current_user is not None:
        if current_user.is_authenticated:
            cases_list = get_cases_list(session_id='dummy_session_id', app_label=app_label, page_id=page_id, user_uid=current_user.user_uid)
            number_of_pages = get_number_of_pages(session_id='dummy_session_id', app_label=app_label, user_uid=current_user.user_uid)

    return render_template('app_{}.html'.format(app_label), uploadedImages=cases_list, numberOfPages=number_of_pages, currentPageID=page_id)


@test_auth_app_flask.route('/app/<app_label>/pages/', methods=['GET'])
def app_number_of_pages(app_label):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    number_of_pages = 0
    if current_user is not None:
        if current_user.is_authenticated:
            cases_list = get_cases_list(session_id='dummy_session_id', app_label=app_label, page_id=-1, user_uid=current_user.user_uid)
            number_of_pages = get_number_of_pages(session_id='dummy_session_id', app_label=app_label, user_uid=current_user.user_uid)

    return Response(json.dumps({'number_of_pages': number_of_pages}), mimetype='application/json')


@test_auth_app_flask.route('/app/app_list/', methods=['GET'])
def app_page_app_list():
    app_labels = get_app_labels()
    ret = {'app_list': list(app_labels)}
    # print(ret)
    return json.dumps(ret)


@test_auth_app_flask.route('/app/<app_label>/cases_list/', methods=['GET'])
# @login_required
def app_page_cases_list(app_label):
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    cases_list = []
    if current_user is not None:
        if current_user.is_authenticated:
            cases_list = get_cases_list(session_id='dummy_session_id', app_label=app_label, page_id=0, user_uid=current_user.user_uid)

    return json.dumps(cases_list)


@test_auth_app_flask.route('/app/<app_label>/<case_id>/', methods=['GET'])
def app_page_case_info(app_label, case_id):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    cases_list = []
    if current_user is not None:
        if current_user.is_authenticated:
            cases_list = get_case(session_id='dummy session id', app_label=app_label, case_id=case_id, user_uid=current_user.user_uid)

    for case in cases_list:
        if case_id == case['case_id']:
            return Response(json.dumps(case), mimetype='application/json')
    return Response(json.dumps({}), mimetype='application/json')


@test_auth_app_flask.route('/app/<app_label>/new_case/', methods=['POST'])
def app_page_new_case_2(app_label, param=None):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    if request.method == 'POST':
        if 'file' not in request.files:
            print('No file part')
            return redirect('/app/<app_label>/')

        files = request.files.getlist('file')

        case_id = '{}'.format(uuid1())
        init_testapp_filename_txt = '{}/{}/{}/case-{}/init_filename.txt'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id)
        init_testapp_filename_txt = os.path.abspath(init_testapp_filename_txt)
        utils.make_dir_if_not_exists(os.path.dirname(init_testapp_filename_txt))

        with open(init_testapp_filename_txt, 'w') as testapp_filename_file:
            testapp_filename_file.write("dummy.nii.gz")

        case_dirname = os.path.dirname(init_testapp_filename_txt)
        tmp_dir = '{}/raw/'.format(case_dirname)
        print('output_dirname = {}'.format(tmp_dir))
        for file in files:
            save_uploaded_file(output_dirname=tmp_dir, f_=file, same_=False)

        ret_code = app_internal_run(app_label=app_label, case_id=case_id, user_uid=current_user.user_uid)
        if ret_code:
            ret_value = {"case_id": case_id}
            print('\n\n ++++++ returning {}\n\n'.format(json.dumps(ret_value)))
            return Response(json.dumps(ret_value), mimetype='application/json')
        else:
            return Response(json.dumps({}), mimetype='application/json')

    else:
        print('request.method is not POST')
    return Response(json.dumps({}), mimetype='application/json')


def app_internal_run(app_label, case_id, user_uid=None):
    if user_uid is None:
        return False

    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return False

    init_testapp_filename_txt = '{}/{}/{}/case-{}/init_filename.txt'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id)
    init_testapp_filename_txt = os.path.abspath(init_testapp_filename_txt)

    if not os.path.exists(init_testapp_filename_txt):
        return False

    with open(init_testapp_filename_txt, 'r') as testapp_filename_file:
        testapp_basename = testapp_filename_file.read()

    # check case_id
    init_testapp_filename = '{}/{}/{}/case-{}/{}'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id, testapp_basename)
    init_testapp_filename = os.path.abspath(init_testapp_filename)

    # is_valid_case_id = os.path.exists(init_filename)
    # if not is_valid_case_id:
    #     return False

    print('app_internal_run: case_id = {}'.format(case_id))

    test_auth_app_manager.append_worker(app_label=app_label, init_filename=init_testapp_filename, user_uid=user_uid)

    print('app_internal_run: returning True')
    return True


@test_auth_app_flask.route('/app/<app_label>/<case_id>/run/', methods=['GET'])
def app_page_run(app_label, case_id):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    if current_user is None:
        return redirect('/app/{}/'.format(app_label))

    if not current_user.is_authenticated:
        return redirect('/app/{}/'.format(app_label))

    init_testapp_filename_txt = '{}/{}/{}/case-{}/init_filename.txt'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id)
    init_testapp_filename_txt = os.path.abspath(init_testapp_filename_txt)

    if not os.path.exists(init_testapp_filename_txt):
        return redirect('/app/{}/'.format(app_label))

    with open(init_testapp_filename_txt, 'r') as testapp_filename_file:
        testapp_basename = testapp_filename_file.read()

    # check case_id
    init_testapp_filename = '{}/{}/{}/case-{}/{}'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id, testapp_basename)
    init_testapp_filename = os.path.abspath(init_testapp_filename)

    is_valid_case_id = os.path.exists(init_testapp_filename)
    if not is_valid_case_id:
        return redirect('/app/{}/'.format(app_label))

    test_auth_app_manager.append_worker(app_label=app_label, init_filename=init_testapp_filename, user_uid=current_user.user_uid)

    return redirect('/app/{}/'.format(app_label))


@test_auth_app_flask.route('/app/<app_label>/<case_id>/remove/', methods=['GET'])
def app_page_remove_case(app_label, case_id):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    if current_user is None:
        return redirect('/app/{}/'.format(app_label))

    if not current_user.is_authenticated:
        return redirect('/app/{}/'.format(app_label))

    root_data_dir = test_auth_app_flask.config['DIR_DATA']
    case_dirname = '{}/{}/{}/case-{}/'.format(root_data_dir, current_user.user_uid, app_label, case_id)
    case_dirname = os.path.abspath(case_dirname)

    if os.path.exists(case_dirname):
        if os.path.isdir(case_dirname):
            shutil.rmtree(case_dirname)

    return redirect('/app/{}/'.format(app_label))


@test_auth_app_flask.route('/app/<app_label>/remove_all/', methods=['GET'])
def app_page_remove_all(app_label):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    if current_user is None:
        return redirect('/app/{}/'.format(app_label))

    if not current_user.is_authenticated:
        return redirect('/app/{}/'.format(app_label))

    root_data_dir = test_auth_app_flask.config['DIR_DATA']
    cases_dir_list = glob.glob('{}/{}/{}/case-*/'.format(root_data_dir, current_user.user_uid, app_label))

    for i in range(len(cases_dir_list)):
        cases_dir_list[i] = os.path.abspath(cases_dir_list[i])
    for cur_dir in cases_dir_list:
        shutil.rmtree(cur_dir)

    return redirect('/app/{}/'.format(app_label))


@test_auth_app_flask.route('/app/<app_label>/<case_id>/clean/', methods=['GET'])
def app_page_clean_case(app_label, case_id):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    if current_user is None:
        return redirect('/app/{}/'.format(app_label))

    if not current_user.is_authenticated:
        return redirect('/app/{}/'.format(app_label))

    root_data_dir = test_auth_app_flask.config['DIR_DATA']
    case_dirname = '{}/{}/{}/case-{}/'.format(root_data_dir, current_user.user_uid, app_label, case_id)
    case_dirname = os.path.abspath(case_dirname)

    init_testapp_filename_txt = '{}/{}/{}/case-{}/init_filename.txt'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id)
    init_testapp_filename_txt = os.path.abspath(init_testapp_filename_txt)

    if not os.path.exists(init_testapp_filename_txt):
        return redirect('/app/{}/'.format(app_label))

    with open(init_testapp_filename_txt, 'r') as testapp_filename_file:
        testapp_basename = testapp_filename_file.read()

    # check case_id
    init_testapp_filename = '{}/{}/{}/case-{}/{}'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id, testapp_basename)
    init_testapp_filename = os.path.abspath(init_testapp_filename)

    if os.path.exists(case_dirname):
        if os.path.isdir(case_dirname):
            worker = None
            if app_label == 'testapp':
                worker = TestApplicationWorker()
            worker.set_input_filename(init_testapp_filename)
            if worker is not None:
                worker.clean()
    return redirect('/app/{}/'.format(app_label))


@test_auth_app_flask.route('/app/<app_label>/clean_all/', methods=['GET'])
def app_page_clean_all(app_label):
    # check app_label
    is_valid_app_label = allowed_app_label(app_label=app_label)
    if not is_valid_app_label:
        return redirect('/')

    if current_user is None:
        return redirect('/app/{}/'.format(app_label))

    if not current_user.is_authenticated:
        return redirect('/app/{}/'.format(app_label))

    root_data_dir = test_auth_app_flask.config['DIR_DATA']

    cases_list = get_cases_list(session_id='dummy session id', app_label=app_label, user_uid=current_user.user_uid)
    for case in cases_list:
        case_id = case['case_id']

        case_dirname = '{}/{}/{}/case-{}/'.format(root_data_dir, current_user.user_uid, app_label, case_id)
        case_dirname = os.path.abspath(case_dirname)

        init_testapp_filename_txt = '{}/{}/{}/case-{}/init_filename.txt'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id)
        init_testapp_filename_txt = os.path.abspath(init_testapp_filename_txt)

        if not os.path.exists(init_testapp_filename_txt):
            return redirect('/app/{}/'.format(app_label))

        with open(init_testapp_filename_txt, 'r') as testapp_filename_file:
            testapp_basename = testapp_filename_file.read()

        # check case_id
        init_testapp_filename = '{}/{}/{}/case-{}/{}'.format(test_auth_app_flask.config['DIR_DATA'], current_user.user_uid, app_label, case_id, testapp_basename)
        init_testapp_filename = os.path.abspath(init_testapp_filename)

        if os.path.exists(case_dirname):
            if os.path.isdir(case_dirname):
                worker = None
                if app_label == 'testapp':
                    worker = TestApplicationWorker()
                worker.set_input_filename(init_testapp_filename)
                if worker is not None:
                    worker.clean()

    return redirect('/app/{}/'.format(app_label))


########################################

@test_auth_app_flask.route('/data/<dirname1>/<dirname2>/<dirname3>/<file_path>', methods=['GET'])
def display_image(dirname1, dirname2, dirname3, file_path):
    real_url = url_for('static', filename='data/{}/{}/{}/{}'.format(dirname1, dirname2, dirname3, file_path), _scheme='https', _external=True)
    return redirect(real_url, code=301)
