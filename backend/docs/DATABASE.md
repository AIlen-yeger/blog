# 数据库说明

**不需要 MCP。** 建表有三种方式，任选其一即可。

## 方式一：启动后端自动建表（默认，推荐）

`application.yml` 已配置：

```yaml
spring.jpa.hibernate.ddl-auto: update
```

执行 `mvn spring-boot:run` 后启动应用。演示数据**默认不会**自动写入；若需要种子数据，在 `application.yml` 设 `app.seed.enabled: true` 启动**一次**后改回 `false`。

数据文件位置：`backend/data/personal-blog.mv.db`（H2 文件库）。

查看表：浏览器打开 `http://localhost:8080/v1/h2-console`  
- JDBC URL：`jdbc:h2:file:./data/personal-blog`  
- 用户名：`sa`，密码留空  

（需在 `backend` 目录启动应用，路径才正确。）

---

## 方式二：手动执行 SQL 脚本

脚本位置：

| 数据库 | 文件 |
|--------|------|
| H2 | `src/main/resources/db/schema-h2.sql` |
| MySQL 8 | `src/main/resources/db/schema-mysql.sql` |

### H2 控制台

1. 启动应用或单独打开 H2 Console  
2. 连接后粘贴执行 `schema-h2.sql`  
3. 演示账号：设 `app.seed.enabled: true` 启动一次，由 `DataInitializer` 写入（密码为 BCrypt，不宜手写 SQL）

### MySQL

```sql
CREATE DATABASE personal_blog DEFAULT CHARSET utf8mb4;
```

在客户端执行 `schema-mysql.sql`，然后修改 `application.yml` 切换数据源（见下方 MySQL 配置示例）。

---

## 方式三：使用 MySQL 配置文件

复制并修改 `application-mysql.yml` 中的账号密码，启动时指定 profile：

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=mysql
```

表仍可由 `ddl-auto: update` 自动生成；若希望**仅用 SQL、不让 Hibernate 改表**，可设：

```yaml
spring.jpa.hibernate.ddl-auto: none
spring.sql.init.mode: always
spring.sql.init.schema-locations: classpath:db/schema-mysql.sql
```

---

## 表结构一览

| 表名 | 说明 |
|------|------|
| `users` | 用户（邮箱、BCrypt 密码、角色） |
| `pending_registrations` | 注册待验证（验证码、过期时间） |
| `profile` | 个人资料（单行，id=1） |
| `topics` | 专题 |
| `notes` | 学习笔记，`topic_id` → `topics.id` |
| `life_records` | 生活记录 |
| `timeline_items` | 学习轨迹 |

---

## 常见问题

**Q：还要接数据库 MCP 吗？**  
A：不用。本地 H2 或你自己的 MySQL 即可。

**Q：表已经存在，会重复建吗？**  
A：脚本使用 `CREATE TABLE IF NOT EXISTS`；`ddl-auto: update` 只会补列，不会删表。

**Q：演示账号密码？**  
A：`admin@qq.com` / `admin123`，`reader@qq.com` / `reader123`（首次启动由程序插入）。
