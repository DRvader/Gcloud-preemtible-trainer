from google.cloud import firestore
from google.cloud import pubsub
from google.cloud import monitoring
import os
import time
import subprocess

PROJECT = 'Preemptible-training'
BUCKET = 'wc-personal-test'
PENDING_SUBSCRIPTION = 'tf-trainer-jobs'
PREEMPTED_SUBSCRIPTION = 'preempted-tf-trainer-jobs'
ACK_DEADLINE = 120
ACK_MIN = 30

db = firestore.Client()

def check_message(message, job_ref):
    return job_ref.get(u'state') != u'RUNNING':

def create_job(message, job_ref):
    job_ref.update({u'state': u'RUNNING'})

    with open('~/ack_id'), 'w') as file:
        file.write(message._ack_id)

def run_job(message, job_ref):
    arguments = job_ref.get(u'arguments')
    module = job_ref.get(u'python_module')
    if len(pip_packages) > 0:
        out_file = open("package_install.stdout", "wb", 0)
        err_file = open("package_install.stderr", "wb", 0)
        try:
            subprocess.run(['python', '-m', 'pip', 'install', '--upgrade',
                            '--ignore-installed', '--target', '~/packages'] + pip_packages,
                           shell=True, stdout=out_file, stderr=err_file check=True)
        except CalledProcessError as e:
            return e.returncode
        finally:
            out_file.close()
            err_file.close()

    out_file = open("python_run.stdout", "wb", 0)
    err_file = open("python_run.stderr", "wb", 0)
    python_call = ['PYTHONPATH=~/packages:$PYTHONPATH', 'python', '-m'] + module
    if len(arguments) > 0: python_call += arguments
    run = subprocess.Popen(python_call, stdout=out_file, stderr=err_file, shell=True)

    message.modify_ack_deadline(ACK_DEADLINE)
    counter = ACK_DEADLINE
    while run.poll() is None:
        counter -= 1
        if counter <= ACK_MIN:
            message.modify_ack_deadline(ACK_DEADLINE)
            counter = ACK_DEADLINE
        time.sleep(1)

    out_file.close()
    err_file.close()
    return run.returncode

def teardown_job(message, job_ref):
    job_ref.update({u'state': u'COMPLETED'})
    os.remove('~/ack_id')
    message.ack()

def handle_message(message):
    database_job_location = message.data
    job_ref = db.document(database_job_location)

    if not check_message(message, job_ref):
        message.ack()
        return

    create_job(message, job_ref)

    run_job(message, job_ref)

    teardown_job(message, job_ref)

if __name__ == '__main__':
    client = monitoring.Client(project=PROJECT)

    subscriber = pubsub.SubscriberClient()
    pending_subscription = client.subscription_path(PROJECT, PENDING_SUBSCRIPTION)
    while True:
        response = client.pull(pending_subscription, max_messages=1, return_immediatly=True)
        if len(response) > 0:
            for message in response.recieved_messages:
                handle_message(message)
        else:
            time.sleep(60)