-- Agent 对笔记 / 生活记录的自动回复字段 + 演示数据
-- mysql -u root -p myblog < backend/src/main/resources/db/migration-agent-reply.sql

USE myblog;

ALTER TABLE notes
    ADD COLUMN agent_reply MEDIUMTEXT NULL COMMENT 'Kohaku 自动回复全文' AFTER status;

ALTER TABLE life_records
    ADD COLUMN agent_reply MEDIUMTEXT NULL COMMENT 'Kohaku 自动回复全文' AFTER status;

-- 演示专题（若无则插入）
INSERT INTO topics (id, title, excerpt, tag, record_date)
SELECT 't-kohaku-demo', 'Kohaku 演示', 'Agent 回复 UI 测试用专题', '专题', '2026-05-23'
WHERE NOT EXISTS (SELECT 1 FROM topics WHERE id = 't-kohaku-demo');

-- 演示笔记（长回复，便于前端卡片截断测试）
INSERT INTO notes (
    id, title, excerpt, tag, topic_id, content, record_date,
    images_json, view_count, pinned, status, agent_reply
)
SELECT
    'n-kohaku-demo',
    'Kohaku 回复演示笔记',
    '用于测试 Agent 回复在卡片与阅读全文中的展示效果。',
    '笔记',
    't-kohaku-demo',
    '这是一篇演示笔记正文。发布笔记后，Kohaku 会根据内容生成一段回复，显示在卡片摘要下方；超出预览字数时显示省略号，完整内容在「阅读全文」弹窗中查看。',
    '2026-05-23',
    '[]',
    0,
    0,
    'published',
    '读完了你的这篇笔记。你把学习过程写成可回顾的片段，这很像在雪地里留下一串脚印——回头看时，会发现自己已经走了很远。Kohaku 尤其注意到你强调「结构化」和「复盘」：说明你不只想记录输入，还想把输入变成属于自己的理解。若下次写完想整理关键词或延伸联想，也可以再叫我帮忙。'
WHERE NOT EXISTS (SELECT 1 FROM notes WHERE id = 'n-kohaku-demo');

-- 演示生活记录
INSERT INTO life_records (
    id, title, excerpt, tag, content, record_date,
    images_json, view_count, pinned, status, agent_reply
)
SELECT
    'l-kohaku-demo',
    'Kohaku 回复演示生活',
    '生活记录 Agent 回复展示测试。',
    '生活',
    '今天想试试把生活片段也交给 Kohaku 回应一下。也许只是一句天气、一段散步，也值得被温柔地接住。',
    '2026-05-23',
    '[]',
    0,
    0,
    'published',
    '这段记录里有很轻的日常感，像窗台上刚晾干的杯子。Kohaku 读到的不是大事，而是你在平凡里仍愿意留一点空白给自己——这本身就很珍贵。'
WHERE NOT EXISTS (SELECT 1 FROM life_records WHERE id = 'l-kohaku-demo');

-- 若已有标题为 TEST 的笔记，为其补上回复（便于对接你现有数据）
UPDATE notes
SET agent_reply = 'TEST 笔记收到了。Kohaku 看到这里像是占位或调试内容；等你换上真实正文后，我会根据你的文字再写一段更贴切的回应。'
WHERE title = 'TEST'
  AND (agent_reply IS NULL OR agent_reply = '');
