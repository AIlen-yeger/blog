# 个人博客 API（Spring Boot + MyBatis）

## 架构

```
controller  →  service（接口）  →  service.impl（实现）  →  mapper  →  mapper.xml  →  MySQL
```

| 层级 | 包路径 | 说明 |
|------|--------|------|
| Controller | `com.personalblog.controller` | REST 接口 |
| Service | `com.personalblog.service` | 业务接口 |
| ServiceImpl | `com.personalblog.service.impl` | 业务实现 |
| Mapper | `com.personalblog.mapper` | MyBatis 接口 |
| Mapper XML | `resources/mapper/*.xml` | SQL 映射 |
| Entity | `com.personalblog.entity` | 数据对象 |

## 启动

```bash
mvn spring-boot:run
```

数据库：`myblog`（见 `application.yml`）

建表脚本：`src/main/resources/db/schema-mysql.sql`

## 演示账号

| 邮箱 | 密码 | 角色 |
|------|------|------|
| admin@qq.com | admin123 | admin |
| reader@qq.com | reader123 | user |

API 基址：`http://localhost:8080/v1`

## 鉴权说明

| 能力 | 技术 |
|------|------|
| 登录 Token | **JWT**（JJWT，HMAC-SHA256），请求头 `Authorization: Bearer <token>` |
| 请求鉴权 | **`JwtAuthInterceptor`**：每次进 Controller 前解析并校验 JWT |
| 注册验证码 | **Redis** 缓存（非 MySQL） |

### JWT 拦截器流程

```
请求进入 → JwtAuthInterceptor.preHandle
  → 公开路径 /auth/**、/uploads/**：不强制登录（有合法 token 仍会解析）
  → 其它路径：校验 Bearer JWT（签名 + 过期 + role）
  → 无效/缺失 → 401 JSON；有效 → 写入 SecurityContext → Controller
  → afterCompletion 清理上下文
```

### 验证码 Redis 策略

| Key | 说明 | TTL |
|-----|------|-----|
| `register:pending:{email}` | 验证码 + 密码哈希 JSON | 300s（可配置 `app.register.code-ttl-seconds`） |
| `register:cooldown:{email}` | 发送冷却标记 | **60s**（防重复发送） |
| `register:daily:{email}:{日期}` | 当日已发送次数 | 至当日 24:00，**每天最多 5 次** |

需本地启动 Redis（默认 `localhost:6379`）。

### 注册验证码邮件（腾讯云 SES）

发信实现：`MailService` → `TencentSesMailServiceImpl`（`SesClient.SendEmail`）。

| 配置 | 说明 |
|------|------|
| `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY` | 环境变量（推荐，与官方 SDK 一致） |
| `app.tencent.ses.region` | 如 `ap-guangzhou` |
| `app.mail.from` | SES 控制台已验证的发件邮箱 |
| `app.mail.template-id` | `0` 用 HTML 正文；填模板 ID 则用模板变量 `code` |
| `app.mail.enabled` | `false` 时仅缓存 Redis + 日志，不调 SES |

发送顺序：限流 → 生成验证码 → **Redis** → **腾讯云 SES** → 注册 QQ 邮箱。

上线前在 [SES 控制台](https://console.cloud.tencent.com/ses) 验证发件地址，密钥勿提交到 Git。
