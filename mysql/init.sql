CREATE DATABASE IF NOT EXISTS shortsdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE shortsdb;

CREATE TABLE IF NOT EXISTS shorts (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  title        VARCHAR(100) NOT NULL,
  genre        ENUM('horror','history','success') NOT NULL,
  hook         TEXT,
  hashtags     JSON,
  filename     VARCHAR(200) NOT NULL,
  file_size_mb FLOAT DEFAULT 0,
  status       ENUM('done','error') DEFAULT 'done',
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
