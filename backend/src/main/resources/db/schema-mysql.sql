-- Personal Blog API schema (MySQL 8)
-- Usage: mysql -u blog -p myblog < backend/src/main/resources/db/schema-mysql.sql

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(128) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(16)  NOT NULL DEFAULT 'user'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS profile (
    id          BIGINT       PRIMARY KEY,
    name        VARCHAR(128) NOT NULL,
    subtitle    VARCHAR(255) NOT NULL DEFAULT '',
    bio         TEXT,
    focus_json  TEXT,
    avatar_url  VARCHAR(512) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS topics (
    id           VARCHAR(64)  PRIMARY KEY,
    title        VARCHAR(255) NOT NULL,
    excerpt      VARCHAR(512) NOT NULL DEFAULT '',
    tag          VARCHAR(64)  NOT NULL DEFAULT '专题',
    record_date  VARCHAR(32)  NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notes (
    id           VARCHAR(64)  PRIMARY KEY,
    title        VARCHAR(255) NOT NULL,
    excerpt      VARCHAR(512) NOT NULL DEFAULT '',
    tag          VARCHAR(64)  NOT NULL DEFAULT '笔记',
    topic_id     VARCHAR(64)  NOT NULL,
    content      MEDIUMTEXT,
    record_date  VARCHAR(32)  NOT NULL DEFAULT '',
    images_json  MEDIUMTEXT,
    view_count   INT          NOT NULL DEFAULT 0,
    pinned       TINYINT(1)   NOT NULL DEFAULT 0,
    status       VARCHAR(16)  NOT NULL DEFAULT 'published',
    KEY idx_notes_topic (topic_id),
    KEY idx_notes_date (record_date),
    KEY idx_notes_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS life_records (
    id           VARCHAR(64)  PRIMARY KEY,
    title        VARCHAR(255) NOT NULL,
    excerpt      VARCHAR(512) NOT NULL DEFAULT '',
    tag          VARCHAR(64)  NOT NULL DEFAULT '生活',
    content      MEDIUMTEXT,
    record_date  VARCHAR(32)  NOT NULL DEFAULT '',
    images_json  MEDIUMTEXT,
    view_count   INT          NOT NULL DEFAULT 0,
    pinned       TINYINT(1)   NOT NULL DEFAULT 0,
    status       VARCHAR(16)  NOT NULL DEFAULT 'published',
    KEY idx_life_date (record_date),
    KEY idx_life_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS timeline_items (
    id           VARCHAR(64)  PRIMARY KEY,
    period       VARCHAR(128) NOT NULL DEFAULT '',
    title        VARCHAR(255) NOT NULL,
    description  TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS content_views (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    content_type VARCHAR(16) NOT NULL,
    content_id   VARCHAR(64) NOT NULL,
    viewer_key   VARCHAR(128) NOT NULL,
    UNIQUE KEY uk_content_view (content_type, content_id, viewer_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ai_chat_message (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id   VARCHAR(128) NOT NULL,
    user_id      BIGINT       NOT NULL DEFAULT 0,
    role         VARCHAR(16)  NOT NULL,
    content      MEDIUMTEXT   NOT NULL,
    create_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_chat_session (session_id, user_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
