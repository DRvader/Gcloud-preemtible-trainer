from jobServer_redisUtils import db, readd_to_queue
import json
import time
import sys

def check_heartbeat_status():
    unresponsive_jobs = db.sdiff('reserved:running', 'reserved:heartbeat')
    print("{} unresponsive jobs".format(len(unresponsive_jobs)))
    for job_id in unresponsive_jobs:
        readd_to_queue(job_id)
        print("re-added {}".format(job_id))

def infinte_job():
    config = json.load(open('config.json'))

    while True:
        time.sleep(config['job_timeout'])
        check_heartbeat_status()

if __name__ == '__main__':
    try:
        infinte_job()
    except KeyboardInterrupt:
        print('\nExiting by user request.\n', file=sys.stderr)
        sys.exit(0)