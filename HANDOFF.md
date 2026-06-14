---
project: video-downloader-cli
updated: 2026-06-14
status: active
---

# 任务交接

## 已完成

- 增加项目级 `AGENTS.md`，明确目录边界、命令、风格和凭据规则。
- 增加 `PROJECT.md`，记录目标、架构、状态和下一步。
- 将项目登记到工作区 `workspace.yaml` 和知识库项目索引。

## 当前状态

- 分支：`main`，跟踪 `origin/main`
- 本次仅增加工作系统文档，没有修改下载逻辑。
- 真实 Cookie 和下载文件仍由现有 `.gitignore` 与发布前检查保护。

## 验证结果

2026-06-14 已通过：

```powershell
python -m unittest discover -s tests -v  # 36 tests
ruff check .
python scripts\prepublish_check.py
python main.py --check
```

基础环境、FFmpeg、yt-dlp、Node 运行时和 B站 Cookie 格式检查正常。

## 未完成与风险

- GitHub CLI 当前未登录，本次工作系统实施不包含远程推送。
- 平台接口和登录挑战仍可能变化，应以可复现链接和错误信息驱动修复。

## 下一步入口

处理项目前先阅读 `AGENTS.md` 和 `PROJECT.md`，然后运行：

```powershell
git status --short --branch
python -m unittest discover -s tests -v
```
