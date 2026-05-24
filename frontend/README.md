# 个人博客

基于 Vue 3 + Vite + TypeScript 的个人博客首页，按提示词实现登录动效与内容展示。

## 功能

- 首页：头像、名称、简介 + 随时间变化的渐变背景
- 头像下方「向上滑动」提示；PC 端滚轮**向下**打开登录；移动端上滑打开登录
- QQ 邮箱 + 密码登录；新用户进入邮箱验证码注册（开发环境验证码 `123456`，控制台也会打印）
- 登录后：参考信息站布局——左侧固定导航 + 右侧分块纵向滚动（关于 / 学习笔记 / 专题 / 学习轨迹）

## 开发

```bash
cd C:\Users\奥利奥\Projects\personal-blog
npm install
npm run dev
```

构建：`npm run build`

## 后端 API

Spring Boot 实现见 [`backend/README.md`](backend/README.md)，接口规范见 [`docs/API.md`](docs/API.md)。

```bash
cd backend
mvn spring-boot:run
```

默认地址：`http://localhost:8080/v1`。演示账号：`admin@qq.com` / `admin123`（管理员）。

## 说明

当前前端认证仍为 **localStorage 本地演示**。对接后端时设置 `VITE_API_BASE` 并改造 `src/api/auth.ts` 等模块为真实 HTTP 请求。
