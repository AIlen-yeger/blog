# 关于页背景音乐

把 **mp3 / m4a / ogg** 直接放进本目录即可，无需改代码。

## 自动识别

启动或构建时会生成 `manifest.json`（曲目列表）：

```bash
npm run dev
# 或手动：npm run music:sync
```

**文件名建议**：`歌手 - 歌名.mp3`（例如 `米津玄師 - Lemon.mp3`），会自动拆成艺术家与曲名。  
也支持带空格、中文、日文等文件名（如 `Take me hand.mp3`）。

## 歌词飘落（LRC）

与 mp3 **同名** 的 `.lrc` 放在本目录，播放时会随樱花/落叶一起飘落当前歌词，例如：

- `心做し (カバー)-majiko(gequba点com)_77365.mp3`
- `心做し (カバー)-majiko(gequba点com)_77365.lrc`

LRC 格式示例：

```text
[00:15.00]第一句歌词
[00:22.00]第二句歌词
```

播放器里可点 **「歌词」** 开关；没有 LRC 时会用曲名、歌手代替。

修改文件后请 **重启 `npm run dev`**，或再执行 `npm run music:sync`。

公网部署说明见 **`docs/MUSIC-DEPLOY.md`**。
