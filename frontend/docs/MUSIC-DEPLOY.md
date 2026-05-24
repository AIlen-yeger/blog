# 关于页音乐 — 公网部署说明

## 1. 音频文件放哪里

构建时，`public/music/` 会原样复制到站点根目录。启动或构建前会自动生成 `manifest.json` 扫描目录内所有 mp3/m4a 等文件，访问路径形如 `https://你的域名/music/歌手%20-%20歌名.mp3`（中文与空格会自动编码）。

| 方式 | 适用场景 |
|------|----------|
| **同站静态** | 个人博客、曲目少（1～5 首），把 mp3 放进 `public/music/` 后 `npm run build` 一起部署 |
| **对象存储 + CDN** | 文件较大或流量高：上传到阿里云 OSS / 腾讯云 COS / Cloudflare R2 等，在 `musicTracks.ts` 里把 `src` 写成完整 `https://...` URL |
| **环境变量前缀** | 所有曲目仍写 `/music/xxx.mp3`，在 `.env.production` 设置 `VITE_MUSIC_BASE=https://cdn.example.com`，构建后请求会指向 CDN |

示例（`src/data/musicTracks.ts`）：

```ts
{ id: 't1', title: '夜航草稿', artist: 'Run', src: 'https://cdn.example.com/blog/music/track1.mp3' }
```

## 2. 版权与内容合规

- 仅上传**你有权公开播放**的音频（原创、已获授权、明确可商用的 CC 等）。
- 不要直接把**未授权的流行歌曲**挂在公网博客上，存在版权与平台下架风险。
- 若只做氛围、不涉及具体曲目，也可用**免版权**素材站（如 Pixabay、Free Music Archive）并保留出处说明。

## 3. Git 与构建体积

建议不要把大体积 mp3 提交进仓库：

```gitignore
public/music/*.mp3
public/music/*.m4a
```

在服务器或 CI 构建前，用脚本/rsync 把音频同步到 `public/music/`，或完全走 CDN URL。

## 4. 部署流程（静态前端）

```bash
npm run build
# 将 dist/ 上传到 Nginx、Vercel、Netlify、GitHub Pages 等
```

Nginx 需对 `/music/` 开启静态文件与合理缓存（示例）：

```nginx
location /music/ {
  alias /var/www/blog/music/;
  expires 7d;
  add_header Cache-Control "public";
}
```

站点请使用 **HTTPS**（多数浏览器对混合内容、部分 API 更严格）。

## 5. 环境变量（可选）

`.env.production`：

```env
# CDN 根地址，不要末尾斜杠
VITE_MUSIC_BASE=https://cdn.example.com

# 默认粒子：sakura | leaf | mixed
VITE_MUSIC_PARTICLE_THEME=mixed
```

## 6. 播放行为说明

- 音乐在浏览器端通过 `<audio>` 播放，**不经过** Spring 后端；公网部署前端即可，与 `localhost:8080` API 无关。
- 用户需**点击播放**（浏览器自动播放策略限制，不能无声自动播）。
- 若 404：检查构建产物里是否有 `dist/music/*.mp3`，或 CDN URL 是否可公网访问、CORS（跨域音频需源站允许）。

## 7. 粒子动效

- 仅在**音乐模式且正在播放**时在「关于我」卡片内显示 Canvas 樱花/落叶。
- 系统开启「减少动态效果」时自动关闭粒子。
- 播放器内可切换「混合 / 樱花 / 落叶」；可开关「歌词」飘落（需同目录 `.lrc` 文件，格式 `[分:秒]歌词`）。
- 每首歌也可在 `manifest.json` 配置 `particleTheme`、`lyricsSrc`。
