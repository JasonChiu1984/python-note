-- TimescaleDB 2.13+ generalized hypertable API; DBA must pre-install extension.
-- Standalone schema for a fresh database, not an add-on to postgresql.sql.
BEGIN;
CREATE TABLE public.lab_reading (
  device_id bigint NOT NULL,
  observed_at timestamptz NOT NULL,
  temperature_c numeric(6,2) NOT NULL CHECK (temperature_c BETWEEN -100 AND 200),
  PRIMARY KEY (device_id, observed_at)
);
SELECT create_hypertable('public.lab_reading', by_range('observed_at', INTERVAL '1 day'));
-- Separate audit retention; don't make readings impossible to retire via FK.
CREATE TABLE public.lab_audit (
  event_id char(36) PRIMARY KEY,
  device_id bigint NOT NULL,
  observed_at timestamptz NOT NULL
);
COMMIT;
