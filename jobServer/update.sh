gsutil cp jobServer/* gs://job-storage/jobServer/

gcloud compute ssh redis@redis-master --command 'sudo gsutil cp gs://job-storage/jobServer/* /home/redis/jobServer/ && sudo systemctl restart jobServer && sudo systemctl restart jobServerHeartbeat'