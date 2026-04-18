# GitHub 发布与拉取操作指南（VS Code）

## 1. 发布前准备
1. 安装 Git 并配置身份：
```powershell
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub邮箱"
```

2. 生成并配置 SSH Key（推荐）：
```powershell
ssh-keygen -t ed25519 -C "你的GitHub邮箱"
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```
将公钥复制到 GitHub -> `Settings` -> `SSH and GPG keys`。

3. 在 VS Code 打开项目根目录：`d:\shop`。

## 2. 首次发布到你的 GitHub 仓库

### 2.1 在 GitHub 新建空仓库
- 建议仓库名：`shop`
- 不勾选 Initialize with README（避免冲突）

### 2.2 本地初始化并推送
在 VS Code 终端执行：
```powershell
cd d:\shop
git init
git add .
git commit -m "feat: first iteration baseline"
git branch -M main
git remote add origin git@github.com:<你的用户名>/<你的仓库名>.git
git push -u origin main
```

> 若你使用 HTTPS remote：
```powershell
git remote add origin https://github.com/<你的用户名>/<你的仓库名>.git
```

## 3. 迭代版本发布（推荐流程）

### 3.1 拉取远端最新
```powershell
git pull --rebase origin main
```

### 3.2 提交本次变更
```powershell
git add .
git commit -m "feat(iter1): complete iteration-1 and test artifacts"
git push origin main
```

### 3.3 打 Tag（版本号）
```powershell
git tag -a v1.0.0-iter1 -m "Iteration 1 release"
git push origin v1.0.0-iter1
```

## 4. 从 GitHub 拉取到新机器

```powershell
git clone git@github.com:<你的用户名>/<你的仓库名>.git
cd <你的仓库名>
git checkout main
```

拉取指定版本：
```powershell
git fetch --tags
git checkout tags/v1.0.0-iter1
```

## 5. 常用 Git 操作（高频）

### 5.1 查看状态与历史
```powershell
git status
git log --oneline --decorate --graph -20
```

### 5.2 查看文件改动
```powershell
git diff
git diff --staged
```

### 5.3 撤销未提交改动（谨慎）
```powershell
git restore <文件路径>
```

### 5.4 新建分支开发
```powershell
git checkout -b feat/xxx
```

### 5.5 合并分支到 main
```powershell
git checkout main
git pull --rebase origin main
git merge feat/xxx
git push origin main
```

## 6. VS Code 内操作建议
1. 左侧 Source Control 查看改动，先做一次人工检查。
2. Commit message 建议规范：
- `feat:` 新功能
- `fix:` 缺陷修复
- `docs:` 文档
- `test:` 测试
- `refactor:` 重构
3. 重大版本一定打 Tag，便于回滚和对比。

## 7. 发版检查清单（建议）
1. 前后端可启动并通过核心冒烟。
2. 文档更新：需求文档、测试用例、测试报告。
3. `.env`、密钥等敏感信息未提交到仓库。
4. `git status` 干净后再打 Tag。

## 8. 常见问题

### Q1：`remote origin already exists`
```powershell
git remote remove origin
git remote add origin git@github.com:<你的用户名>/<你的仓库名>.git
```

### Q2：推送被拒绝（non-fast-forward）
```powershell
git pull --rebase origin main
git push origin main
```

### Q3：SSH 认证失败
- 检查是否添加公钥到 GitHub。
- 检查本机 SSH Agent 是否加载私钥。

### Q4：误提交敏感信息
1. 立即修改密钥。
2. 删除仓库历史中的敏感内容（必要时重建仓库）。

---

最后建议：第一迭代发布时，至少保留一个稳定 Tag（如 `v1.0.0-iter1`），后续所有修复走 `v1.0.1-iter1-hotfix*` 体系。
