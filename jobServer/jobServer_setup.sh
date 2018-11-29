gsutil mb gs://job-storage
gsutil cp jobServer/jobServer.py gs://job-storage/jobServer/
gsutil cp jobServer/redis.conf gs://job-storage/jobServer/
gsutil cp jobServer/config.json gs://job-storage/jobServer/

gcloud beta compute instances delete redis-master --zone=us-east4-c

gcloud compute addresses create jobserver --region us-east4 --ip-version IPV4

gcloud beta compute instances create redis-master --zone=us-east4-c --address=jobserver --tags=https-server,http-server \
--machine-type=f1-micro --metadata-from-file startup-script=jobServer/jobServer_startup.sh \
--image=debian-9-stretch-v20181113 --image-project=debian-cloud --boot-disk-size=10GB