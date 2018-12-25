from redisUtils import db, readd_to_queue, convert_bytesToString

def check_heartbeat_status():
    unresponsive_jobs = db.sdiff('reserved:running', 'reserved:heartbeat')
    print("{} unresponsive jobs".format(len(unresponsive_jobs)))
    for job_id in convert_bytesToString(unresponsive_jobs):
        readd_to_queue(job_id)
        print("re-added {}".format(job_id))

if __name__ == '__main__':
    check_heartbeat_status()