gcloud compute instance-templates create tf-trainer-preemptible \
  --image-family gci-stable \
  --image-project google-containers \
  --machine-type n1-standard-1 \
  --metadata-from-file user-data=cloud-init

gcloud compute instance-groups managed create tf-trainer-preemptible \
  --base-instance-name nginx \
  --size 3 \
  --template nginx-instance-template