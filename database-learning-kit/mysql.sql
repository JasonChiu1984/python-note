-- MySQL 8.4 / InnoDB; apply once in a new disposable database.
CREATE TABLE lab_reading (
  device_id BIGINT NOT NULL,
  observed_at DATETIME(6) NOT NULL COMMENT 'UTC by application contract',
  temperature_c DECIMAL(6,2) NOT NULL CHECK (temperature_c BETWEEN -100 AND 200),
  PRIMARY KEY (device_id, observed_at)
) ENGINE=InnoDB;
CREATE TABLE lab_audit (
  event_id CHAR(36) PRIMARY KEY,
  device_id BIGINT NOT NULL,
  observed_at DATETIME(6) NOT NULL,
  FOREIGN KEY (device_id, observed_at) REFERENCES lab_reading (device_id, observed_at)
) ENGINE=InnoDB;
