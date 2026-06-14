# netease_minecraft_income_viewer
非常暴力的爬取开发者平台计算自己账户准确收益

用于登录网易我的世界开发者后台，抓取 PE 组件收益数据，生成本地 JSON 数据，并通过 `收益报告.html` 查看账户、月份、每日收益和组件收益明细。

## 文件说明

- `netease_minecraft_income_viewer.py`：主脚本，负责登录、抓取收益、生成 JSON、打开报告页面。
- `accounts_config.py`：账号配置文件，存放要查询的网易账号和密码。
- `收益报告.html`：本地收益报告页面。
- `report_data/`：脚本生成的收益 JSON 数据目录。

## 环境要求

建议使用 Python 3.11 或兼容版本。

需要安装 Google Chrome 浏览器，以及浏览器对应版本的 ChromeDriver。

安装 Python 依赖：

```bash
pip install matplotlib beautifulsoup4 lxml selenium splinter
```

## 安装 ChromeDriver

脚本使用浏览器自动登录和访问后台接口，因此需要 ChromeDriver。

1. 打开 Chrome 浏览器，查看浏览器版本。
   - 地址栏输入：`chrome://settings/help`
   - 例如版本是 `120.0.xxxxxxx`，则需要下载 `120.0` 对应版本的 ChromeDriver。

2. ChromeDriver 下载地址：

```text
https://googlechromelabs.github.io/chrome-for-testing/#stable
```

3. 下载后解压，将压缩包里的 `chromedriver.exe` 放到 Python 安装目录根目录，或者放到系统 `PATH` 环境变量中。

示例：

```text
C:\Python311\chromedriver.exe
```

也可以下载专门用于测试的 Chrome，避免日常浏览器自动更新后 ChromeDriver 版本不匹配。这个方案需要自行配置和研究。

## 配置账号

打开 `accounts_config.py`，按下面格式添加账号：

```python
ACCOUNTS = [
    {
        "account": "你的邮箱账号",
        "password": "你的密码",
    },
    {
        "account": "另一个邮箱账号",
        "password": "另一个密码",
    },
]
```

账号数量不固定，可以任意增加或删除。脚本启动后会自动列出所有账号，并让你输入序号选择。

注意：`accounts_config.py` 包含明文密码。如果要上传到 GitHub，建议不要提交真实账号密码。可以改成示例账号，或者自行把真实配置加入 `.gitignore`。

## 运行脚本

在项目目录下运行：

```bash
python netease_minecraft_income_viewer.py
```

脚本会依次询问：

1. 查询年份
2. 查询类型
   - `1`：单月查询
   - `2`：多月查询
3. 查询月份或月份范围
4. 要使用的账号序号

示例：

```text
请输入查询年份: 2026
请选择查询类型（1=单月查询，2=多月查询）: 1
请输入查询月份: 6
请选择账号:
1. example1@example.com
2. example2@example.com
请输入账号序号: 1
```

## 查看报告

脚本运行完成后会生成或更新：

```text
report_data/index.json
report_data/账号_年份_月份.json
```

然后打开：

```text
收益报告.html
```

如果页面无法自动读取本地 JSON，请点击页面右上角的“选择 report_data 文件夹”，选择项目里的 `report_data` 目录。

## 常见问题

### ChromeDriver 版本不匹配

如果运行时报 ChromeDriver 相关错误，通常是 Chrome 浏览器版本和 ChromeDriver 版本不一致。

解决方法：

1. 查看 Chrome 版本。
2. 下载对应版本的 ChromeDriver。
3. 替换旧的 `chromedriver.exe`。

### 登录页面出现验证码或二次确认

脚本会尝试自动登录。如果遇到验证码、二维码、二次确认或页面结构变化，需要在打开的浏览器窗口中手动完成登录，然后回到终端按回车继续。

### 报告页面没有数据

检查：

- `report_data/index.json` 是否存在。
- `report_data` 目录里是否有对应账号和月份的 JSON 文件。
- 页面是否选择了正确的账号和月份。
