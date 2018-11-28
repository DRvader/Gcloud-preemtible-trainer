gsutil mb gs://job-storage
gsutil redis/redis_master.py gs://job-storage/redis/
gsutil redis/redis.conf gs://job-storage/redis/
gsutil redis/config.json gs://job-storage/redis/

gcloud beta compute instances delete redis-master
gcloud beta compute instance-groups managed delete tf-trainer-preemptible --region=us-east4
gcloud compute instance-templates delete tf-trainer-preemptible

gcloud beta compute instances create redis-master --zone=us-east4-c \
--machine-type=f1-micro --metadata-from-file startup-script=redis/redis_startup.sh
--image=debian-9-stretch-v20181113 --image-project=debian-cloud --boot-disk-size=10GB

gcloud beta compute instance-templates create tf-trainer-preemptible \
--machine-type=n1-highmem-2 --no-restart-on-failure --maintenance-policy=TERMINATE --preemptible \
--accelerator=type=nvidia-tesla-p4,count=1 --image=c2-deeplearning-tf-1-12-cu100-20181120 \
--image-project=ml-images --boot-disk-size=200GB --boot-disk-type=pd-standard \
--boot-disk-device-name=tf-trainer-preemptible \
--metadata-from-file shutdown-script=worker-scripts/shutdown_worker.py,startup-script=worker-scripts/worker_startup.sh

gcloud beta compute instance-groups managed create tf-trainer-preemptible \
--base-instance-name=tf-trainer-preemptible --template=tf-trainer-preemptible --size=1 --region=us-east4 \
--health-check=preempted-check --initial-delay=300

gcloud compute --project "preemtible-training-222101" instance-groups managed set-autoscaling \
"tf-trainer-preemptible" --zone "us-east4-b" --cool-down-period "60" --max-num-replicas "1" --min-num-replicas "0" \
--update-stackdriver-metric=pubsub.googleapis.com/subscription/num_undelivered_messages\
--stackdriver-metric-single-instance-assignment=1\
--stackdriver-metric-filter='resource.label.group = tf-trainer-preemptible AND resource.type = pubsub_subscription'