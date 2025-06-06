# X-NEWS

## 每日新闻，邮箱推送

[![Python Version](https://img.shields.io/badge/python-3.1%2B-blue)]()

- [News API](https://newsapi.org/) 新闻获取
- [Gemini](https://ai.google.dev/)
- `Python SMTP` 发送邮件
- `Github Actions` 每日执行

## 注意
- 本项目仅供学习和研究使用，请勿用于商业用途。
- 推荐使用：官方的邮件订阅新闻
- [Reuters 邮件订阅](https://www.reuters.com/newsletters/)
- [Bloomberg 中文版 邮件订阅](https://www.bloomberg.com/account/newsletters/china-markets?taid=6840d8afb471da0001cc82f5&utm_campaign=trueanthem&utm_content=business&utm_medium=social&utm_source=twitter)

## 开发指南

### 环境准备

首先，创建并激活 Python 虚拟环境：
```bash
# Python 3.3+ 内置 venv

# 创建并激活虚拟环境（Windows）
python -m venv .venv
.venv\Scripts\activate

# 或 macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

这样可以确保项目依赖被安装在虚拟环境中，避免影响全局 Python 环境。

### 安装依赖

更新包管理工具并安装项目依赖：

```bash
# 更新 pip 和相关工具
python -m pip install --upgrade pip setuptools wheel

# 安装项目依赖
python -m pip install -r requirements.txt
```

## 配置与运行

### 环境配置

在项目根目录创建 `.env` 文件，配置必要的环境变量：
参考 `.env.example` 示例文件

### 运行程序

1. 首先运行测试脚本确保配置正确：

```bash
python test.py
```

2. 测试通过后运行主程序：

```bash
python main.py
```

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。
