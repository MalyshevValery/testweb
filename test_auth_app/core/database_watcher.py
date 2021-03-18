import os
import glob
import numpy as np
import nibabel as nib


class CaseInfo:
    GOOD_MODALITIES = {'CT': 36, 'CXR': 1}

    case_type = 'CT'
    case_data_dirname = None
    case_id = None
    series_length = 0
    image_shape = None

    def is_initialized(self):
        return (self.case_data_dirname is not None) and (self.series_length > self.GOOD_MODALITIES[self.case_type])

    def data_dirname(self):
        if self.case_data_dirname is not None:
            return os.path.dirname(self.case_data_dirname)
        else:
            return None

    def case_id(self):
        if self.case_id is not None:
            return self.case_id
        else:
            return None

    def is_empty(self):
        if self.series_length > 0:
            return True
        else:
            return False

    def as_string(self):
        tmp = 'CaseInfo: case_id={0}, #image shape={1}'.format(self.case_id(), self.image_shape)
        return tmp

    def __str__(self):
        return self.as_string()

    def __repr__(self):
        return self.as_string()

    def __init__(self, case_dirname_=None):
        if case_dirname_ is not None:
            self.load_info(case_dirname_=case_dirname_)

    def clear(self):
        self.case_data_dirname = None
        self.case_id = None
        self.series_length = 0
        self.image_shape = None

    def load_info(self, case_dirname_, drop_bad=False):
        if not os.path.exists(case_dirname_):
            return
        if 'case-' not in case_dirname_:
            return
        self.case_data_dirname = case_dirname_
        case_dirname_tokens_list = self.case_data_dirname.split('/')
        for tok in case_dirname_tokens_list:
            if 'case-' in tok:
                self.case_id = tok.replace('case-', '')
                break
        image_filename = '{}/{}.nii.gz'.format(self.case_data_dirname, self.case_id)
        if not os.path.exists(image_filename):
            self.clear()
            return
        img_vol = nib.load(image_filename).get_data()
        self.image_shape = img_vol.shape
        if len(self.image_shape) != 3:
            self.clear()
            return
        self.series_length = self.image_shape[2]
        if self.series_length < self.GOOD_MODALITIES[self.case_type]:
            self.clear()
            return


class DatabaseWatcher:
    working_dirname = None
    cases = None
    user_id = None
    app_name = None

    def __init__(self, working_dirname_=None, user_id_=None, app_name_=None):
        self.cases = dict()
        if user_id_ is not None:
            self.user_id = user_id_
        if app_name_ is not None:
            self.app_name = app_name_
        if working_dirname_ is not None:
            self.load(working_dirname_)

    def load(self, working_dirname_, drop_empty=False, drop_bad_series=False):
        if not os.path.isdir(working_dirname_):
            return
        self.working_dirname = working_dirname_
        cases_list = glob.glob('%s/case-*' % self.working_dirname)
        number_of_cases = len(cases_list)
        cases_dict = dict()
        for ii, case_dirname in enumerate(cases_list):
            case_info = CaseInfo()
            case_info.load_info(case_dirname_=case_dirname, drop_bad=drop_bad_series)
            if ii % 20 == 0:
                print('[%d/%d] --> case #%s' % (ii, number_of_cases, case_info.case_id()))
            if drop_empty and case_info.is_empty():
                continue
            else:
                tkey = case_info.case_id()
                cases_dict[tkey] = case_info
        self.cases = cases_dict

    def reload(self):
        if self.working_dirname is not None:
            self.load(self.working_dirname)

    def has_case(self, case_id_):
        if self.cases is None:
            return False
        else:
            if case_id_ in self.cases.keys():
                return True
            else:
                return False

    def all_series(self):
        for case_key, case in self.cases.items():
            if not case.is_empty():
                for _, ser in case.series.items():
                    yield ser

    def check_series_in_database(self, series_):
        for series in self.all_series():
            if series.get_case_id() == series_.get_case_id():
                return True
        return False

    def as_string(self):
        if self.cases is None:
            return 'DatabaseWatcher is not initialized'
        else:
            tret = self.get_statistics()
            return 'Cases: #All/#Good = {0}/{1}' \
                .format(tret['cases']['total'],
                        tret['cases']['empty'])

    def __str__(self):
        return self.as_string()

    def __repr__(self):
        return self.as_string()

    def get_statistics(self):
        ret = {
            'cases': {
                'total': 0,
                'empty': 0
            }
        }
        if self.cases is not None:
            ret['cases']['total'] = len(self.cases)
            for ic, (case_key, case) in enumerate(self.cases.items()):
                if case.is_empty():
                    ret['cases']['empty'] += 1

        return ret

    def print_statistics(self):
        print(self.as_string())
