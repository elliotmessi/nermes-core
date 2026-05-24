#!/usr/bin/env python3
"""每周五自动同步 Hermes Agent 上游。

策略：
  1. fetch upstream/main
  2. 如果没有新 commit → 退出
  3. 创建 sync/upstream-YYYYMMDD 分支
  4. 尝试 merge
  5. 无冲突 → 品牌修复 → 汉化扫描 → commit → merge 回 main → push
  6. 有冲突 → 保存状态，通知用户手动处理
"""

import subprocess
import sys
import os
from datetime import datetime

REPO = os.path.expanduser("~/projects/nermes-core")
SCRIPTS = os.path.join(REPO, "scripts")
TODAY = datetime.now().strftime("%Y%m%d")
BRANCH = f"sync/upstream-{TODAY}"


def run(cmd, cwd=REPO):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_script(name):
    """运行 scripts/ 下的脚本。"""
    path = os.path.join(SCRIPTS, name)
    if os.path.exists(path):
        rc, out, err = run(f"python3 {path}")
        if rc != 0 and err:
            print(f"⚠️  {name} 警告: {err[:200]}")
        return out
    return ""


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
        return

    print(f"📦 上游新增 {count} 个 commit\n")

    # 3. 创建同步分支
    run(f"git checkout -b {BRANCH}")

    # 4. 尝试 merge
    rc, out, err = run("git merge upstream/main --no-edit")
    
    if rc != 0:
        conflict_files = subprocess.run(
            "git diff --name-only --diff-filter=U",
            shell=True, cwd=REPO, capture_output=True, text=True
        ).stdout.strip()
        
        print(f"⚠️  合并有冲突！共 {len(conflict_files.split(chr(10)))} 个文件：")
        print(conflict_files)
        print(f"\n🛑 需要手动处理。分支已保留在 {BRANCH}")
        print("   处理完成后运行：")
        print(f"   git checkout main && git merge {BRANCH} && git push origin main")
        sys.exit(1)
    
    # 5. 无冲突 — 三步后处理
    print("✅ 无冲突合并\n")
    
    # 5a. 品牌修复：Hermes → Nermes
    print("🔧 品牌修复（Hermes → Nermes）...")
    brand_output = run_script("fix_upstream_brand.py")
    if brand_output:
        print(brand_output)
    print()
    
    # 5b. 汉化扫描：检测新增英文文案
    print("🔍 汉化扫描...")
    i18n_output = run_script("scan_and_localize.py")
    print(i18n_output)
    print()
    
    # 6. 确认是否有实际变更需要提交
    rc, diff_stat, _ = run("git diff --stat")
    if not diff_stat:
        print("ℹ️  没有需要提交的变更（上游无新文案或代码未变）。")
        # 切换回 main 并清理
        run("git checkout main")
        run(f"git branch -D {BRANCH}")
        return
    
    # 7. Commit
    summary = f"sync: 自动合并 Hermes Agent 上游 {TODAY} ({count} commits)"
    rc, out, err = run(f'git add -A && git commit -m "{summary}"')
    
    if rc != 0:
        print(f"❌ 提交失败: {err}")
        sys.exit(1)
    
    print(f"📝 {summary}")
    
    # 8. 合并回 main 并推送
    run("git checkout main")
    merge_rc, merge_out, merge_err = run(f"git merge {BRANCH}")
    if merge_rc != 0:
        print(f"❌ 合并回 main 失败: {merge_err}")
        sys.exit(1)
    
    push_rc, push_out, push_err = run("git push origin main")
    if push_rc != 0:
        print(f"❌ 推送失败: {push_err}")
        sys.exit(1)
    
    # 9. 清理
    run(f"git branch -d {BRANCH}")
    
    print(f"\n🎉 同步完成！{count} 个上游 commit 已合并到 main。")
    print(f"   品牌修复 + 汉化扫描均已完成。")


if __name__ == "__main__":
    main()
