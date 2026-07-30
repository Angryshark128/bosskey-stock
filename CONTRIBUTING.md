# Contributing

欢迎贡献！无论是修 Bug、加功能、改进文档，还是提 Issue，都感谢你的时间。

## 开发环境

```bash
git clone <your-fork>
cd astock
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 代码风格

本项目使用 [ruff](https://docs.astral.sh/ruff/) 进行格式化和 lint：

```bash
pip install ruff
ruff check astock/
ruff format astock/
```

提交前请确保无 lint 错误。

## 测试

```bash
pip install pytest
pytest
```

测试文件在 `tests/` 目录，涵盖数据解析、配置管理、老板模式等核心逻辑。

## 提 PR

1. Fork 仓库并创建你的功能分支（`git checkout -b feat/my-feature`）。
2. 提交改动（`git commit -am 'Add my feature'`）。
3. 确保测试通过且 lint 无报错。
4. Push 到你的分支并创建 PR。

## Issue 模板

- **Bug 报告**：请描述复现步骤、预期行为、实际行为、环境信息（OS、Python 版本）。
- **功能请求**：请描述你想解决的问题和使用场景。

## 发布流程（维护者）

```bash
# 1. 更新版本号
# 2. 更新 CHANGELOG.md
# 3. 打 tag
git tag v0.2.0
git push --tags
# 4. 发布到 PyPI
pip install build twine
python -m build
twine upload dist/*
```
