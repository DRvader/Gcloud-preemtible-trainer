#!/bin/bash
sudo apt update
sudo apt install -y python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv redis-server
sudo add-apt-repository ppa:certbot/certbot
sudo apt -y install python-certbot-nginx

mkdir -p /home/redis
mkdir /home/redis/jobServer
cd /home/redis/jobServer
python3 -m venv jobServerEnv
source jobServerEnv/bin/activate
pip install wheel
pip install gunicorn flask redis
deactivate

gsutil cp gs://job-storage/jobServer/redis.conf /home/redis/jobServer/redis.conf
gsutil cp gs://job-storage/jobServer/jobServer.py /home/redis/jobServer/jobServer.py
gsutil cp gs://job-storage/jobServer/config.json /home/redis/jobServer/config.json
redis-server /home/redis/jobServer/redis.conf

sudo cat > /etc/systemd/system/jobServer.service << EOL
[Unit]
Description=Gunicorn instance to serve jobs
After=network.target

[Service]
User=redis
Group=www-data
WorkingDirectory=/home/redis/jobServer/
Environment="PATH=/home/redis/jobServer/jobServerEnv/bin"
ExecStart=/home/redis/jobServer/jobServerEnv/bin/gunicorn --bind unix:/tmp/jobServer.sock jobServer:app

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl start jobServer
sudo systemctl enable jobServer

sudo cat > /etc/nginx/sites-available/jobServer << EOL
server {
    listen 80;
    server_name jobserver.drosen.me;

    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/jobServer.sock;
    }
}
EOL

sudo ln -s /etc/nginx/sites-available/jobServer /etc/nginx/sites-enabled
sudo systemctl restart nginx

wget https://dl.eff.org/certbot-auto -P /home/redis/
chmod a+x /home/redis/certbot-auto

sudo /home/redis/certbot-auto --nginx -d jobserver.drosen.me --non-interactive --agree-tos --redirect --email "letsencrypt@ddwr.ca"

sudo cat > /etc/systemd/system/certRenew.timer << EOL
[Unit]
Description=Timer to renew let's encypt certs

[Timer]
OnBootSec=300
OnUnitActiveSec=1w
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
EOL

sudo cat > /etc/systemd/system/certRenew.service << EOL
[Unit]
Description=Renew let's encypt certs

[Service]
ExecStart=/home/redis/certbot-auto renew --post-hook "systemctl restart nginx"
EOL

sudo systemctl start certRenew.timer
sudo systemctl enable certRenew.timer