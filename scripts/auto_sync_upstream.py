#!/usr/bin/env python3
"""每周五自动同步 Hermes Agent 上游。

策略：
  1. fetch upstream/main
  2. 如果没有新 commit → 退出
  3. 创建 sync/upstream-YYYYMMDD 分支
  4. 尝试 merge
  5. 无冲突 → 汉化扫描 + 品牌修复 + commit + merge 回 main + push
  6. 有冲突 → 保存状态，通知用户手动处理
"""

import subprocess
import sys
import os
from datetime import datetime

REPO = os.path.expanduser("~/projects/nermes-core")
TODAY = datetime.now().strftime("%Y%m%d")
BRANCH = f"sync/upstream-{TODAY}"


def run(cmd, cwd=REPO):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def main():
    print(f"=== Nermes 上游同步 {TODAY} ===\n")

    # 0. 确保在 main 且最新
    rc, out, err = run("git checkout main && git pull origin main")
    if rc != 0:
        print(f"❌ 无法切换到 main: {err}")
        sys.exit(1)

    # 1. Fetch upstream
    rc, out, err = run("git fetch upstream main")
    if rc != 0:
        print(f"❌ 无法 fetch upstream: {err}")
        sys.exit(1)

    # 2. 检查是否有新 commit
    rc, count, _ = run("git rev-list --count main..upstream/main")
    if rc != 0 or int(count) == 0:
        print("✅ 没有新的上游 commit，无需同步。")
        return "no_new_commits"

    print(f"📦 上游新增 {count} 个 commit\n")

    # 3. 创建同步分支
    run(f"git checkout -b {BRANCH}")

    # 4. 尝试 merge
    rc, out, err = run("git merge upstream/main --no-edit")
    
    if rc != 0:
        # 有冲突！
        conflict_files = subprocess.run(
            "git diff --name-only --diff-filter=U",
            shell=True, cwd=REPO, capture_output=True, text=True
        ).stdout.strip()
        
        print(f"⚠️  合并有冲突！共 {len(conflict_files.split(chr(10)))} 个文件：")
        print(conflict_files)
        print("\n🛑 需要手动处理。分支已保留在 sync/upstream-{TODAY}")
        print("   处理完成后运行：")
        print(f"   git checkout main && git merge {BRANCH} && git push origin main")
        sys.exit(1)
    
    # 5. 无冲突 — 自动汉化扫描 + 品牌修复
    print("✅ 无冲突合并\n")
    
    # 运行品牌修复脚本
    fix_script = os.path.join(REPO, "scripts/fix_upstream_brand.py")
    if os.path.exists(fix_script):
        run(f"python3 {fix_script}")
    
    # 6. Commit
    rc, out, _ = run(
        f'git add -A && git commit -m "sync: 自动合并 Hermes Agent 上游 {TODAY} ({count} commits)"'
    )
    
    if rc != 0:
        # 可能没有需要 commit 的内容
        print("ℹ️  没有需要提交的变更")
    
    # 7. 合并回 main 并推送
    run("git checkout main")
    run(f"git merge {BRANCH}")
    run("git push origin main")
    
    # 8. 清理
    run(f"git branch -d {BRANCH}")
    
    print(f"\n🎉 同步完成！{count} 个上游 commit 已合并到 main。")


if __name__ == "__main__":
    result = main()
    print(f"\n=== 结果: {result} ===")
