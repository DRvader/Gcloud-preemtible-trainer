from google.cloud import firestore
from google.cloud import storage
import json
import os
from queue import Queue, Empty
import requests
from threading  import Thread
import time
import subprocess

try:
    config = json.load(open('../config.json'))
except:
    config = json.load(open('config.json'))

try:
    redis_config = json.load(open('../jobServer/config.json'))
except:
    redis_config = json.load(open('jobServer/config.json'))

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)

def call_subprocess(args, stdout_writer, stdout_reader, stderr_writer, stderr_reader, env, shell):
    process = subprocess.Popen(args, stdout=stdout_writer, stderr=stderr_writer, env=env, shell=shell)

    if stdout_reader is None:
        stdout_reader = process.stdout
    if stderr_writer is not None and stderr_reader is None:
        stderr_reader = process.stderr

    queue = Queue()
    t = Thread(target=enqueue_output, args=(stdout_reader, queue))
    t.daemon = True # thread dies with the program
    t.start()

    t = Thread(target=enqueue_output, args=(stderr_reader, queue))
    t.daemon = True # thread dies with the program
    t.start()

    while process.poll() is None or not queue.empty():
        try:
            print(str(queue.get(timeout=0.1), 'utf-8'), end='')
        except Empty:
            pass

    return process

def subprocess_live_output(args, env=None, use_shell=False,
                           stdout_path=None, stderr_path=None, include_stderr=True):
    stdout_writer = stdout_reader = stderr_writer = stderr_reader = None
    if stdout_path is not None:
        stdout_writer = open(stdout_path, 'wb')
        stdout_reader = open(stdout_path, 'rb', 1)

        if include_stderr:
            if stdout_path is not None:
                stderr_writer = subprocess.STDOUT
                stderr_reader = subprocess.STDOUT
            else:
                stderr_writer = open(stderr_path, 'wb')
                stderr_reader = open(stderr_path, 'rb', 1)
        else:
            stderr_writer = None
            stderr_reader = None
    else:
        stdout_writer = subprocess.PIPE
        stdout_reader = None

        if include_stderr:
            stderr_writer = subprocess.PIPE
            stdout_reader = None
        else:
            stderr_writer = None
            stderr_reader = None

    try:
        process = call_subprocess(args, stdout_writer, stdout_reader, stderr_writer, stderr_reader, env, use_shell)
    finally: # make sure that files are properly closed
        if stdout_path is not None:
            if stdout_writer is not None:
                stdout_writer.close()
            if stdout_reader is not None:
                stdout_reader.close()
            if stdout_path is not None:
                if stderr_writer is not None:
                    stderr_writer.close()
                if stderr_reader is not None:
                    stderr_reader.close()

    process.poll()
    return process

def run_python_script(main_module, code_location, arguments=[], packages=[], env=None,
                      use_shell=[False, False], see_output=[False, False],
                      use_files=[False, False], concurrent_callback=[None, None]):
    package_process = None
    if len(packages) > 0:
        args = ['python', '-m', 'pip', 'install', '--upgrade',
                '--ignore-installed', '--target', '~/packages'] + pip_packages

        if use_files[0]:
            stdout = "~/package_install.stdout"
            stderr = "~/package_install.stderr"
        else:
            stdout = None
            stderr = None

        if see_output[0]:
            process = subprocess_live_output(args, env=env, use_shell=use_shell[0],
                                             include_stderr=True,
                                             stdout_path=stdout,
                                             stderr_path=stderr)
        else:
            process = subprocess.run(args, env=env, shell=use_shell[0],
                                     stdout=stdout, stderr=stderr)

        if "PYTHONPATH" in env:
            env["PYTHONPATH"] =  env["PYTHONPATH"] + ':' + '~/packages'
        else:
            env["PYTHONPATH"] = '~/packages'

        package_process = process.returncode

    if package_process is not None and package_process != 0:
        return package_process, None

    python_call = ['python', '-m', main_module]
    if len(arguments) > 0: python_call += arguments
    if "PYTHONPATH" in env:
            env["PYTHONPATH"] = code_location + ':' + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = code_location

    if use_files[1]:
        stdout = "~/python_run.stdout"
        stderr = "~/python_run.stderr"
    else:
        stdout = None
        stderr = None

    if see_output[1]:
        process = subprocess_live_output(python_call, env=env, use_shell=use_shell[1],
                                         include_stderr=True,
                                         stdout_path=stdout,
                                         stderr_path=stderr)
    else:
        process = subprocess.run(python_call, env=env, shell=use_shell[1],
                                 stdout=stdout, stderr=stderr)

    return package_process, process.returncode

def check_message(message, job_ref):
    # return job_ref.get(u'state') != u'RUNNING'
    return True

def create_job(message, job_ref):
    job_ref.update({u'state': u'RUNNING'})

    with open('~/job_id', 'w') as file:
        file.write(message['id'])

def run_job(message, job_ref):
    arguments = job_ref.get(u'arguments')
    module = job_ref.get(u'python_module')
    code_path = job_ref.get(u'cloud_storage_path')
    packages = job_ref.get(u'pip_packages')

    output_dir = '~/code/code.tar.gz'

    subprocess.run(['mkdir', '~/code', ';',
                    'gsutil', 'cp', code_path, output_dir, ';',
                    'tar', '-xf', '~/code/code.tar.gz', '-C', '~/code'],
                    shell=True)

    class ACKDEADLINE_EXTEND():
        def __init__(self, message, ack_deadline=config.ack_deadline, ack_min=config.ack_min):
            self.first_call = True
            self.message = message
            self.ack_deadline = ack_deadline
            self.ack_min = ack_min

            self.message.modify_ack_deadline(self.ack_deadline)
            self.get_time = lambda: time.time()
            self.start_time = self.get_time()

        def __call__(self):
            current_time = self.get_time()
            if current_time - self.start_time < self.ack_min:
                self.start_time = current_time
                self.message.modify_ack_deadline(self.ack_deadline)

    process = run_python_script(module, output_dir, env=os.environ.copy(),
                                arguments=arguments, packages=packages,
                                use_files=[True, True], concurrent_callback=[None, ACKDEADLINE_EXTEND(message)])
    return process[1].returncode

def teardown_job(message, job_ref):
    job_ref.update({u'state': u'COMPLETED'})
    os.remove('~/job_id')
    requests.put('{}/job/{}/completed'.format(config['job_queue_address'], message['id']),
                 headers={'auth_key': redis_config['redis_auth_key']})

def handle_message(message):
    db = firestore.Client()

    database_job_location = message.data
    job_ref = db.document(database_job_location)

    if not check_message(message, job_ref):
        return

    create_job(message, job_ref)

    run_job(message, job_ref)

    teardown_job(message, job_ref)

if __name__ == '__main__':
    client = pubsub.SubscriberClient()
    while True:
        for queue in config['worker_queues']:
            response = requests.put('{}/queue/{}/pop'.format(config['job_queue_address'], queue),
                                    headers={'auth_key': redis_config['redis_auth_key']})
            job = json.loads(response.text)
            handle_message(job['payload'])
        time.sleep(1)