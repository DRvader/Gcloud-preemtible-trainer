gsutil mb gs://job-storage
gsutil cp jobServer/* gs://job-storage/jobServer/

gcloud beta compute instances delete redis-master --zone=us-east4-c

gcloud compute addresses create jobserver --region us-east4 --ip-version IPV4

gcloud compute instances create redis-master --zone=us-east4-c --address=jobserver --tags=https-server,http-server \
--machine-type=f1-micro --metadata-from-file startup-script=jobServer/startup.sh \
--image-family=debian-9 --image-project=debian-cloud --boot-disk-size=10GB