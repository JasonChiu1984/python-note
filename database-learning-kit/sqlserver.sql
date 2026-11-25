-- SQL Server 2022 / T-SQL; apply once in a new disposable database, as a migrator.
CREATE TABLE dbo.lab_reading (
  device_id bigint NOT NULL,
  observed_at datetimeoffset(6) NOT NULL,
  temperature_c decimal(6,2) NOT NULL CHECK (temperature_c BETWEEN -100 AND 200),
  PRIMARY KEY (device_id, observed_at)
);
CREATE TABLE dbo.lab_audit (
  event_id char(36) PRIMARY KEY,
  device_id bigint NOT NULL,
  observed_at datetimeoffset(6) NOT NULL,
  FOREIGN KEY (device_id, observed_at) REFERENCES dbo.lab_reading (device_id, observed_at)
);
