apt update && apt install redis-server python3-redis python3-flask
gsutil cp gs://job-storage/redis/redis.conf ~/redis.conf
gsutil cp gs://job-storage/redis/redis_master.py ~/redis_master.py
gsutil cp gs://job-storage/redis/config.json ~/config.json
redis-server ~/redis.conf
python3 ~/redis-master.py