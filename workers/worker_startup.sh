#!/usr/bin/bash

cd ~

curl -sSO https://dl.google.com/cloudagents/install-monitoring-agent.sh
bash install-monitoring-agent.sh

curl -sSO https://dl.google.com/cloudagents/install-logging-agent.sh
bash install-logging-agent.sh

curl -L  https://github.com/DRvader/Gcloud-preemtible-trainer/releases/latest | grep "tar.gz" | head -1 \
| cut -d \" -f 2 |  xargs printf "https://github.com%s" | xargs wget -O "tf-trainer-latest.tar.gz"

wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh ~/miniconda.sh
bash ~/miniconda.sh -b -p $HOME/miniconda
export PATH="$HOME/miniconda/bin:$PATH"

conda create env -f worker_env.yaml
conda activate worker

mkdir worker-scripts
tar -xvf tf-trainer-latest.tar.gz -C worker-scripts
cd worker-scripts
mv */* .
python worker-scripts/workers/worker.py