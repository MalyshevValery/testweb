import nibabel as nib
import numpy as np
import os
import distutils
import distutils.spawn
import glob
import tempfile
import shutil
from copy import deepcopy
import scipy.linalg as la
import subprocess
import threading


def check_file_or_dir(node_path, is_dir=False, do_raise_exception=True):
    if not is_dir:
        ret = os.path.isfile(node_path)
        if do_raise_exception and (not ret):
            raise Exception('Can not find file {}'.format(node_path))
    else:
        ret = os.path.isdir(node_path)
        if do_raise_exception and (not ret):
            raise Exception('Can not find directory {}'.format(node_path))
    return ret


def check_exe_by_path(path_to_exe, do_raise_exception=True):
    temp_ret = distutils.spawn.find_executable(path_to_exe)
    if do_raise_exception and (temp_ret is None):
        raise Exception('Can not find program {} in PATH variable'.format(path_to_exe))
    return temp_ret is not None


def check_dir_contains_dicom(dicom_dirname, do_raise_exception=True):
    tmp_list = [os.path.splitext(os.path.join(dicom_dirname, xx))[1].lower()[:4] for xx in os.listdir(dicom_dirname) if os.path.isfile(os.path.join(dicom_dirname, xx))]
    dcm_list = np.unique(tmp_list)
    ret = '.dcm' in dcm_list
    if (not ret) and do_raise_exception:
        raise Exception('Cant find DICOM files in directory {}'.format(dicom_dirname))
    return ret


class CommandRunner(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None
        self.std_out = None
        self.std_err = None
        self.ret_code = -1
        self.is_finished = False

    def run(self, timeout=60):
        def target():
            self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            self.std_out, self.std_err = self.process.communicate()
            self.ret_code = self.process.returncode
            self.is_finished = True

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()
            self.is_finished = True

    def check_is_ok(self, do_raise_exception=True):
        ret = (self.ret_code == 0) and self.is_finished
        if (not ret) and do_raise_exception:
            raise Exception('Error while run {}, stdout={}, stderr={}'.format(self.cmd, self.std_out, self.std_err))
        if (not ret) and not do_raise_exception:
            print('Error while run {}, stdout={}, stderr={}'.format(self.cmd, self.std_out, self.std_err))
        return ret


def dcmdjpeg_dir(dir_name_):
    for subdir, dirs, files in os.walk(dir_name_):
        for file in files:
            filename_ = os.path.join(subdir, file)
            command_to_run_ = 'dcmdjpeg {} {}'.format(filename_, filename_)
            cmd_runner_ = CommandRunner(command_to_run_)
            cmd_runner_.run()
            cmd_runner_.check_is_ok(do_raise_exception=False)
            # print os.path.join(subdir, file)


def pydcm2nii(dicom_dirname, out_nii_filename, path_to_exe='dcm2niix'):
    if os.path.exists(out_nii_filename):
        os.remove(out_nii_filename)

    # (1) check input params
    dicom_dirname = os.path.abspath(dicom_dirname)
    check_file_or_dir(dicom_dirname, is_dir=True)
    check_exe_by_path(path_to_exe)
    # (2) check if dir contains DICOMs
    try:
        check_dir_contains_dicom(dicom_dirname)
    except:
        return False
    # (3) convert *.dcm --> *.nii.gz
    tmp_dir = tempfile.mkdtemp(prefix='pydcm2nii-')
    dir_link_inp = dicom_dirname
    dir_link_out = os.path.join(tmp_dir, os.path.basename(dicom_dirname))
    os.symlink(dir_link_inp, dir_link_out)
    run_cmd = "{0} -m y -z y -o {1} {2}".format(path_to_exe, tmp_dir, dir_link_out)
    run_cmd_1 = CommandRunner(run_cmd)
    run_cmd_1.run()
    if not run_cmd_1.check_is_ok(do_raise_exception=False):
        dcmdjpeg_dir(dir_link_out)
        run_cmd_1.run()
    #
    nii_filename_list = sorted(glob.glob('%s/*.nii.gz' % tmp_dir))

    if len(nii_filename_list) < 1:
        shutil.rmtree(tmp_dir)
        # raise Exception('Cant find Nifti images in dcm2nii output directory [%s]' % tmp_dir)
        print('Cant find Nifti images in dcm2niix output directory [%s]' % tmp_dir)
        return False

    if nib.load(nii_filename_list[0]).affine[2, 2] > 5:
        for lfilename in nii_filename_list:
            os.remove(lfilename)
        run_cmd = "{0} -z y -o {1} {2}".format(path_to_exe, tmp_dir, dir_link_out)
        run_cmd_1 = CommandRunner(run_cmd)
        run_cmd_1.run()
        if not run_cmd_1.check_is_ok(do_raise_exception=False):
            dcmdjpeg_dir(dir_link_out)
            run_cmd_1.run()
        nii_filename_list = sorted(glob.glob('%s/*.nii.gz' % tmp_dir))

    for nii_filename in nii_filename_list:
        if len(nib.load(nii_filename).shape) > 3:
            nii_filename_list.remove(nii_filename)

    if len(nii_filename_list) < 1:
        shutil.rmtree(tmp_dir)
        print('Cant find Nifti images in dcm2niix output directory {}'.format(tmp_dir))
        return False
    input_nii_filename = nii_filename_list[0]

    if len(nii_filename_list) == 2:
        inp_name_1 = nii_filename_list[0]
        inp_name_2 = nii_filename_list[1]
        inp_img_1 = nib.load(inp_name_1)
        inp_affine_1 = inp_img_1.affine
        inp_img_2 = nib.load(inp_name_2)
        inp_affine_2 = inp_img_2.affine
        if len(inp_img_1.shape) == len(inp_img_2.shape):
            if np.equal(inp_img_1.shape, inp_img_2.shape).all():
                if 0 < inp_affine_2[2, 2] < inp_affine_1[2, 2] and inp_affine_1[2, 2] > 0:
                    input_nii_filename = nii_filename_list[1]

    if input_nii_filename is None:
        shutil.rmtree(tmp_dir)
        print('Cant find adequate image during conversion with dcm2niix in output directory {}'.format(tmp_dir))
        return False

    shutil.move(input_nii_filename, out_nii_filename)

    if os.path.exists(out_nii_filename):
        # important : conversion from RGB to int16 - seen in India data
        rgb_dtype = np.dtype([('R', 'u1'), ('G', 'u1'), ('B', 'u1')])
        img_ = nib.load(out_nii_filename)
        img_data_ = img_.get_fdata()
        if img_.get_data_dtype() == rgb_dtype:
            img_data_ = img_data_.copy().view(dtype=np.dtype(np.uint8))
            img_data_ = deepcopy(img_data_[:, :, 0])

        img_data_ = img_data_.astype(np.int16)
        img_affine_ = img_.affine

        img_affine_[np.fabs(img_affine_[:]) > 10.0] = 0
        img_affine_[np.fabs(img_affine_[:]) < np.finfo(np.float32).eps] = 0
        # important : rotation of affine matrix of CT image
        img_affine_3x3 = img_affine_[:3, :3]
        # --- these three lines drunk a cup of my blood ---
        tmp_affine_indices = np.argmax(np.absolute(img_affine_3x3), axis=1)
        x_idx = tmp_affine_indices[0]
        img_affine_3x3[:, x_idx] = -img_affine_3x3[:, x_idx]
        # -------------------------------------------------
        affine_diagonal = np.diagonal(img_affine_3x3)

        if np.count_nonzero(img_affine_3x3 - np.diag(affine_diagonal)):
            print('Affine matrix is not diagonal. Trying to arrange everything properly')
            print('img_affine_:\n{}\n'.format(img_affine_3x3))
            # print('affine_diagonal:\n{}\n'.format(affine_diagonal))
            # print('np.diag(affine_diagonal):\n{}\n'.format(np.diag(affine_diagonal)))

            affine_indices = np.argmax(np.absolute(img_affine_3x3), axis=1)
            print('affine_indices = {}'.format(affine_indices))
            img_affine_3x3_mod = img_affine_3x3[:, affine_indices]
            print('img_affine_3x3_mod:\n{}\n'.format(img_affine_3x3_mod))

            real_affine_ = np.zeros(img_affine_.shape, np.float32)
            for i in range(3):
                real_affine_[i, i] = img_affine_3x3_mod[i, i]
            real_affine_[3, 3] = 1.0
            img_affine_ = deepcopy(real_affine_)
            img_data_ = np.transpose(img_data_, axes=affine_indices)

        print('intermediate real_affine_:\n{}'.format(img_affine_))

        for i in range(4):
            if img_affine_[i][i] < 0:
                img_affine_[i][i] = -img_affine_[i][i]
                img_data_ = np.flip(img_data_, axis=i).astype(np.int16)
        img_nif = nib.Nifti1Image(img_data_, img_affine_)
        nib.save(img=img_nif, filename=out_nii_filename)
        print('result real_affine_:\n{}'.format(img_affine_))
    #
    shutil.rmtree(tmp_dir)
    return os.path.isfile(out_nii_filename)


if __name__ == '__main__':
    # dcm_dirname_1 = '../frontend/data/data_for_test_4/series-1.3.46.670589.33.1.35361704032918934337.30434182963102618809-CT/raw/'
    # dcm_dirname_2 = '../frontend/data/data_for_test_4/series-1.3.46.670589.33.1.9274211373084014663.28760091352254309508-CT/raw/'
    # dcm_dirname_3 = '../frontend/data/data_for_test_4/series-1.3.46.670589.50.2.4098226830352868681.23259815842647874772-CT/raw/'
    root_data_dir = '../frontend/data/data_for_test_4/'

    tmp_dir_list = glob.glob('{}/*-CT/raw/'.format(root_data_dir))
    cases_dir_list = {}
    for cases_dir in tmp_dir_list:
        cases_dir = os.path.abspath(cases_dir)
        series_uid = cases_dir.split('/')[-2]
        series_uid = ''.join(series_uid.split('-')[1])
        cases_dir_list[series_uid] = cases_dir
        # print(series_uid)
    # print(cases_dir_list)

    idx = 0
    for series_uid in cases_dir_list:
        idx += 1
        # if idx != 2:
        #     continue
        dcm_dirname_actual = cases_dir_list[series_uid]
        out_filename = '{}/{}.nii.gz'.format(root_data_dir, series_uid)
        out_filename = os.path.abspath(out_filename)
        print('dcm_dirname_actual = {}'.format(dcm_dirname_actual))
        print('out_filename = {}\n'.format(out_filename))

        pydcm2nii(dicom_dirname=dcm_dirname_actual, out_nii_filename=out_filename, path_to_exe='dcm2niix')
    pass
