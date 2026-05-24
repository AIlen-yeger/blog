@echo off
setlocal EnableDelayedExpansion

echo === 修复 Git 仓库位置 ===
echo.

set "HOME_GIT=C:\Users\奥利奥\.git"
set "BLOG_DIR=C:\Users\奥利奥\Projects\personal-blog"

if exist "%HOME_GIT%" (
  echo [1/5] 删除误建在用户主目录的 .git ...
  rd /s /q "%HOME_GIT%"
  if errorlevel 1 (
    echo 错误: 无法删除 %HOME_GIT%，请以管理员身份运行或手动删除该文件夹。
    exit /b 1
  )
  echo       已删除 %HOME_GIT%
) else (
  echo [1/5] 用户主目录无 .git，跳过
)

cd /d "%BLOG_DIR%"
if errorlevel 1 (
  echo 错误: 无法进入 %BLOG_DIR%
  exit /b 1
)

if exist ".git" (
  echo [2/5] personal-blog 已有 .git，跳过 init
) else (
  echo [2/5] 在 personal-blog 初始化 Git ...
  git init -b main
  if errorlevel 1 exit /b 1
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo [3/5] 添加 remote origin ...
  git remote add origin https://github.com/AIlen-yeger/blog.git
) else (
  echo [3/5] remote origin 已存在
)

echo [4/5] 提交博客项目文件 ...
git add .
git status
git commit -m "初始化 personal-blog 项目"
if errorlevel 1 (
  echo 提示: 若无新变更，commit 可能失败，可继续 push。
)

echo [5/5] 推送到 GitHub ...
git push -u origin main

echo.
echo === 完成 ===
pause
