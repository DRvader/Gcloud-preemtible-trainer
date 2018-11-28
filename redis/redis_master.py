import flask
from flask import Flask, jsonify, request, Response
import json
import redis
import sched
import time

# The redis server sits on a webserver. It can be any connected server but it
# means that jobs can be grabbed without needing redis specific software at any point.
# and the redis server can be distributed as I want with the same back end.

# To run any api command the correct key is required (in the header of the request).
# When a new worker wants to request a new job, it calls /queue/<id>/pop this gets the next job from the
# queue and returns it. It also puts the job in the running category.

# When adding a new job, the user specified the priority, the payload and the running queue.
# The job is added to the job_map (for efficient callback) and the size of the queue and job_id are incremented.

# The workers have 10 minutes to ping the webserver or the job will be considered imcomplete and be requeued.
# The worker can also call re_add on a job to requeue it in the case of a recoverable failure.

app = Flask(__name__)
db = redis.Redis('localhost') #connect to server
config = json.load(open('config.json'))
s = sched.scheduler(time.time, time.sleep)

def refresh_config():
    global config
    config = json.load(open(config.json))

def add_job(queue_name, payload, priority, job_id=None):
    if job_id is None:
        job_id = db.get('job_id')
        db.incr('job_id')

    if not queue_name.startswith('queue:'):
        queue_name = 'queue:' + queue_name

    if priority:
        db.rpush(queue, job_id)
    else:
        db.lpush(queue, job_id)
    db.incr('size:' + queue)
    job = json.dumps({'payload':payload, 'id':job_id, 'queue': queue_name})
    db.hset('reserved:job_map', job_id, job)

def readd_job(job_id):
    job = db.hget('reserved:job_map', job_id)
    db.rem('reserved:running', job_id)
    add_job(job['queue'], job['payload'], True, job['id'])

def check_heartbeat_status():
    unresponsive_jobs = db.diff('reserved:running', 'reserved:heartbeat')
    for job_id in unresponsive_jobs:
        job = db.hget('reserved:job_map', job_id)
        db.rem('reserved:running', job_id)
        add_job(job['queue'], job['payload'], True, job['id'])
    s.enter(600, 1, check_heartbeat_status)

def authorize(request):
    header = request.header
    if 'auth_key' not in header or header['auth_key'] != config['redis_auth_key']:
        return False
    return True

# curl -X PUT -H "Content-Type:application/json" -d '{"payload":"hello","queue":"test","priority":False}' localhost:5000/proj/exp/add
@app.route('/queue/<queue_name>/push', methods=['PUT'])
def add_job_from_API(queue_name):
    if not authorize(request):
        return Response(status=403)

    job = request.json

    if 'payload' not in job:
        return Response('A payload for the queue must be passed in.', status=400)

    payload = job['payload']
    priority = if 'priority' in job: job['priority'] else: False

    add_job(queue_name, payload, priority)

    return Response('Added job to queue', status=200)

@app.route('/job/<int:job_id>/requeue', methods=['PUT'])
def requeue_job(job_id):
    if not authorize(request):
        return Response(status=403)

    readd_job(job_id)

    return Response('Readded job to queue', status=200)

@app.route('/queue/<queue_name>/pop', methods=['GET'])
def get_jobs(queue_name):
    if not authorize(request):
        return Response(status=403)
    job_id = db.brpop(queue_name)
    job = json.loads(db.get('reserved:job_map', job))

    db.sadd('reserved:running', job_id)
    return jsonify(job)

@app.route('/queue/<queue_name>/list', methods=['GET'])
def get_queue(queue_name):
    if not authorize(request):
        return Response(status=403)

    if not queue_name.startswith('queue:'):
        queue_name = 'queue:' + queue_name

    return jsonify(json.loads(db.lrange(queue_name, 0, -1)))

@app.route('/queue/<queue_name>/len', methods=['GET'])
def get_queue_length(queue_name):
    if not authorize(request):
        return Response(status=403)

    if not queue_name.startswith('queue:'):
        queue_name = 'queue:' + queue_name

    return jsonify({'len': len(db.lrange(queue_name, 0, -1))})

@app.route('/queue/<queue_name>/size', methods=['GET'])
def get_queue_size(queue_name):
    if not authorize(request):
        return Response(status=403)

    if not queue_name.startswith('queue:'):
        queue_name = 'queue:' + queue_name

    queue_size_name = 'size:' + queue_name

    return jsonify({'size': db.get(queue_size_name)})

@app.route('/job/<int:job_id>/ping', methods=['PUT'])
def ping_job(job_id):
    if not authorize(request):
        return Response(status=403)

    if db.exists('reserved:job_map', job_id) == 0:
        return Response('requested job does not exist.', status=404)

    db.sadd('reserved:heartbeat', job_id)

    return Response('PONG', status=200)

@app.route('/job/<int:job_id>/complete', methods=['PUT'])
def complete_job(job_id):
    if not authorize(request):
        return Response(status=403)

    if db.exists('reserved:job_map', job_id) == 0:
        return Response('requested job does not exist.', status=404)

    job = db.hget('reserved:job_map', job_id)
    db.hrem('reserved:job_map', job_id)
    db.srem('reserved:running', job_id)

    db.incrby('size:' + job['queue'], -1)

    return Response(status=200)

if __name__ == '__main__':
    db.set('job_id', 0)
    s.enter(600, 1, check_heartbeat_status)
    app.run(debug=True)