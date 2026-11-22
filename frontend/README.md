# Shadow World Frontend

Shadow World 的 React 19 + TypeScript 前端，使用 Vite、TanStack Query、Zustand、React Router 和安全 Markdown 渲染。项目总览与完整启动方式请阅读根目录 [README](../README.md)。

## 开发

先启动 `backend`，再运行：

```bash
cd frontend
npm install
npm run dev
```

开发服务器默认位于 <http://127.0.0.1:5173>，并将 `/api` 请求代理到 <http://127.0.0.1:8000>。

## 常用命令

```bash
npm run generate:api  # 根据 backend/openapi.json 生成 API 类型
npm run typecheck     # TypeScript 检查
npm run lint          # ESLint
npm run test          # Vitest
npm run build         # 生产构建
```

生产构建输出到 `frontend/dist`。目录存在时，FastAPI 会直接托管构建产物并支持 SPA 深链。
