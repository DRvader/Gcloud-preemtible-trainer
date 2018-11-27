cd ~

curl -L  https://github.com/DRvader/Gcloud-preemtible-trainer/releases/latest | grep "tar.gz" | head -1 \
| cut -d \" -f 2 |  xargs printf "https://github.com%s" | xargs wget -O "tf-trainer-latest.tar.gz"

mkdir worker-scripts
tar -xvf tf-trainer-latest.tar.gz -C worker-scripts
cd worker-scripts
mv */* .
python worker-scripts/worker_startup.py