# x-news

> 基于  `AI` `News API` 的新闻摘要和邮件发送工具
> 项目代码由`AI`生成，仅供学习参考

## dev

首先，为项目创建一个虚拟环境（避免污染全局 Python）：
```bash
# Python 3.3+ 内置 venv

# 创建并激活虚拟环境（Windows）
python -m venv .venv
.venv\Scripts\activate

# 或 macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

这样安装的包都只作用于当前目录下的 .venv，方便不同项目之间隔离。
然后，使用 pip 从 requirements.txt 批量安装：
```bash
# 推荐使用 -m 方式，确保用到的是当前激活环境里的 pip

# 确保包管理与构建工具为最新，以最大化兼容性和安装速度（如确认最新，则可忽略）
python -m pip install --upgrade pip setuptools wheel

python -m pip install -r requirements.txt

```

# 运行

本地运行需要新建 .env 文件，内容如下：
```bash
# .env
NEWS_API_KEY=
OPENAI_API_KEY=
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
EMAIL_USER=
EMAIL_PASSWORD=
TO_EMAIL=
```
执行
```bash
# 建议 先测试是否能连通
python test.py

# 再运行
python main.py
```