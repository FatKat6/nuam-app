#!/bin/bash
# =====================================================================
# EC2 WEB (Nginx + Gunicorn + Django) · Ubuntu 24.04 · t3.micro
# Pegar en "Advanced details > User data" al crear la instancia,
# DESPUÉS de crear la EC2 de datos (necesita su IP privada).
# ANTES de pegar, cambie los valores de abajo.
# Registro de la ejecución: /var/log/cloud-init-output.log
# =====================================================================
set -euo pipefail

REPO_URL="https://github.com/USUARIO/nuam-app.git"   # repositorio del grupo (público, o use una deploy key)
DB_HOST="172.31.X.X"                                 # IP PRIVADA de la EC2 de datos
DB_PASSWORD="CAMBIAR-clave-larga-de-la-base"         # la misma del script de datos
CLAVE_DEMO="CAMBIAR.Demo.2026"                       # contraseña de los usuarios de prueba (mín. 10 caracteres)

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-venv python3-pip nginx git openssl

useradd --system --create-home --home-dir /opt/nuam --shell /usr/sbin/nologin nuam || true
git clone "$REPO_URL" /opt/nuam/app
python3 -m venv /opt/nuam/venv
/opt/nuam/venv/bin/pip install --upgrade pip
/opt/nuam/venv/bin/pip install -r /opt/nuam/app/requirements.txt

# IP pública de la instancia (IMDSv2) para ALLOWED_HOSTS
TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
IP_PUBLICA=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)

cat > /opt/nuam/app/.env <<ENV
DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=${IP_PUBLICA},localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://${IP_PUBLICA}
DB_HOST=${DB_HOST}
DB_NAME=nuam
DB_USER=nuam_app
DB_PASSWORD=${DB_PASSWORD}
DB_SSLMODE=require
ENV
chmod 600 /opt/nuam/app/.env
chown -R nuam:nuam /opt/nuam

cd /opt/nuam/app
sudo -u nuam /opt/nuam/venv/bin/python manage.py migrate --noinput
sudo -u nuam /opt/nuam/venv/bin/python manage.py collectstatic --noinput
chmod o+x /opt/nuam /opt/nuam/app && chmod -R o+rX /opt/nuam/app/staticfiles   # Nginx debe leer los estáticos
sudo -u nuam /opt/nuam/venv/bin/python manage.py cargar_demo --clave "$CLAVE_DEMO"

# Gunicorn como servicio
cp deploy/gunicorn-nuam.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now gunicorn-nuam

# Certificado autofirmado para HTTPS sobre la IP (con dominio, reemplazar por certbot)
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/nuam.key -out /etc/nginx/ssl/nuam.crt \
  -subj "/CN=${IP_PUBLICA}" -addext "subjectAltName=IP:${IP_PUBLICA}"
chmod 600 /etc/nginx/ssl/nuam.key

cp deploy/nginx-nuam.conf /etc/nginx/sites-available/nuam
ln -sf /etc/nginx/sites-available/nuam /etc/nginx/sites-enabled/nuam
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "EC2 web lista en https://${IP_PUBLICA}"
