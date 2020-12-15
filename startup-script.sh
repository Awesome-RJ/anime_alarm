# Install Stackdriver logging agent
curl -sSO https://dl.google.com/cloudagents/install-logging-agent.sh
sudo bash install-logging-agent.sh

#Install python3.8
sudo apt update
sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libsqlite3-dev libreadline-dev libffi-dev curl libbz2-dev
curl -O https://www.python.org/ftp/python/3.8.2/Python-3.8.2.tar.xz
tar -xf Python-3.8.2.tar.xz
ls -a
cd Python-3.8.2
./configure --enable-optimizations

make -j 2
sudo make altinstall
cd ..

# Install or update needed software
apt-get update
apt-get install -yq git supervisor

# Check python version
python3.8 --version
python --version

# Account to own server process
# Creating a new user for this app
useradd -m -d /home/pythonapp pythonapp

# Fetch source code
export HOME=/root
ls -a
git clone https://github.com/GoZaddy/anime_alarm.git /opt/app


# Python environment setup
python3.8 -m venv /opt/app/env
source /opt/app/env/bin/activate
/opt/app/env/bin/pip install -r /opt/app/requirements.txt

# Set ownership to newly created account
chown -R pythonapp:pythonapp /opt/app

# Put supervisor configuration in proper place
cp /opt/app/python-app.conf /etc/supervisor/conf.d/python-app.conf

# Start service via supervisorctl
supervisorctl reread
supervisorctl update