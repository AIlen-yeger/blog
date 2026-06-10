@echo off
setlocal
cd /d "%~dp0.."

echo === git status (before) ===
git status --short

git add -u
git add .gitignore
git add backend frontend python
git add scripts/commit-agent-feature.cmd 2>nul

git reset -- python/data/chroma_user_memory 2>nul
git reset -- python/docker/napcat 2>nul
git reset -- "**/__pycache__" 2>nul
git reset -- python/route/__pycache__ 2>nul
git reset -- .cursor 2>nul
git reset -- python/.env 2>nul

echo.
echo === staged ===
git status --short

git commit -m "feat(agent): eval harness, editor overlay, and note publish fixes" -m "- Add Python agent eval harness (golden suites, runner, local-only reports)" -m "- Fix publish-note route, document ingest, and markdown bold rendering" -m "- Editor drawer overlay UI; update note without agent reply" -m "- Fix image upload validation, agent session bridge, publish confirm message"

if errorlevel 1 (
  echo Commit failed or nothing to commit.
  exit /b 1
)

echo.
echo === push ===
git push -u origin HEAD
if errorlevel 1 (
  echo Push failed. Check: git remote -v && git branch -vv
  exit /b 1
)

echo.
echo Done. Commit: 
git rev-parse --short HEAD
endlocal
