-- PostgreSQL; apply once in a new disposable database as a migrator.
BEGIN;
CREATE TABLE public.lab_reading (
  device_id bigint NOT NULL,
  observed_at timestamptz NOT NULL,
  temperature_c numeric(6,2) NOT NULL CHECK (temperature_c BETWEEN -100 AND 200),
  PRIMARY KEY (device_id, observed_at)
);
CREATE TABLE public.lab_audit (
  event_id char(36) PRIMARY KEY,
  device_id bigint NOT NULL,
  observed_at timestamptz NOT NULL,
  FOREIGN KEY (device_id, observed_at) REFERENCES public.lab_reading (device_id, observed_at)
);
COMMIT;
