/**
 * X-Worker - High-performance HTTP API Proxy Forwarder on Cloudflare Workers
 * 
 * 支持两种代理转发触发方式:
 * 1. Request Header 模式: 传入 X-Target-URL: https://target-api.com/path
 * 2. Query Parameter 模式: 请求 https://worker.domain.com/?url=https://target-api.com/path
 */

export default {
  async fetch(request, env, ctx) {
    // 1. 处理 CORS 跨域预检请求 (OPTIONS)
    if (request.method === "OPTIONS") {
      return handleCors();
    }

    const url = new URL(request.url);

    // 2. 解析目标 URL：优先读取 X-Target-URL 请求头，次之读取 ?url= 查询参数
    let targetUrlStr = request.headers.get("X-Target-URL") || url.searchParams.get("url");

    // 访问根节点无目标参数时，返回服务状态与 API 帮助说明
    if (!targetUrlStr) {
      if (url.pathname === "/" || url.pathname === "") {
        return new Response(
          JSON.stringify(
            {
              service: "X-Worker",
              status: "ok",
              description: "Cloudflare Worker HTTP Forwarding Proxy Server",
              usage: {
                via_header: "Add 'X-Target-URL: https://target-api.com/path' to headers",
                via_query: `${url.origin}/?url=https://target-api.com/path`
              },
              example: `${url.origin}/?url=https://fundf10.eastmoney.com/zcpz_019172.html`
            },
            null,
            2
          ),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json; charset=utf-8",
              ...corsHeaders()
            }
          }
        );
      }
      return new Response(
        JSON.stringify({ error: "Missing target URL (X-Target-URL header or ?url= query parameter required)" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json", ...corsHeaders() }
        }
      );
    }

    // 3. 可选的安全访问密钥校验 (若设置了 SECRET_KEY 环境变量)
    if (env && env.SECRET_KEY) {
      const clientSecret = request.headers.get("X-Proxy-Secret");
      if (clientSecret !== env.SECRET_KEY) {
        return new Response(
          JSON.stringify({ error: "Unauthorized: Invalid X-Proxy-Secret" }),
          { status: 401, headers: { "Content-Type": "application/json", ...corsHeaders() } }
        );
      }
    }

    // 4. 校验目标 URL 合法性
    let targetUrl;
    try {
      targetUrl = new URL(targetUrlStr);
    } catch (e) {
      return new Response(
        JSON.stringify({ error: `Invalid Target URL: ${targetUrlStr}` }),
        { status: 400, headers: { "Content-Type": "application/json", ...corsHeaders() } }
      );
    }

    // 5. 复制并清洗请求头（过滤 Cloudflare/代理专用 Header）
    const newHeaders = new Headers();
    for (const [key, value] of request.headers.entries()) {
      const lowerKey = key.toLowerCase();
      if (
        !lowerKey.startsWith("cf-") &&
        !lowerKey.startsWith("x-real-") &&
        lowerKey !== "x-target-url" &&
        lowerKey !== "x-proxy-secret" &&
        lowerKey !== "host"
      ) {
        newHeaders.set(key, value);
      }
    }

    // 补全通用 User-Agent 与 Referer 防止防盗链防护拦截
    if (!newHeaders.has("user-agent")) {
      newHeaders.set(
        "User-Agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      );
    }
    if (!newHeaders.has("referer")) {
      newHeaders.set("Referer", `${targetUrl.protocol}//${targetUrl.hostname}/`);
    }

    // 6. 构造并发送目标 HTTP 请求
    try {
      const fetchOptions = {
        method: request.method,
        headers: newHeaders,
        redirect: "follow"
      };

      // 仅 POST / PUT / PATCH / DELETE 等带请求体的方法传递 Request Body
      if (!["GET", "HEAD"].includes(request.method.toUpperCase())) {
        fetchOptions.body = request.body;
      }

      const response = await fetch(targetUrl.toString(), fetchOptions);

      // 7. 构造 Response 返回 (注入 CORS 响应头)
      const responseHeaders = new Headers(response.headers);
      Object.entries(corsHeaders()).forEach(([k, v]) => responseHeaders.set(k, v));

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ error: `Proxy Request Failed: ${err.message}` }),
        { status: 502, headers: { "Content-Type": "application/json", ...corsHeaders() } }
      );
    }
  }
};

/**
 * 跨域 CORS 响应头配置
 */
function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Target-URL, X-Proxy-Secret, User-Agent"
  };
}

/**
 * 处理 OPTIONS 预检请求
 */
function handleCors() {
  return new Response(null, {
    status: 204,
    headers: corsHeaders()
  });
}
