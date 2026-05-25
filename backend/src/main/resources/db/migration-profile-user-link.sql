-- 将 profile 与 users 关联（已有库执行一次即可）
-- Usage: mysql -u blog -p myblog < backend/src/main/resources/db/migration-profile-user-link.sql

SET NAMES utf8mb4;

ALTER TABLE profile
    ADD COLUMN user_id BIGINT NULL COMMENT '关联 users.id' AFTER id;

ALTER TABLE profile
    ADD COLUMN site_owner TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否在着陆页公开展示' AFTER avatar_url;

UPDATE profile
SET user_id = (SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1)
WHERE user_id IS NULL;

UPDATE profile
SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1)
WHERE user_id IS NULL;

UPDATE profile SET site_owner = 1 WHERE user_id IS NOT NULL;

ALTER TABLE profile MODIFY id BIGINT AUTO_INCREMENT;
ALTER TABLE profile MODIFY user_id BIGINT NOT NULL;
ALTER TABLE profile ADD UNIQUE KEY uk_profile_user_id (user_id);
ALTER TABLE profile
    ADD CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES users (id);
