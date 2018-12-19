import json
import redis
db = redis.Redis('localhost') #connect to server

def convert_bytesToString(data):
    if isinstance(data, list):
        return [convert_bytesToString(nested_data) for nested_data in data]

    if isinstance(data, set):
        return set(convert_bytesToString(nested_data) for nested_data in data)

    if isinstance(data, dict):
        return {convert_bytesToString(k):convert_bytesToString(v) for k,v in data.items()}

    if isinstance(data, tuple):
        return tuple(convert_bytesToString(nested_data) for nested_data in data)

    try:
        return data.decode()
    except AttributeError:
        return data

def refresh_config():
    global config
    config = json.load(open(config.json))

def add_to_queue(queue_name, payload, high_priority, job_id=None):
    if job_id is None:
        job_id = db.get('reserved:job_id')
        if job_id is None:
            job_id = '0'
        db.incr('reserved:job_id')

    job_id = convert_bytesToString(job_id)
    queue_name = convert_bytesToString(queue_name)

    if not queue_name.startswith('queue:'):
        queue_name = 'queue:' + queue_name

    if high_priority:
        db.rpush(queue_name, job_id)
    else:
        db.lpush(queue_name, job_id)
    db.hincrby('reserved:size', queue_name, 1)

    job = json.dumps({'payload':payload, 'id':job_id, 'queue': queue_name})
    db.hset('reserved:job_map', job_id, job)

def readd_to_queue(job_id):
    job = json.loads(convert_bytesToString(db.hget('reserved:job_map', job_id)))
    db.srem('reserved:running', job_id)
    db.hincrby('reserved:size', job['queue'], -1) # it will immediatly incremented
    add_to_queue(job['queue'], job['payload'], True, job['id'])

def pop_queue(queue_name):
    if not queue_name.startswith('queue:'):
        queue_name = 'queue:' + queue_name

    if not db.exists(queue_name):
        return None

    job_id = convert_bytesToString(db.brpop(queue_name)[1])
    job = convert_bytesToString(db.hget('reserved:job_map', job_id))

    if job is None: # if the job has already been cleared from the job_map
        return pop_queue(queue_name)
    job = json.loads(job)

    db.sadd('reserved:running', job_id)
    return job

def list_queue(queue_name):
    if not queue_name.startswith('queue:'):
        queue_name = 'queue:' + queue_name

    return convert_bytesToString(db.lrange(queue_name, 0, -1))

def queue_size(queue_name):
    """
    Returns len of queue including running jobs.
    """

    if not queue_name.startswith('queue:'):
        queue_name = 'queue:' + queue_name

    if db.hexists('reserved:size', queue_name) == 0:
        return 0

    return convert_bytesToString(db.hget('reserved:size', queue_name))

def ping_job(job_id):
    if db.hexists('reserved:job_map', job_id) == 0:
        return False

    db.sadd('reserved:heartbeat', job_id)
    return True

def complete_job(job_id):
    if db.hexists('reserved:job_map', job_id) == 0:
        return False

    job = json.loads(convert_bytesToString(db.hget('reserved:job_map', job_id)))
    db.hdel('reserved:job_map', job_id)
    db.srem('reserved:running', job_id)

    db.hincrby('reserved:size', job['queue'], -1)

    return True