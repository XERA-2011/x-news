# X-Worker

🚀 高性能、支持 CORS 与访问密钥校验的 **Cloudflare Worker 通用 HTTP API 代理中继服务**。

---

## 📌 项目特性

- ⇄ **双模式代理**：支持 `X-Target-URL` Header 模式与 `?url=` URL 查询参数模式。
- 🛡️ **安全密钥保护 (可选)**：通过设置环境变量 `SECRET_KEY` 即可防范未经授权的滥用。
- 🌐 **全量 CORS 支持**：自动处理浏览器 `OPTIONS` 跨域预检，前端可直接无缝调用。
- ⚡ **请求头清洗与防盗链伪造**：自动过滤代理内部 Header，补全 `User-Agent` 与 `Referer`。
- 📦 **开箱即用**：适配 Cloudflare Workers GitHub 自动联部署与 Wrangler CLI。

---

## 🚀 部署步骤 (Deploy)

### 方式 A：GitHub 关联 Cloudflare 自动部署 (推荐)

1. **推送代码到 GitHub**：
   将本项目代码推送到你的 GitHub 仓库（例如 `https://github.com/your-username/x-worker`）。

2. **在 Cloudflare Dashboard 导入**：
   - 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)。
   - 导航至 **Workers & Pages** -> **Create Application**。
   - 选择 **Pages** 或 **Workers** 中的 **Connect to Git** 标签页。
   - 关联你的 GitHub 账户并选择 `x-worker` 仓库。
   - 部署入口文件填 `src/index.js`，点击 **Save and Deploy** 即可！

### 方式 B：使用 Wrangler 命令行部署

```bash
# 安装依赖
npm install

# 本地调试预览
npm run dev

# 一键部署至 Cloudflare Workers
npm run deploy
```

---

## 📖 API 使用说明 (Usage)

部署完成后，你将获得形如 `https://x-worker.your-subdomain.workers.dev`（或已绑定自定义域名 `https://proxy.xera.cc.cd`）的服务地址。

### 1. URL 参数模式 (Query Mode)

适合在浏览器、简单 Curl 或前端中直接使用：

```bash
curl "https://x-worker.your-subdomain.workers.dev/?url=https://fundf10.eastmoney.com/zcpz_019172.html"
```

---

### 2. Header 传递模式 (Header Mode - 推荐)

适合 Python `requests`、AKShare 拦截代理或后端程序使用：

```bash
curl -H "X-Target-URL: https://fundf10.eastmoney.com/zcpz_019172.html" \
     "https://x-worker.your-subdomain.workers.dev"
```

---

### 3. 在 Python 中拦截 API / AKShare 调用示例

```python
import requests

WORKER_URL = "https://x-worker.your-subdomain.workers.dev"

# 示例：通过代理抓取页面
resp = requests.get(
    WORKER_URL,
    headers={"X-Target-URL": "https://fundf10.eastmoney.com/zcpz_019172.html"}
)
print(resp.status_code, resp.text[:200])
```

---

## 🔒 开启访问密钥保护 (Optional)

若想防止他人盗用你的 Worker 额度，可以在 Cloudflare Workers 设置中添加变量：

* **变量名**: `SECRET_KEY`
* **值**: `your-custom-secret-token`

设置后，发起的每个请求必须带有 Header：
```http
X-Proxy-Secret: your-custom-secret-token
```
否则 Worker 将返回 `401 Unauthorized`。

---

## 📄 开源协议

[MIT License](LICENSE)
