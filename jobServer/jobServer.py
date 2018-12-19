from flask import Flask, jsonify, request, Response
from functools import wraps
import redisUtils
import json

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

# TODO(daniel): add support for marking a job that hasn't yet run as complete

# Every queue contains a list of jobs, the data that each job holds is held in a map
# and all running jobs are put in a single list

# If a job is not found the job map then it is assumed that it has been completed.

app = Flask(__name__)
config = json.load(open('config.json'))
db = redisUtils.db

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'daniel' and password == config['redis_auth_key']

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/queue/<queue_name>/push', methods=['PUT'])
@requires_auth
def push_job(queue_name):
    job = request.get_json()

    if 'payload' not in job:
        return Response('A payload for the queue must be passed in.', status=400)

    payload = job['payload']
    priority = job['priority'] if 'priority' in job else False

    redisUtils.add_to_queue(queue_name, payload, priority)

    return Response('Added job to queue', status=200)

@app.route('/queue/<queue_name>/pop', methods=['GET'])
@requires_auth
def pop_job(queue_name):
    job = redisUtils.pop_queue(queue_name)
    if job is None:
        return Response('Queue Empty', status=404)
    return jsonify(job)

@app.route('/queue/<queue_name>/list', methods=['GET'])
def get_queue(queue_name):
    return jsonify(redisUtils.list_queue(queue_name))

@app.route('/queue/<queue_name>/len', methods=['GET'])
def get_queue_length(queue_name):
    return jsonify({'len': len(redisUtils.list_queue(queue_name))})

@app.route('/queue/<queue_name>/size', methods=['GET'])
def get_queue_size(queue_name):
    return jsonify({'size': redisUtils.queue_size(queue_name)})

@app.route('/job/<int:job_id>/ping', methods=['PUT'])
@requires_auth
def ping_job(job_id):
    if not redisUtils.ping_job(job_id):
        return Response('Requested job does not exist.', status=404)
    return Response('PONG', status=200)

@app.route('/job/<int:job_id>/requeue', methods=['PUT'])
@requires_auth
def requeue_job(job_id):
    redisUtils.readd_to_queue(job_id)
    return Response('Readded job to queue', status=200)

@app.route('/job/<int:job_id>/complete', methods=['PUT'])
@requires_auth
def complete_job(job_id):
    if not redisUtils.complete_job(job_id):
        return Response('Requested job does not exist.', status=404)
    return Response(status=200)

if __name__ == '__main__':
    app.run(debug=True)