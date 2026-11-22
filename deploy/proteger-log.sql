-- Deja el log de auditoría en "solo inserción" también a nivel de base de datos (sección 5.4 del informe).
-- Ejecutar en la EC2 de datos, después de la primera migración:
--   sudo -u postgres psql -d nuam -f proteger-log.sql
BEGIN;
ALTER TABLE auditoria_logauditoria OWNER TO postgres;
ALTER TABLE auditoria_detallelog OWNER TO postgres;
REVOKE ALL ON auditoria_logauditoria, auditoria_detallelog FROM nuam_app;
GRANT SELECT, INSERT, REFERENCES ON auditoria_logauditoria, auditoria_detallelog TO nuam_app;
GRANT USAGE, SELECT ON SEQUENCE auditoria_logauditoria_id_seq, auditoria_detallelog_id_seq TO nuam_app;
COMMIT;
