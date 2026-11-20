# nuam · Mantenedor de Calificaciones Tributarias

Prototipo funcional de la Entrega 2 (Proyecto Integrado TIHV43, SOLUCIONES_TECH).
Cubre las historias **HU06 (acceso seguro por corredor)** y **HU02 (ingreso por montos y cálculo de factores)**,
que suman el 40 % de la funcionalidad, más la grilla del mantenedor con filtros, el detalle de una calificación,
la eliminación lógica para el supervisor y un historial básico.

| App | Contenido |
|---|---|
| `usuarios` | Corredor, Rol, Usuario. Login con bloqueo (5 intentos → 15 min), sesión de 30 min, matriz de permisos por rol. |
| `calificaciones` | Mercado, Instrumento, ConceptoTributario (columnas 8 a 37), Calificacion, DetalleCalificacion. Servicio de cálculo en `calculo.py`. |
| `auditoria` | LogAuditoria y DetalleLog (solo inserción). |
| `cargas` | Modelo CargaArchivo (la carga masiva HU04 se programa en el Sprint 5). |

## Probar en el computador (sin AWS)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (en Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt -r requirements-dev.txt
set DJANGO_DEBUG=1              # Windows  (Linux/Mac: export DJANGO_DEBUG=1)
python manage.py migrate
python manage.py cargar_demo --clave "Prueba.Nuam.2026"
python manage.py runserver
```

Abrir http://127.0.0.1:8000. Sin `DB_HOST` usa SQLite; para PostgreSQL complete el `.env` (ver `.env.example`).

### Usuarios de prueba (`cargar_demo`)

| Usuario | Rol | Corredora |
|---|---|---|
| operador_a | Operador | Andes |
| supervisor_a | Supervisor | Andes |
| auditor_a | Auditor | Andes |
| operador_b | Operador | Bío Bío (sirve para probar el aislamiento) |
| admin_nuam | Administrador | – (gestiona usuarios en `/admin/`, no ve calificaciones) |

## Despliegue en AWS (2 EC2)

1. **Subir el código a GitHub** (repositorio del grupo). El `.env` no se sube.
2. **Bucket S3** privado para respaldos, con cifrado por defecto (SSE-S3). Anote el nombre.
3. **Rol IAM** para la EC2 de datos con permiso `s3:PutObject` sobre ese bucket.
   En AWS Academy suele existir el rol `LabRole`/`LabInstanceProfile`: úselo.
4. **Grupos de seguridad**
   - `sg-web`: entrada 443 y 80 desde `0.0.0.0/0`; 22 solo desde *Mi IP*.
   - `sg-datos`: entrada 5432 **solo desde `sg-web`**; 22 solo desde *Mi IP*.
5. **EC2 de datos**: Ubuntu 24.04, t3.micro, `sg-datos`, el rol IAM del paso 3.
   En *Advanced details → User data* pegue `deploy/user-data-datos.sh` (después de cambiar sus 3 valores).
   Al terminar, anote su **IP privada**.
6. **EC2 web**: Ubuntu 24.04, t3.micro, `sg-web`. Pegue `deploy/user-data-web.sh` con el repositorio, la IP privada
   de datos, la misma contraseña de base y la contraseña de los usuarios de prueba.
7. **IP elástica**: asóciela a la EC2 web. Si la asocia *después* de crearla, entre por SSH y actualice
   `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS` en `/opt/nuam/app/.env`, regenere el certificado con la
   nueva IP y ejecute `sudo systemctl restart gunicorn-nuam nginx`.
8. Abrir `https://<IP elástica>`. El certificado es autofirmado: el navegador muestra una advertencia que se acepta
   una vez. Con un dominio (por ejemplo, uno gratuito de DuckDNS) se puede usar `certbot --nginx` y quitarla.

Revisar el avance de cada script con `sudo tail -f /var/log/cloud-init-output.log`.

### Actualizar la versión desplegada

```bash
cd /opt/nuam/app && sudo -u nuam git pull
sudo -u nuam /opt/nuam/venv/bin/pip install -r requirements.txt
sudo -u nuam /opt/nuam/venv/bin/python manage.py migrate --noinput
sudo -u nuam /opt/nuam/venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart gunicorn-nuam
```

## Pruebas (sección 6 del informe)

```bash
# Unitarias, integración y seguridad automatizadas (26 casos) + cobertura
coverage run --source=calificaciones,usuarios,auditoria,cargas --omit="*/migrations/*,*/tests/*" manage.py test calificaciones
coverage report

# Análisis estático y de dependencias
bandit -r calificaciones usuarios auditoria cargas nuam -x "*/tests/*,*/migrations/*"
pip-audit -r requirements.txt

# Rendimiento PR-01 y PR-02 contra el servidor (20 usuarios, 5 minutos)
set NUAM_CLAVE=<clave de los usuarios de prueba>
locust -f pruebas/locustfile.py --host https://<IP> --headless -u 20 -r 4 -t 5m --csv resultados/locust --html resultados/locust.html
```

Para el escaneo con **OWASP ZAP** (PS-08), use el *Automated Scan* de ZAP Desktop sobre `https://<IP>`.

El workflow `.github/workflows/pruebas.yml` ejecuta pruebas, cobertura, Bandit y pip-audit en cada push.

## Reglas de negocio implementadas

- Factor = monto de la columna / suma de los montos de las columnas 8 a 19, con 8 decimales (redondeo half-up).
- Si la suma de los montos 8 a 19 es cero, no se calcula y se informa.
- Si por redondeo la suma de los factores 8 al 19 supera 1, la diferencia se descuenta del factor mayor.
- No se graba una calificación cuyos factores 8 al 19 sumen más de 1, ni con factores fuera de 0 a 1.
- Llave única: corredor + ejercicio + instrumento + secuencia del evento (secuencia > 10.000).

> Los nombres de las columnas 34 a 37 no vienen en la hoja de tipos de datos del HDU; se tomaron de la hoja de
> homologación y conviene confirmarlos con el cliente.
