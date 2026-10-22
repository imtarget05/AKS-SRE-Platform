#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_SITE_DIR="$REPO_ROOT/docs-site"
SITE_OUTPUT_DIR="$DOCS_SITE_DIR/site"
CONSOLE_SRC="$REPO_ROOT/apps/sre-console/index.html"

echo "==> 1. Building MkDocs documentation site..."
cd "$DOCS_SITE_DIR"
mkdocs build

echo "==> 2. Preserving MkDocs home page to /docs-home/index.html..."
mkdir -p "$SITE_OUTPUT_DIR/docs-home"
cp "$SITE_OUTPUT_DIR/index.html" "$SITE_OUTPUT_DIR/docs-home/index.html"

echo "==> 3. Installing upgraded SRE Console to root / and /console/..."
cp "$CONSOLE_SRC" "$SITE_OUTPUT_DIR/index.html"
mkdir -p "$SITE_OUTPUT_DIR/console"
cp "$CONSOLE_SRC" "$SITE_OUTPUT_DIR/console/index.html"

echo "==> 4. Verifying static assets and routes..."
required_files=(
  "$SITE_OUTPUT_DIR/index.html"
  "$SITE_OUTPUT_DIR/console/index.html"
  "$SITE_OUTPUT_DIR/docs-home/index.html"
  "$SITE_OUTPUT_DIR/architecture/overview/index.html"
  "$SITE_OUTPUT_DIR/evidence/aks-live/index.html"
  "$SITE_OUTPUT_DIR/evidence/test-results/index.html"
  "$SITE_OUTPUT_DIR/evidence/workload-identity/index.html"
  "$SITE_OUTPUT_DIR/runbooks/finops/index.html"
  "$SITE_OUTPUT_DIR/runbooks/incident-response/index.html"
  "$SITE_OUTPUT_DIR/cv-portfolio/index.html"
  "$SITE_OUTPUT_DIR/sitemap.xml"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "ERROR: Required file missing: $file" >&2
    exit 1
  fi
done

echo "==> [SUCCESS] Distribution build verified at: $SITE_OUTPUT_DIR"
