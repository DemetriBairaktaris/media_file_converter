import ffmpy
from threading import Thread
import sys
import os
from time import sleep
import tempfile


def remove_file(path):
    try:
        os.remove(path)
        return True
    except Exception as e:
        e = "Couldn't remove file, {}".format(str(e))
        print(e)
        return False


class CustomThread(Thread):

    def __init__(self, *args, **kwargs):
        super(CustomThread, self).__init__(*args, **kwargs)
        self.started = False
        self.std_error = None

    def start(self):
        self.started = True
        super(CustomThread, self).start()


class Job:
    def __init__(self, thread, name, src, dest):
        self.thread: CustomThread = thread
        self.id = hash(self.thread)
        self.name = name
        self.dest_path = dest
        self.src_path = src

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self)

    @property
    def success(self) -> bool:
        if self.thread.started:
            is_error = False
            if self.thread.std_error:
                self.thread.std_error.seek(0)
                is_error = bool(self.thread.std_error.read())

            return not is_error and os.path.exists(self.dest_path)
        else:
            return False

    def is_done(self):
        return not self.thread.is_alive() and self.thread.started

    def get_src_path(self):
        return self.src_path

    def get_dest_path(self):
        return self.dest_path

    def __eq__(self, other):
        return self.id == other.id


class Jobs:
    def __init__(self):
        self.jobs = []
        self.observers = []
        self.stop_poll_for_jobs = False
        self.t = CustomThread(target=self._poll_for_jobs)
        self.t.start()

    def _poll_for_jobs(self):
        while not self.stop_poll_for_jobs:
            for j in self.jobs[:]:
                if j.is_done():
                    for o in self.observers:
                        if o.notify(j):
                            self.jobs.remove(j)

            sleep(.5)

    def stop_polling_for_jobs(self, wait=False):
        self.stop_poll_for_jobs = True
        while wait and self.t.is_alive():
            sleep(.2)

    def add_job(self, thread, name, src_path, dest_path):
        j = Job(thread, name, src_path, dest_path)
        self.jobs.append(j)
        return j

    def remove_job_by_id(self, id):
        for i in self.jobs[:]:
            if i.id == id:
                self.jobs.remove(i)

    def index_of_id(self, id):
        for i, j in enumerate(self.jobs):
            if j.id == id:
                return i

    def get_job(self, id):
        for i in self.jobs:
            if i.id == id:
                return i

    def __iter__(self):
        return iter(self.jobs)

    def __getitem__(self, item):
        return self.jobs[item]


class Conversion:
    executable = 'ffmpeg'

    def run(self, runnable, *args, **kwargs):
        thread = CustomThread(target=runnable, args=args, **kwargs)
        thread.start()
        return thread

    def convert(self, input_path, conversion_extension, check_file_path=True, do_multi_thread=True):
        output_path, ext = os.path.splitext(input_path)
        output_path += ('.' if '.' not in conversion_extension else '') + conversion_extension
        if check_file_path is True and os.path.exists(output_path):
            raise FileExistsError
        elif input_path == output_path:
            raise FileExistsError
        else:
            remove_file(output_path)

        if getattr(sys, 'freeze', False):
            executable = os.path.join(sys._MEIPASS, self.executable)
        else:
            executable = self.executable

        ff = ffmpy.FFmpeg(
            executable=executable,
            inputs={input_path: None},
            outputs={output_path: None})

        if do_multi_thread:
            #TODO Refactor
            f = tempfile.NamedTemporaryFile('w+')
            f.close()

            std_error = open(f.name, 'w+')

            def run_with_exception_handling(*a, **kw):
                try:
                    ff.run(*a, **kw)
                except Exception as e:
                    std_error.write(str(e))
                    std_error.flush()

            thread = self.run(run_with_exception_handling, None, None, std_error)
            thread.std_error = std_error
            return thread
        else:
            ff.run()
        pass

    @staticmethod
    def get_supported_types():
        return sorted([
            'AIFF',
            'ASF',
            'AVI',
            'BFI',
            'CAF',
            'FLV',
            'GIF',
            'MP4',
            'MP3',
            'WAV',
            'MOV',
            'MPG4',
        ])
