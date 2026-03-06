#!/bin/sh

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
export PATH="$PROJECT_ROOT/.tools/bin:$PATH"

echo "PATH updated with $PROJECT_ROOT/.tools/bin"
echo "Available tools:"
echo "  node: $(command -v node || true)"
echo "  npm: $(command -v npm || true)"
echo "  npx: $(command -v npx || true)"
echo "  redis-server: $(command -v redis-server || true)"
echo "  redis-cli: $(command -v redis-cli || true)"
