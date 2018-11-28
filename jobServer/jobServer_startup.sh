#!/bin/bash
sudo apt update
sudo apt install -y python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv redis-server

mkdir ~/jobServer
cd ~/jobServer
python3 -m venv jobServerEnv
source jobServerEnv/bin/activate
pip install wheel
pip install gunicorn flask
deactivate

gsutil cp gs://job-storage/redis/redis.conf ~/jobServer/redis.conf
gsutil cp gs://job-storage/redis/redis_master.py ~/jobServer/redis_master.py
gsutil cp gs://job-storage/redis/config.json ~/jobServer/config.json
redis-server ~/jobServer/redis.conf

sudo cat > /etc/systemd/system/jobServer.service << EOL
[Unit]
Description=Gunicorn instance to serve jobs
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=~/jobServer
Environment="PATH=~/jobServerEnv/bin"
ExecStart=~/JobServerEnv/bin/gunicorn --bind unix:jobServer.sock -m 007 jobServer:app

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl start jobServer
sudo systemctl enable jobServer

cd ~
gunicorn3 redis_master:app -b 0.0.0.0:8000 --daemon

# final exams are different but representative
# micro-COS3:interrupt management (most likely have application from this section) [see final exams]
# have some threoretical questions
# know RM EDF, basic algorithm principals
# polling server
# given formulas
# getting schdualbility formulas