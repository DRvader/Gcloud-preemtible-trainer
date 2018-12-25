from google.cloud import monitoring_v3
import redisUtils
import json
import redis
import time

config = json.load(open('config.json'))
db = redisUtils.db

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
    point.value.int64_value = value
    now = time.time()
    point.interval.end_time.seconds = int(now)
    point.interval.end_time.nanos = int((now - point.interval.end_time.seconds) * 10**9)

    return series_point

if __name__ == '__main__':
    points = []
    size = redisUtils.convert_bytesToString(db.hgetall('reserved:size'))
    for k,v in size.items():
        points.append(create_point('queue/{}'.format(k.split(':')[-1]), int(v)))

    if len(points) > 0:
        print("pushed {} points".format(len(points)))
        client.create_time_series(project_name, points)