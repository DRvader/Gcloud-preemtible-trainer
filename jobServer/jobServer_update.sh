gsutil mb gs://job-storage
gsutil cp jobServer/jobServer.py gs://job-storage/jobServer/
gsutil cp jobServer/jobServer_deploy.py gs://job-storage/jobServer/
gsutil cp jobServer/jobServer_redisUtils.py gs://job-storage/jobServer/
gsutil cp jobServer/jobServer_checkHeartbeat.py gs://job-storage/jobServer/
gsutil cp jobServer/redis.conf gs://job-storage/jobServer/
gsutil cp jobServer/config.json gs://job-storage/jobServer/

gcloud compute ssh --zone ZONE INSTANCE --command 'gsutil cp gs://job-storage/jobServer/* /home/redis/jobServer/ && sudo systemctl restart jobServer && sudo systemctl restart jobServerHeartbeat'