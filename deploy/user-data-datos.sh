#!/bin/bash
# =====================================================================
# EC2 de DATOS (PostgreSQL 16) · Ubuntu 24.04 · t3.micro
# Pegar en "Advanced details > User data" al crear la instancia.
# ANTES de pegar, cambie los 3 valores de abajo.
# Registro de la ejecución: /var/log/cloud-init-output.log
# =====================================================================
set -euo pipefail

DB_PASSWORD="CAMBIAR-clave-larga-de-la-base"   # la misma que irá en el .env de la EC2 web
RED_PRIVADA="172.31.0.0/16"                    # bloque CIDR de su VPC (la VPC por defecto usa 172.31.0.0/16)
BUCKET_S3="nuam-respaldos-grupoXX"             # bucket privado y cifrado para los respaldos

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y postgresql-16 unzip
snap install aws-cli --classic

CONF=/etc/postgresql/16/main
# Escuchar en la red privada; la entrada real la limita el grupo de seguridad (solo la EC2 web).
sed -i "s/^#\?listen_addresses.*/listen_addresses = '*'/" $CONF/postgresql.conf
sed -i "s/^#\?password_encryption.*/password_encryption = scram-sha-256/" $CONF/postgresql.conf
# Solo conexiones cifradas (hostssl) desde la red privada, con contraseña.
echo "hostssl nuam nuam_app ${RED_PRIVADA} scram-sha-256" >> $CONF/pg_hba.conf
systemctl restart postgresql

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE nuam_app LOGIN PASSWORD '${DB_PASSWORD}';
CREATE DATABASE nuam OWNER nuam_app;
SQL

# Respaldo diario a S3 a las 03:00 (requiere un rol IAM con permiso s3:PutObject sobre el bucket).
cat > /usr/local/bin/respaldo-nuam.sh <<SCRIPT
#!/bin/bash
set -euo pipefail
ARCHIVO=/tmp/nuam-\$(date +%F).sql.gz
sudo -u postgres pg_dump nuam | gzip > \$ARCHIVO
/snap/bin/aws s3 cp \$ARCHIVO s3://${BUCKET_S3}/postgres/ --sse AES256
rm -f \$ARCHIVO
SCRIPT
chmod 700 /usr/local/bin/respaldo-nuam.sh
echo "0 3 * * * root /usr/local/bin/respaldo-nuam.sh >> /var/log/respaldo-nuam.log 2>&1" > /etc/cron.d/respaldo-nuam

echo "EC2 de datos lista."
