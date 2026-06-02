# 阿里云 ECS 部署指南（Nginx + Spring Boot + Python Agent）

适用于 monorepo 三端同机部署：**前端静态资源** → **Java API :8080** → **Python Agent :8000**（仅本机）。

```
                    ┌─────────────────────────────────────┐
  用户浏览器 ──443──►│ Nginx                               │
                    │  /        → frontend/dist           │
                    │  /api/*   → 127.0.0.1:8080/v1/*     │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ blog-api (Spring Boot :8080)        │
                    │  /v1/agent/chat → 转发 Agent        │
                    └──────────────┬──────────────────────┘
                                   │ 127.0.0.1:8000
                    ┌──────────────▼──────────────────────┐
                    │ blog-agent (FastAPI :8000)          │
                    └─────────────────────────────────────┘
         MySQL / Redis 同机或 RDS；NapCat 可选（:3000/:3001 勿对公网）
```

---

## 1. 服务器准备

| 组件 | 版本建议 |
|------|----------|
| OS | Ubuntu 22.04 / Alibaba Cloud Linux 3 |
| Java | 17（`openjdk-17-jdk`） |
| Node.js | 20 LTS（仅构建前端） |
| Python | 3.11+ |
| MySQL | 8.0 |
| Redis | 6+ |
| Nginx | 1.18+ |

```bash
# Ubuntu 示例
sudo apt update
sudo apt install -y openjdk-17-jdk nginx redis-server mysql-server git

# Node 20（nvm 或 NodeSource 任选其一）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Python venv
sudo apt install -y python3.11 python3.11-venv python3-pip
```

**安全组 / 防火墙**：仅开放 **22、80、443**；**不要**对公网开放 8080、8000、3306、6379、3000、3001。

---

## 2. 目录与代码

```bash
sudo useradd -r -m -d /opt/blog -s /bin/bash blog || true
sudo mkdir -p /opt/blog/config
sudo chown -R blog:blog /opt/blog

sudo -u blog git clone https://github.com/AIlen-yeger/blog.git /opt/blog/app
cd /opt/blog/app
```

后续更新：

```bash
cd /opt/blog/app
git pull origin main
```

---

## 3. 数据库

```bash
mysql -u root -p
```

```sql
CREATE DATABASE IF NOT EXISTS myblog
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 建表（首次）
SOURCE /opt/blog/app/backend/src/main/resources/db/schema-mysql.sql;

-- 按需执行 db/ 下其它 migration-*.sql
```

Agent 相关表（Bug Ops，可选）见项目内 SQL 说明，在 MySQL 中手动执行即可。

---

## 4. 私密配置（勿提交 Git）

### 4.1 Java 生产配置：`backend/src/main/resources/application-prod.yml`

**推荐（与本地习惯一致）**：放在 `resources` 下，打 jar 时打进包，启动加 `--spring.profiles.active=prod`。

```bash
cd /opt/blog/backend/src/main/resources
cp application-prod.yml.example application-prod.yml
# 编辑 application-prod.yml（勿提交 Git）
cd /opt/blog/backend && mvn clean package -DskipTests
```

`deploy/systemd/blog-api.service` 已使用 `--spring.profiles.active=prod`（不再依赖 `/opt/blog/config/application-prod.yml`）。

**可选**：仍可使用 `/opt/blog/config/application-prod.yml` + `--spring.config.additional-location=...` 与代码目录分离。

从 `application-local.yml` 复制后修改生产项示例：

```yaml
server:
  port: 8080
  servlet:
    context-path: /v1

spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/myblog?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
    username: blog_user
    password: '你的数据库密码'
  data:
    redis:
      host: 127.0.0.1
      port: 6379
      database: 5
  mail:
    username: ${QQ_SMTP_USER}
    password: ${QQ_SMTP_AUTH_CODE}

app:
  seed:
    enabled: false
  jwt:
    secret: '生产用随机字符串至少32位'
  dev:
    fixed-verification-code: ''   # 生产必须留空
  mail:
    enabled: true
    from: ${QQ_SMTP_USER}
    reply-to: ${QQ_SMTP_USER}
  upload:
    avatar-dir: /opt/blog/backend/uploads/avatars
    content-dir: /opt/blog/backend/uploads/content
  agent:
    base-url: http://127.0.0.1:8000
    chat-path: /ai/chat
  cors:
    allowed-origins: "https://你的域名.com"
```

```bash
sudo mkdir -p /opt/blog/backend/uploads/{avatars,content}
sudo chown -R blog:blog /opt/blog/backend/uploads /opt/blog/config
sudo chmod 600 /opt/blog/config/application-prod.yml
```

### 4.2 Java 环境变量：`/opt/blog/config/blog-api.env`

```bash
QQ_SMTP_USER=你的QQ号@qq.com
QQ_SMTP_AUTH_CODE=QQ邮箱SMTP授权码
```

```bash
sudo chmod 600 /opt/blog/config/blog-api.env
```

### 4.3 Python：`/opt/blog/app/python/.env`

```bash
cp /opt/blog/app/python/.env.example /opt/blog/app/python/.env
# 编辑填写：
# MYSQL_*、DP_AGENT_API_KEY、BLOG_API_BASE=http://127.0.0.1:8080/v1
chmod 600 /opt/blog/app/python/.env
```

`config/config.yml` 中 **不要** 写明文密钥，走 `.env` 即可。

---

## 5. 构建

```bash
cd /opt/blog/app

# 前端（生产不要 VITE_BASE_PATH=/blog/）
cp frontend/.env.production.example frontend/.env.production
cd frontend
npm ci
npm run build
cd ..

# 后端 JAR
cd backend
mvn -DskipTests package
cd ..

# Python 虚拟环境
cd python
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..
```

构建产物：

| 路径 | 说明 |
|------|------|
| `frontend/dist/` | Nginx 静态根目录 |
| `backend/target/personal-blog-api-1.0.0.jar` | Spring Boot |
| `python/.venv/` | Agent 依赖 |

---

## 6. systemd 服务

```bash
sudo cp /opt/blog/app/deploy/systemd/blog-api.service /etc/systemd/system/
sudo cp /opt/blog/app/deploy/systemd/blog-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now blog-api blog-agent
```

查看状态：

```bash
sudo systemctl status blog-api blog-agent
journalctl -u blog-api -f
journalctl -u blog-agent -f
```

---

## 7. Nginx

```bash
sudo cp /opt/blog/app/deploy/nginx/blog.conf /etc/nginx/sites-available/blog.conf
# 编辑 server_name、ssl 证书路径（若已申请）
sudo ln -sf /etc/nginx/sites-available/blog.conf /etc/nginx/sites-enabled/blog.conf
sudo nginx -t && sudo systemctl reload nginx
```

### HTTPS（推荐）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名.com
```

申请成功后，`app.cors.allowed-origins` 改为 `https://你的域名.com`。

---

## 8. 健康检查

```bash
# Agent（仅本机）
curl -s http://127.0.0.1:8000/health

# Java（经 context-path）
curl -s http://127.0.0.1:8080/v1/meta/agent-reply-settings

# 经 Nginx
curl -sI https://你的域名.com/
curl -s https://你的域名.com/api/meta/agent-reply-settings
```

桌宠 Agent 对话走 `POST /api/agent/chat`（SSE），需登录 JWT。

---

## 9. 日常发布流程

```bash
cd /opt/blog/app && git pull origin main

# 前端：push 只更新源码，必须 build 后 Nginx 才会变
bash deploy/scripts/deploy-frontend.sh

cd backend && mvn -DskipTests package && cd ..
sudo systemctl restart blog-api
cd python && .venv/bin/pip install -r requirements.txt && cd ..
sudo systemctl restart blog-agent
sudo nginx -t && sudo systemctl reload nginx
```

**页面仍是旧版？** 检查 Nginx `root` 是否指向最新 `frontend/dist`（旧部署可能是 `/opt/personal-blog/frontend`）。

**大文件**：`public/music/`、`landing-rain.mp4` 不在 Git，需 scp 到服务器后再 build。

---

## 10. NapCat（QQ 告警，可选）

```bash
cd /opt/blog/python/docker/napcat
mkdir -p data/QQ data/config
# 镜像使用 Docker Hub：mlikiowa/napcat-docker（ports 已绑 127.0.0.1）
docker-compose up -d
docker logs -f napcat   # 首次扫码登录；WebUI: http://127.0.0.1:6099/webui
```

在 **`python/.env`** 中配置 Agent 侧 QQ 告警（与 NapCat 同机）：

```env
NAPCAT_NOTIFY_ENABLED=true
NAPCAT_HTTP_URL=http://127.0.0.1:3000
NAPCAT_ALERT_QQ=你的QQ号
# NAPCAT_ACCESS_TOKEN=   # 与 NapCat HTTP 配置一致时填写
NAPCAT_MIN_SEVERITY=high
NAPCAT_ALERT_ON_ERROR=true
AGENT_OPS_TOKEN=随机长串
```

重启 Agent 后日志应出现 `[config] napcat ... configured=True`。

**测试 QQ 私聊**（需 `AGENT_OPS_TOKEN`）：

```bash
curl -s -X POST http://127.0.0.1:8000/ai/ops/napcat-test \
  -H "X-Ops-Token: 你的token"
```

**NapCat HTTP 直连**（排查 Agent 之外的问题）：

```bash
curl -s -X POST http://127.0.0.1:3000/send_private_msg \
  -H "Content-Type: application/json" \
  -d '{"user_id":你的QQ号,"message":[{"type":"text","data":{"text":"ping"}}]}'
```

Bug Ops 手动巡检（需配置 `AGENT_OPS_TOKEN`）：

```bash
curl -X POST http://127.0.0.1:8000/ai/ops/bug-scan \
  -H "X-Ops-Token: 你的token"
```

---

## 11. 常见问题

| 现象 | 排查 |
|------|------|
| 图片 404 | `app.upload.*-dir` 是否为绝对路径；Nginx `/api/uploads/` 是否反代到 Java |
| Agent 无回复 | `journalctl -u blog-agent`；`.env` 中 `DP_AGENT_API_KEY`；Java `app.agent.base-url` |
| SSE 卡住 / 超时 | Nginx `proxy_buffering off`、`proxy_read_timeout 300s` |
| 注册收不到邮件 | `QQ_SMTP_*` 环境变量；`app.dev.fixed-verification-code` 是否误填 |
| CORS 错误 | `app.cors.allowed-origins` 是否包含前端域名（含 https） |

---

## 12. 安全检查清单

- [ ] `application-prod.yml`、`.env`、`blog-api.env` 权限 `600`，不在 Git 中
- [ ] 生产 JWT secret、SMTP 授权码、API Key 已轮换
- [ ] `fixed-verification-code` 为空
- [ ] 8080 / 8000 / 3306 / 6379 未对公网开放
- [ ] GitHub Pages 已关闭（Settings → Pages → None）
- [ ] 定期 `git pull` + 重启服务
