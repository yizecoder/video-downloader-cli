# Video Downloader CLI

[![CI](https://github.com/yizecoder/video-downloader-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/yizecoder/video-downloader-cli/actions/workflows/ci.yml)

Windows 优先的视频与音频下载工具。默认下载平台返回的最高可用画质，也可提取
MP3，并支持严格的最低画质检查。

> 本工具不绕过 DRM、付费墙或平台访问控制。请只下载你有权访问和保存的内容，
> 并遵守当地法律、版权规则和目标平台条款。

## 功能

- B站、YouTube、抖音、小红书及 yt-dlp 支持的其他公开网站
- 最高可用画质，自动合并独立的视频流和音频流
- MP3 音频提取
- `720p`、`1080p`、`4k` 严格最低画质，不满足时停止
- 单链接、批量和 Windows 交互模式
- 抖音分享短链、`/video/ID` 和 `/jingxuan?modal_id=ID`
- Windows 长中文文件名兼容处理
- B站与 YouTube Cookie 完全隔离

本项目不包含 Whisper 转写、AI 摘要或 Markdown 导出。

## 平台支持

| 平台 | 视频 | MP3 | 严格画质 | Cookie |
|---|---:|---:|---:|---|
| B站 | 是 | 是 | 是 | 1080P、4K 或受限内容通常需要 |
| YouTube | 是 | 是 | 是 | 普通公开视频通常不需要 |
| 抖音 | 是 | 是 | 是 | 视平台返回结果而定 |
| 小红书 | 是 | 是 | 是 | 视平台返回结果而定 |
| 其他 yt-dlp 网站 | 视站点 | 视站点 | 是 | 视站点而定 |

平台接口会变化，表格表示当前实现能力，不保证每个链接永久可下载。

## 目录结构

```text
video-downloader-cli/
├── main.py                         # 稳定命令入口
├── start.bat                       # Windows 双击启动
├── video_downloader/
│   ├── cli.py                      # 参数、交互和环境检查
│   ├── config.py                   # 平台隔离配置
│   ├── core.py                     # 下载路由
│   ├── models.py                   # 结构化下载结果
│   ├── utils.py                    # URL、画质、Cookie 工具
│   └── adapters/
│       ├── bilibili.py             # B站公开接口适配器
│       └── ytdlp.py                # yt-dlp 平台适配器
├── tests/                          # 无真实网络请求的单元测试
└── scripts/prepublish_check.py     # 发布前敏感信息检查
```

## 安装

要求：

- Windows 10/11
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html)，并加入 `PATH`

```powershell
python -m pip install -r requirements.txt
python main.py --check
```

FFmpeg 是外部依赖，本项目不捆绑或重新分发 FFmpeg。

## 使用

双击 `start.bat` 可进入交互模式。脚本只负责切换目录、设置 UTF-8、检查 Python
并启动程序，因此标题只显示一次。

```powershell
# 最高可用画质
python main.py "https://www.bilibili.com/video/BV..."

# 仅下载 MP3
python main.py "https://www.youtube.com/watch?v=..." --audio

# 至少 1080P，拿不到就停止
python main.py "https://..." --min-quality 1080p

# 至少 4K
python main.py "https://..." --min-quality 4k

# 批量视频
python main.py --batch "URL1" "URL2"

# 批量 MP3
python main.py --batch "URL1" "URL2" --audio
```

默认输出到 `downloads/`。视频文件名会标记实际清晰度，例如 `_1080P.mp4`、
`_1440P.mp4` 或 `_4K.mp4`。

## 画质规则

`best` 表示平台当前返回的最高可用版本，不等于固定 1080P。视频本身、账号权限、
地区和平台接口都会影响结果。

`--min-quality 1080p` 和 `--min-quality 4k` 是严格模式。实际最高画质不足时，
程序会在下载前停止，不会静默降级。抖音原视频如果最高只有 720P，选择“最高可用”
可以下载 720P；选择“至少 1080P”会报错，这是预期行为。

## Cookie

Cookie 等同登录凭据，不要上传、分享、截图或提交到 Git。

### 推荐导出方式

推荐仅从[官方 Chrome Web Store 页面](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
安装 **Get cookies.txt LOCALLY**。该扩展开源并声明 Cookie 只在本地处理，可检查其
[GitHub 源码](https://github.com/kairi003/Get-cookies.txt-LOCALLY)，但本项目不对
任何第三方扩展作绝对安全担保。

不要误装名称相似的旧版 **Get cookies.txt**。旧版同名扩展曾被公开报告存在恶意
行为。请核对扩展完整名称、商店链接和发布者。

导出步骤：

1. 登录目标平台并打开该平台页面。
2. 在扩展中导出 **Netscape** 格式，不要选择 JSON。
3. B站文件重命名为 `space.bilibili.com_cookies.txt`。
4. 将文件放入项目根目录，运行 `python main.py --check`。

项目只提供格式示例 `space.bilibili.com_cookies.example.txt`，不提供真实 Cookie。

### B站

B站默认自动读取项目根目录：

```text
space.bilibili.com_cookies.txt
```

可以直接把该文件放在项目根目录，程序会自动读取，`.gitignore` 会阻止正常提交。
只有希望把 Cookie 存放在项目外部时才需要设置：

```powershell
setx BILIBILI_COOKIES_FILE "E:\private\bilibili-cookies.txt"
```

也可尝试读取浏览器 Cookie，但 Chrome 新版可能受 DPAPI 或数据库锁影响：

```powershell
setx BILIBILI_COOKIE_BROWSER edge
```

更推荐 Netscape Cookie 文件。

### YouTube

普通公开视频通常不需要 Cookie。遇到登录、人机验证或年龄限制时，单独导出
YouTube Cookie：

```powershell
setx YOUTUBE_COOKIES_FILE "E:\private\youtube-cookies.txt"
```

B站 Cookie 永远不会自动传给 YouTube。项目不再识别通用的 Cookie 环境变量，
避免一个平台的登录凭据被误传给另一个平台。

`setx` 会永久写入当前 Windows 用户环境变量，新终端和重新打开的 `start.bat`
才会读取新值。临时测试可在当前 PowerShell 使用：

```powershell
$env:YOUTUBE_COOKIES_FILE = "E:\private\youtube-cookies.txt"
```

## 代理与输出目录

```powershell
setx VIDEO_PROXY "http://127.0.0.1:7890"
setx DOWNLOAD_DIR "E:\Videos"
```

代理当前用于 YouTube 下载。不要把含用户名和密码的代理 URL 提交到仓库。

| 环境变量 | 默认值 | 作用 |
|---|---|---|
| `BILIBILI_COOKIES_FILE` | 项目根目录默认文件 | B站 Netscape Cookie |
| `YOUTUBE_COOKIES_FILE` | 未配置 | YouTube Netscape Cookie |
| `BILIBILI_COOKIE_BROWSER` | 未配置 | B站浏览器 Cookie 来源 |
| `VIDEO_PROXY` | 未配置 | YouTube 网络代理 |
| `DOWNLOAD_DIR` | `downloads/` | 下载目录 |

## 常见错误

### `Failed to decrypt with DPAPI`

Chrome Cookie 使用了应用绑定加密。改用 Get cookies.txt LOCALLY 导出的 Netscape
文件，不要继续读取 Chrome 数据库。

### `Could not copy ... cookie database`

浏览器仍占用 Cookie 数据库。完全退出浏览器，或改用 Netscape Cookie 文件。

### `Requested format is not available`

平台没有返回所选最低画质。改选 `best`，或降低 `--min-quality`。

### YouTube 要求登录

先确认浏览器能播放该视频；确实需要登录时配置 `YOUTUBE_COOKIES_FILE`，不要配置
B站 Cookie。

## 开发与测试

```powershell
python -m pip install -r requirements-dev.txt
python -m compileall -q main.py video_downloader tests scripts
python -m unittest discover -s tests -v
ruff check .
python scripts\prepublish_check.py
python -m pip check
```

CI 在 Windows 上覆盖 Python 3.10 和较新稳定版本，单元测试使用模拟数据，不访问
真实视频网站。真实平台验证只在发布前手工执行。

## 隐私与安全

- `--check` 只显示 Cookie 路径、格式和是否存在登录态，不输出 Cookie 值。
- 默认真实 Cookie 文件、下载目录和环境文件均被 `.gitignore` 忽略。
- 发布前运行 `scripts/prepublish_check.py`。
- Cookie 一旦泄露，应立即退出平台所有会话或刷新登录状态。仅删除本地文件不能让
  已泄露的 Cookie 失效。

安全问题请参考 [SECURITY.md](SECURITY.md)。

## 许可证与第三方组件

本项目采用 [MIT License](LICENSE)。

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)主体主要采用 Unlicense，仓库内部分组件
  可能有各自许可证。
- [FFmpeg](https://www.ffmpeg.org/legal.html)通常采用 LGPL 2.1+；构建时启用部分
  可选组件后可能适用 GPL。请以你实际安装的 FFmpeg 构建配置为准。
