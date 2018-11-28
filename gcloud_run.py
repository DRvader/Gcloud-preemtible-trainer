import argparse
from google.cloud import firestore
from google.cloud import storage
from google.cloud import pubsub_v1
import json
import os
import requests
from shutil import make_archive
import tempfile
from worker import run_python_script
import zipfile

config = json.load(open('config.json'))
redis_config = json.load(open('redis/config.json'))

def upload_blob(bucket, source_file, destination_blob_name, from_file=True):
    """Uploads a file to the bucket."""
    blob = bucket.blob(destination_blob_name)

    if from_file:
        blob.upload_from_file(source_file)
    else:
        blob.upload_from_filename(source_file)

    print('File {} uploaded to {}.'.format(source_file, destination_blob_name))

def get_blobs_with_prefix(bucket, prefix, delimiter=None):
    """
    Specify delimeter='/' to get only the level of files with the prefix and not the entire tree.
    """
    blobs = bucket.list_blobs(prefix=prefix, delimiter=delimiter)

    prefixes = []
    if delimiter:
        prefixes.extend(blobs.prefixes)

    return blobs, prefixes

def get_blobs(bucket):
    return bucket.list_blobs()

# db schema
# project name [c]
#   - experiment [d]
#       - version [c]
#           - next version [d]
#              > next_version : int
#       - statuses [c]
#           - 0 [d]
#               > state : string
#               > model_dir : reference
#       - stats [c]
#           - 0 [d]
#               > loss : list
#               > accuracy : list
#               > weight vecociy : list

def set_version_number(db_client, project_name, experiment_name, version_number):
    db.collection(project_name).document(experiment_name).collection(u'info').document(u'next_version').set({u'next_version_number': version_number})

def get_version_number(db_client, project_name, experiment_name):
    return db.collection(project_name).document(experiment_name).collection(u'info').document(u'next_version').get().to_dict()

def update_version_number(db_client, project_name, experiment_name, version_number):
    db.collection(project_name).document(experiment_name).collection(u'info').document(u'next_version').update({u'next_version_number': version_number})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the specified code on google cloud or locally.')
    parser.add_argument('path', action='store',
                        help='The path to the folder containing the code to run.')
    parser.add_argument('main_module', action='store',
                        help='The path to the module to run starting from the top level folder.')
    parser.add_argument('project_name', action='store',
                        help='Sets the project name.')
    parser.add_argument('experiment_name',
                        help='Sets the experiment name.')
    parser.add_argument('--local', dest='local', action='store_true', default=False,
                        help='Performs a test run locally.')
    parser.add_argument('--real', dest='real', action='store_true', default=False,
                        help='Send run stats to database while running locally.')
    parser.add_argument('-p','--packages', nargs='*', default=[],
                        help='Specify the pip packages to install on the worker before the job is run.')
    results, unknown_results = parser.parse_known_args()

    zip_path = os.path.join(tempfile.mktemp(), 'code')
    make_archive(zip_path, 'gztar', results.path)

    send_data = results.real
    version_number = None

    print("Uploading File")
    if results.local:
        from shutil import copyfile
        uploaded_dir = os.path.join(tempfile.mkdtemp(), 'code')
        copyfile(zip_path + '.tar.gz', uploaded_dir)
    else:
        storage_client = storage.Client()
        db = firestore.Client()
        version_number = get_version_number(db, results.project_name, results.experiment_name)
        if version_number is None:
            set_version_number(db, results.project_name, results.experiment_name, 1)
            version_number = str(0)
        else:
            version_number = str(version_number['next_version_number'])

        bucket_name = results.project_name
        bucket = storage_client.get_bucket(config['bucket_name'])
        cloud_storage_path = os.path.join(results.project_name, results.experiment_name, version_number, 'code.tar.gz')
        upload_blob(bucket, zip_path + '.tar.gz', cloud_storage_path, from_file=False)
        send_data = True

    if send_data:
        print("Making Entry in Database")
        if version_number is None:
            db = firestore.Client()
            version_number = get_version_number(db, results.project_name, results.experiment_name)

            if version_number is None:
                set_version_number(db, results.project_name, results.experiment_name, 0)
                version_number = str(0)
            else:
                version_number = str(version_number[u'next_version_number'])

        update_version_number(db, results.project_name, results.experiment_name, int(version_number)+1)

        status_update = {u'state': u'PENDING',
                         u'current_epoch': 0,
                         u'current_step': 0,
                         u'cloud_storage_path': None,
                         u'python_module': results.main_module,
                         u'arguments': unknown_results,
                         u'pip_packages': results.packages}

        if not results.local:
            status_update[u'cloud_storage_path'] = os.path.join(u'gs://{}'.format(bucket_name), cloud_storage_path)

        status_ref = db.collection(results.project_name).document(results.experiment_name) \
                       .collection(u'statuses').document(version_number)
        status_ref.set(status_update)

    if results.local:
        import subprocess
        print("Running Locally")

        output_dir = os.path.join(tempfile.mktemp(), 'code')
        subprocess.run(['mkdir', '-p', output_dir], check=True)
        subprocess.run(['tar', '-xf', uploaded_dir, '-C', output_dir], check=True)

        python_call = ['python', '-m', results.main_module]
        if len(unknown_results) > 0: python_call += unknown_results
        process = run_python_script(results.main_module, output_dir, arguments=unknown_results,
                                    env=os.environ.copy(), see_output=[True, True])
        print(process[1])
    else:
        print("Submitted to Queue")
        r = requests.put('{}/queue/tf-trainer-preemptible/push'.format(config['job_queue_address'],
                         data={'payload':'/'.join([results.project_name, results.experiment_name, version_number])},
                         headers={'auth_key': redis_config['redis_auth_key']})