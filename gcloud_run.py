import argparse
from google.cloud import firestore
from google.cloud import storage
from google.cloud import pubsub_v1
import json
import os
import subprocess
import zipfile

config = json.load(open('config.json'))

def zipdir(path, zip_handle):
    for root, dirs, files in os.walk(path):
        for file in files:
            zip_handle.write(os.path.join(root, file))

def upload_blob(bucket, source_file, destination_blob_name, from_file=True):
    """Uploads a file to the bucket."""
    blob = bucket.blob(destination_blob_name)

    if from_file:
        blob.upload_from_file(source_file)
    else:
        blob.upload_from_filename(source_file)

    print('File {} uploaded to {}.'.format(source_file_name, destination_blob_name))

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

def get_version_number(db_client):
    return db.collection(results.project_name).document(results.experiment_name).get(u'next_version_number')

def set_version_number(db_client, version_number):
    db.collection(results.project_name).document(results.experiment_name).update({u'next_version_number': version_number})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the specified code on google cloud or locally.')
    parser.add_argument('path', action='store',
                        help='The path to the folder containing the code to run.')
    parser.add_argument('main_module', action='store',
                        help='The path to the folder containing the code to run.')
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

    zip_path = tempfile.mkdtemp()
    zip_file = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
    zipdir(results.path, zip_file)
    zip_file.close()

    send_data = results.real
    version_number = None

    if results.local:
        uploaded_dir = tempfile.mkdtemp()
    else:
        storage_client = storage.Client()
        db = firestore.Client()
        version_number = get_version_number(db)

        bucket_name = results.project_name
        bucket = storage_client.get_bucket(bucket_name)
        cloud_storage_path = os.path.join(results.experiment_name, version_number, 'code.zip')
        upload_blob(bucket, cloud_storage_path, zip_file)
        send_data = True

    if send_data:
        if version_number is None:
            db = firestore.Client()
            version_number = get_version_number(db)

        set_version_number(db, version_number+1)

        status_update = {u'state': u'PENDING',
                         u'current_epoch': 0,
                         u'current_step': 0,
                         u'cloud_storage_path': None,
                         u'python_module': results.main_module,
                         u'arguments': unknown_results}

        if not results.local:
            status_update[u'cloud_storage_path'] = os.path.join(u'gs://{}'.format(bucket_name), cloud_storage_path)

        status_ref = db.collection(results.project_name).collection(results.experiment_name) \
                       .collection(version_number).document(u'status')
        status_ref.set(status_update)

    if not results.local:
        publisher = pubsub_v1.PublisherClient()
        topic_name = 'projects/{project_id}/topics/{topic}'.format(project_id=config['project_id'],
                                                                   topic=config['topic_name'])
        publisher.create_topic(topic_name)
        publisher.publish(topic_name,
                          '/'.join([results.project_name, results.experiment_name, version_number]).encode())
    else:
        pass