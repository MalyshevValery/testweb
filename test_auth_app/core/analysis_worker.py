from test_auth_app.core.worker import Worker


class AnalysisWorker(Worker):
    def __init__(self):
        super().__init__()
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
        self.worker_name = 'image analysis worker'
        self.suffix = 'analysis-worker'
        self.is_finished = False
        self.is_success = False

    def check_self(self) -> bool:
        pass

    def prepare_inputs(self) -> bool:
        pass

    def check_inputs(self) -> bool:
        pass

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
