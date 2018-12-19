#!/bin/bash
apt update
apt install -y python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv redis-server
add-apt-repository ppa:certbot/certbot
apt -y install python-certbot-nginx

mkdir -p /home/redis/jobServer
mkdir -p /home/redis/logs
cd /home/redis/jobServer
python3 -m venv jobServerEnv
source jobServerEnv/bin/activate
pip install wheel
pip install gunicorn flask redis
deactivate

chown redis -R /home/redis/

gsutil cp gs://job-storage/jobServer/* /home/redis/jobServer/
redis-server /home/redis/jobServer/redis.conf

cat > /etc/systemd/system/jobServer.service << EOL
[Unit]
Description=Gunicorn instance to serve jobs
After=network.target

[Service]
User=redis
Group=www-data
WorkingDirectory=/home/redis/jobServer/
Environment="PATH=/home/redis/jobServer/jobServerEnv/bin"
ExecStart=/home/redis/jobServer/jobServerEnv/bin/gunicorn --bind unix:/tmp/jobServer.sock deploy:app --log-file /home/redis/logs/gunicorn.log --log-level DEBUG

[Install]
WantedBy=multi-user.target
EOL

systemctl start jobServer
systemctl enable jobServer

cat > /etc/systemd/system/jobServerHeartbeat.service << EOL
[Unit]
Description=Infinite process to re-add jobs whose workers have stopped responding.
After=network.target jobServer.service

[Service]
User=redis
Group=www-data
WorkingDirectory=/home/redis/jobServer/
Environment="PATH=/home/redis/jobServer/jobServerEnv/bin"
ExecStart=/home/redis/jobServer/jobServerEnv/bin/python /home/redis/jobServer/checkHeartbeat.py

[Install]
WantedBy=multi-user.target
EOL

systemctl start jobServerHeartbeat
systemctl enable jobServerHeartbeat

cat > /etc/systemd/system/stackDriverMetrics.timer << EOL
[Unit]
Description=Timer to update stack driver metrics for queue size.

[Timer]
OnBootSec=60
OnUnitActiveSec=60
RandomizedDelaySec=10

[Install]
WantedBy=timers.target
EOL

cat > /etc/systemd/system/stackDriverMetrics.service << EOL
[Unit]
Description=Update stack driver metrics for queue size.

[Service]
WorkingDirectory=/home/redis/jobServer/
Environment="PATH=/home/redis/jobServer/jobServerEnv/bin"
ExecStart=/home/redis/jobServer/jobServerEnv/bin/python /home/redis/jobServer/stackDriverMetrics.py
EOL

systemctl start stackDriverMetrics.timer
systemctl enable stackDriverMetrics.timer

cat > /etc/nginx/sites-available/jobServer << EOL
server {
    listen 80;
    server_name jobserver.drosen.me;

    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/jobServer.sock;
    }
}
EOL

ln -s /etc/nginx/sites-available/jobServer /etc/nginx/sites-enabled
systemctl restart nginx

wget https://dl.eff.org/certbot-auto -P /home/redis/
chmod a+x /home/redis/certbot-auto

/home/redis/certbot-auto --nginx -d jobserver.drosen.me --non-interactive --agree-tos --redirect --email "letsencrypt@ddwr.ca"

cat > /etc/systemd/system/certRenew.timer << EOL
[Unit]
Description=Timer to renew let's encypt certs

[Timer]
OnBootSec=300
OnUnitActiveSec=1w
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
EOL

cat > /etc/systemd/system/certRenew.service << EOL
[Unit]
Description=Renew let's encypt certs

[Service]
ExecStart=/home/redis/certbot-auto renew --post-hook "systemctl restart nginx"
EOL

systemctl start certRenew.timer
systemctl enable certRenew.timer

curl -sSO https://dl.google.com/cloudagents/install-monitoring-agent.sh
bash install-monitoring-agent.sh

curl -sSO https://dl.google.com/cloudagents/install-logging-agent.sh
bash install-logging-agent.sh