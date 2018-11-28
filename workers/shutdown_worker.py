#!/usr/bin/python

from google.cloud import firestore
import json
import os
import requests

def main():
    if os.isfile(os.path.join('~/job_id')):
        config = json.load(open('../config.json'))
        redis_config = json.load(open('../redis/config.json'))

        with open('~/job_id') as file:
            job_id = file.readline().strip()

        r = request.put('{}/job/{}/requeue'.format(config['job_queue_address'], job_id),
                        headers={'auth_key': redis_config['redis_auth_key']})

        db = firestore.Client()
        job_ref = db.document(document_path)
        job_ref.update({u'state': u'PREEMPTED'})

if __name__ == '__main__':
    main()