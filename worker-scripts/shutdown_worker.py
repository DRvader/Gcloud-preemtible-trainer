from google.cloud import firestore
from google.cloud import pubsub_v1
import os
import requests

def main():
    if os.isfile(os.path.join('~/ack_id')):
        with open('~/ack_id') as file:
            ack_id = file.readline().strip()
            project = file.readline().strip()
            subscription = file.readline().strip()

        r = request.post('https://pubsub.googleapis.com/v1/projects/{0}/subscriptions/{1}:acknowledge',
                         data={"ackIds": [ack_id]})

if __name__ == '__main__':
    main()