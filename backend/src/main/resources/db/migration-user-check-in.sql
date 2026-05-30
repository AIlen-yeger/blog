-- 用户签到记录（按用户 + 日期唯一）
-- Usage: mysql -u root -p myblog < backend/src/main/resources/db/migration-user-check-in.sql

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS user_check_in (
    id           BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT       NOT NULL COMMENT 'users.id',
    check_in_date DATE        NOT NULL COMMENT '签到自然日',
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_check_in (user_id, check_in_date),
    KEY idx_user_check_in_user (user_id, check_in_date),
    CONSTRAINT fk_user_check_in_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户每日签到';
