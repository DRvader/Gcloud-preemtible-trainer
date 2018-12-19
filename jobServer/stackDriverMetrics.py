from google.cloud import monitoring_v3
import jobServer_redisUtils as redisUtils
import json
import redis
import time

config = json.load(open('config.json'))

client = monitoring_v3.MetricServiceClient()
project_name = client.project_path(config['monitoring_project_id'])

# METADATA_URL = 'http://metadata.google.internal/computeMetadata/v1/instance/'
# METADATA_HEADERS = {'Metadata-Flavor': 'Google'}

# def get_instance_metadata(metadata_path):
#     url = METADATA_URL + metadata_path
#     r = requests.get(url, headers=METADATA_HEADERS)

#     return r.text

# instance_id = get_instance_metadata('id')
# instance_zone = get_instance_metadata('zone').split('/')[-1]

def create_point(path, value):
    series_point = monitoring_v3.types.TimeSeries()
    series_point.metric.type = 'custom.googleapis.com/{}'.format(path.lstrip('/'))
    series_point.resource.type = 'global'
    # series_point.resource.labels['instance_id'] = instance_id
    # series_point.resource.labels['zone'] = instance_zone
    point = series_point.points.add()
    point.value.value = value
    now = time.time()
    point.interval.end_time.seconds = int(now)
    point.interval.end_time.nanos = int((now - point.interval.end_time.seconds) * 10**9)

points = []
size = db.hgetall('reserved:size')
if len(size) > 1:
    for k,v in zip(size[::2], size[1::2]):
        points.append(create_point('queue/{}'.format(k), v))

if len(points) > 0:
    client.create_time_series(project_name, points)