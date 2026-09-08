# Contributing to Runtrail

感谢你对 Runtrail 的兴趣！本项目遵循标准的 GitHub Flow。

## 开发环境

```bash
git clone https://github.com/xxx/runtrail.git
cd runtrail
pip install -e ".[dev]"
```

## 提交前检查

```bash
ruff check src tests
pytest --cov=runtrail
```

## Pull Request

1. Fork 仓库，从 `main` 切出功能分支
2. 提交信息遵循 Conventional Commits（`feat:`、`fix:`、`docs:` 等）
3. 确保 CI（lint + test）通过
4. 描述变更动机与测试方式

## 扩展点

新增 Agent / Evaluator / Tool / Dataset / Storage 实现时，请继承 `src/runtrail/*/base.py` 中的抽象基类，不要修改框架核心代码。参见 [docs/extend.md](docs/extend.md)。
