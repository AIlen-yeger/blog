-- 将站点主人标记到已有签到数据的用户（按 user_id 调整）
-- Usage: mysql -u root -p myblog < backend/src/main/resources/db/migration-fix-site-owner-check-in.sql

SET NAMES utf8mb4;

-- 先取消所有站点主人标记
UPDATE profile SET site_owner = 0;

-- 把站点主人设为你的管理员账号（示例：user_id = 7，请按实际修改）
UPDATE profile SET site_owner = 1 WHERE user_id = 7;

-- 验证
-- SELECT user_id, name, site_owner FROM profile WHERE site_owner = 1;
-- SELECT user_id, COUNT(*) AS total_days FROM user_check_in GROUP BY user_id;
