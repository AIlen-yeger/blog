# Q 版桌宠素材

## 重要：请用 PNG，不要用 JPG

扣图后若保存为 **JPG**，透明区域会变成**白色或灰色底**，在深色页面上会像一块「贴纸底板」。

请从 `图片/q版桌宠` 导出为 **PNG 透明背景**，放入本目录：

| 文件名 | 说明 |
|--------|------|
| `idle.png` | 常态 / 待机（原 `1.jpg`） |
| `happy.png` | 开心动作（原 `2.jpg`） |

仍可使用 `idle.jpg` / `happy.jpg` 作为回退，但会有底色。

**切换不跳动：** 页面会把所有立绘放进固定舞台（112×168px），脚底对齐、高度拉满；若两张图人物大小仍不一致，可在 `src/data/desktopPetSprites.ts` 里给某张图加 `fitScale: 0.95` 等微调。

复制示例（PowerShell）：

```powershell
$src = "$env:USERPROFILE\Pictures\q版桌宠"
$dst = ".\public\desktop-pet"
Copy-Item -LiteralPath "$src\1.png" -Destination "$dst\idle.png" -ErrorAction SilentlyContinue
Copy-Item -LiteralPath "$src\2.png" -Destination "$dst\happy.png" -ErrorAction SilentlyContinue
# 若只有 jpg，先复制 jpg，再用画图/PS 另存为 png 透明底
Copy-Item -LiteralPath "$src\1.jpg" -Destination "$dst\idle.jpg" -ErrorAction SilentlyContinue
Copy-Item -LiteralPath "$src\2.jpg" -Destination "$dst\happy.jpg" -ErrorAction SilentlyContinue
```
