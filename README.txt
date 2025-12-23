========================================
Tecorb Taxi AI – FastAPI Deployment Guide
========================================

This document explains how to run the Tecorb Taxi FastAPI application
on an Ubuntu EC2 instance.

----------------------------------------
1. SYSTEM REQUIREMENTS
----------------------------------------
- Ubuntu 20.04 / 22.04
- Python 3.10+
- Git
- EC2 instance with port 3016 open

----------------------------------------
2. CLONE THE PROJECT
----------------------------------------
cd /home/ubuntu
git clone https://github.com/abhishek-tec123/tecorbTaxiAI.git
cd tecorbTaxiAI

----------------------------------------
3. CREATE & ACTIVATE VIRTUAL ENV
----------------------------------------
python3 -m venv .TecobAITaxiENV
source .TecobAITaxiENV/bin/activate

----------------------------------------
4. INSTALL DEPENDENCIES
----------------------------------------
pip install --upgrade pip
pip install -r requirements.txt

----------------------------------------
5. PROJECT STRUCTURE
----------------------------------------
appfastapi.py     -> FastAPI entry point
src/              -> All API routes & logic
map_file/         -> Generated maps / static files
requirements.txt  -> Python dependencies

----------------------------------------
6. RUN LOCALLY (TEST)
----------------------------------------
uvicorn appfastapi:app --host 0.0.0.0 --port 3016

Open in browser:
http://<EC2_PUBLIC_IP>:3016/health
http://<EC2_PUBLIC_IP>:3016/docs

----------------------------------------
7. SYSTEMD (PRODUCTION SETUP)
----------------------------------------

Create service file:
sudo nano /etc/systemd/system/tecorb-taxi.service

Paste the following:

[Unit]
Description=Tecorb Taxi FastAPI Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/TecorbAITaxi/tecorbTaxiAI
Environment="PATH=/home/ubuntu/TecorbAITaxi/.TecobAITaxiENV/bin"
ExecStart=/home/ubuntu/TecorbAITaxi/.TecobAITaxiENV/bin/uvicorn appfastapi:app --host 0.0.0.0 --port 3016 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

----------------------------------------
8. START THE SERVICE
----------------------------------------
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable tecorb-taxi
sudo systemctl start tecorb-taxi

Check status:
sudo systemctl status tecorb-taxi

----------------------------------------
9. VIEW LOGS
----------------------------------------
journalctl -u tecorb-taxi -f

----------------------------------------
10. IMPORTANT: EC2 SECURITY GROUP
----------------------------------------
Allow inbound traffic:
- Type: Custom TCP
- Port: 3016
- Source: 0.0.0.0/0


----------------------------------------
12. RESTART AFTER CODE CHANGES
----------------------------------------
sudo systemctl restart tecorb-taxi
