---
project: video-downloader-cli
status: active
updated: 2026-06-14
repository: https://github.com/yizecoder/video-downloader-cli
---

# Video Downloader CLI

## 目标

提供 Windows 优先的视频与音频下载 CLI，支持 B站、YouTube、抖音、小红书以及
yt-dlp 可处理的其他公开网站。

## 当前状态

- 主分支：`main`
- 已公开发布，当前本地分支跟踪 `origin/main`
- 支持最高可用画质、MP3、严格最低画质、批量与交互模式
- Cookie 与下载文件仅保留在本地，不进入版本控制

## 架构与入口

- `main.py`：稳定入口
- `video_downloader/cli.py`：命令行和环境检查
- `video_downloader/core.py`：下载路由
- `video_downloader/adapters/`：平台适配
- `tests/`：离线单元测试

## 开发命令

```powershell
python -m unittest discover -s tests -v
ruff check .
python scripts\prepublish_check.py
python main.py --check
```

## 已知风险

- 平台接口、登录挑战和 Cookie 格式会变化。
- 项目目录含真实本地 Cookie，任何提交前必须检查跟踪文件。
- 下载、模型和浏览器配置不得进入 Git。

## 下一步

以 Issue、用户反馈和平台变化为依据迭代，不在没有复现证据时扩展平台特例。
