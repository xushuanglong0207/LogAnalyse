# === purge_large_node_binaries_and_force_push.sh ===
set -euo pipefail

# 1) 目标文件（就是 GitHub 报错的俩）
declare -a TARGETS=(
  "frontend/node_modules/@next/swc-linux-x64-gnu/next-swc.linux-x64-gnu.node"
  "frontend/node_modules/@next/swc-linux-x64-musl/next-swc.linux-x64-musl.node"
)

# 2) 记住当前分支 & 暂存工作区改动（filter 会拒绝有脏改动的历史改写）
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if git status --porcelain | grep . >/dev/null; then
  git stash push -m "pre-filter backup $(date +%F_%T)"
  STASHED=1
else
  STASHED=0
fi

# 3) 准备 git-filter-repo（优先使用它；没有的话自动尝试 apt 或 venv）
if git filter-repo -h >/dev/null 2>&1; then
  MODE=repo
elif command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -y
  if sudo apt-get install -y git-filter-repo; then
    MODE=repo
  else
    MODE=venv
  fi
else
  MODE=venv
fi

if [ "$MODE" = venv ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "缺少 python3，无法创建 venv；改用老办法 filter-branch。" >&2
    MODE=branch
  else
    TMPDIR="$(mktemp -d)"
    python3 -m venv "$TMPDIR/venv"
    "$TMPDIR/venv/bin/python" -m pip install --upgrade pip
    "$TMPDIR/venv/bin/python" -m pip install git-filter-repo
    export PATH="$TMPDIR/venv/bin:$PATH"
    MODE=repo
  fi
fi

# 4) 真正清理历史
if [ "$MODE" = repo ]; then
  # 精确移除两个超大文件的所有历史
  for p in "${TARGETS[@]}"; do
    git filter-repo --path "$p" --invert-paths || true
  done
  # 可选：一把梭把整个 node_modules 从历史里抹掉（更干净）
  # git filter-repo --path node_modules --invert-paths
else
  # 老工具 fallback（会慢一些）
  git filter-branch --force --index-filter \
    'git rm --cached --ignore-unmatch '"${TARGETS[0]}"' '"${TARGETS[1]}" \
    --prune-empty --tag-name-filter cat -- --all
fi

# 5) 强推覆盖远端（⚠ 会改写历史）
git push origin "$BRANCH" --force

# 6) 恢复你的工作区改动
if [ "$STASHED" -eq 1 ]; then
  git stash pop || true
fi

echo "✅ 完成：已从历史中清除大文件并强推 $BRANCH。若团队协作，请让同事重新 clone。"

