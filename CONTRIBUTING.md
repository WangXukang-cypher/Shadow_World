# 参与贡献

感谢你愿意改进 Shadow World。Bug 修复、文档、测试、工具与人格体验方面的贡献都很欢迎。

## 开始之前

1. 在 Issue 中搜索是否已经有人报告或讨论相同问题。
2. 较大的功能请先创建 Issue，说明使用场景和大致方案，避免重复投入。
3. 安全漏洞不要提交公开 Issue，请按照 [SECURITY.md](SECURITY.md) 私下报告。

## 本地开发

项目需要 Python 3.12+、Node.js 24 和 `uv`。

```bash
git clone https://github.com/WangXukang-cypher/Shadow_World.git
cd Shadow_World
cp .env.example .env
./scripts/dev.sh
```

如需分别启动前后端，请参考 [README.md](README.md#手动启动)。

## 提交前检查

完整检查可以通过以下命令运行：

```bash
./scripts/test.sh
```

它会依次运行：

- 后端 Ruff 与 pytest；
- OpenAPI 导出和前端类型生成；
- 前端 TypeScript、ESLint、Vitest 与生产构建。

请为行为变化补充相应测试，并确认没有提交 `.env`、数据库、上传文件、API Key 或其他个人数据。

## Pull Request

- 一个 PR 尽量只解决一个明确问题。
- 在描述中说明改动原因、主要实现和验证方式。
- 界面变化请附截图或录屏。
- 如果 API 契约发生变化，请同步生成前端类型并更新相关文档。
- 保留现有分层边界；数据库结构变化必须新增显式 Alembic migration。

提交 PR 即表示你同意以项目的 [MIT License](LICENSE) 发布你的贡献。
