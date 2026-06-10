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
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT       NOT NULL UNIQUE COMMENT '关联 users.id，一人一份资料',
    name         VARCHAR(128) NOT NULL,
    subtitle     VARCHAR(255) NOT NULL DEFAULT '',
    bio          TEXT,
    focus_json   TEXT,
    avatar_url   VARCHAR(512) NOT NULL DEFAULT '',
    site_owner   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1=站点着陆页公开展示',
    agent_reply_owner_only TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1=Agent 回复仅管理员可见',
    CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_check_in (
    id            BIGINT    NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id       BIGINT    NOT NULL COMMENT 'users.id',
    check_in_date DATE      NOT NULL COMMENT '签到自然日',
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_check_in (user_id, check_in_date),
    KEY idx_user_check_in_user (user_id, check_in_date),
    CONSTRAINT fk_user_check_in_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户每日签到';

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
    status              VARCHAR(16)  NOT NULL DEFAULT 'published',
    agent_reply_status  VARCHAR(16)  NOT NULL DEFAULT 'none' COMMENT 'none|pending|running|done|failed',
    agent_reply         MEDIUMTEXT   NULL COMMENT 'Kohaku 自动回复全文',
    agent_reply_job_id  VARCHAR(64)  NULL COMMENT '关联 content_agent_comment_job.job_id',
    KEY idx_notes_topic (topic_id),
    KEY idx_notes_date (record_date),
    KEY idx_notes_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS content_agent_comment_job (
    id                BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    content_type      VARCHAR(16)  NOT NULL COMMENT 'note | life',
    content_id        VARCHAR(64)  NOT NULL,
    job_id            VARCHAR(64)  NOT NULL,
    idempotency_key   VARCHAR(128) NOT NULL,
    content_hash      CHAR(64)     NOT NULL,
    session_id        VARCHAR(128) NULL,
    user_id           BIGINT       NOT NULL DEFAULT 0,
    status            VARCHAR(16)  NOT NULL DEFAULT 'pending',
    agent_reply       MEDIUMTEXT   NULL,
    error_message     VARCHAR(512) NULL,
    trace_id          VARCHAR(64)  NULL,
    requested_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    started_at        DATETIME(3)  NULL,
    completed_at      DATETIME(3)  NULL,
    UNIQUE KEY uk_agent_comment_idempotency (idempotency_key),
    KEY idx_agent_comment_content (content_type, content_id, status),
    KEY idx_agent_comment_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Kohaku 内容评价生成任务';

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
    agent_reply  MEDIUMTEXT   NULL COMMENT 'Kohaku 自动回复全文',
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

CREATE TABLE IF NOT EXISTS user_music_track (
    id           VARCHAR(64)  NOT NULL PRIMARY KEY,
    user_id      BIGINT       NOT NULL COMMENT 'users.id',
    qq_song_id   VARCHAR(32)  NOT NULL COMMENT 'QQ 音乐 songid',
    title        VARCHAR(255) NOT NULL DEFAULT '',
    artist       VARCHAR(255) NOT NULL DEFAULT '',
    src          VARCHAR(512) NOT NULL DEFAULT '',
    duration_sec INT          NULL,
    source_url   VARCHAR(1024) NULL,
    sort_order   INT          NOT NULL DEFAULT 0,
    play_count   INT          NOT NULL DEFAULT 0 COMMENT '累计播放次数',
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_qq_song (user_id, qq_song_id),
    KEY idx_user_music_sort (user_id, sort_order, created_at),
    CONSTRAINT fk_user_music_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户音乐播放列表';

CREATE TABLE IF NOT EXISTS ai_chat_session (
    session_id   VARCHAR(128) NOT NULL PRIMARY KEY,
    user_id      BIGINT       NOT NULL,
    guest_flag   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '0=登录用户 1=访客',
    title        VARCHAR(255) NOT NULL DEFAULT '新对话',
    msg_count    INT          NOT NULL DEFAULT 0,
    last_msg_id  BIGINT       NULL,
    last_active  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_chat_session_user (user_id, last_active DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent Web 对话会话';

CREATE TABLE IF NOT EXISTS ai_chat_message (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id   VARCHAR(128) NOT NULL,
    user_id      BIGINT       NOT NULL DEFAULT 0,
    channel      VARCHAR(16)  NOT NULL DEFAULT 'web' COMMENT 'web | qq | internal',
    role         VARCHAR(16)  NOT NULL,
    content      MEDIUMTEXT   NOT NULL,
    create_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_chat_session (session_id, user_id, id),
    KEY idx_chat_session_channel (session_id, user_id, channel, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
