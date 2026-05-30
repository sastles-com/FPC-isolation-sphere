#!/usr/bin/env bash
# Upload web/output/ files to Lolipop FTP server.
# Credentials are read from .ftp_credentials (gitignored).
#
# Usage:
#   shell-cad/scripts/upload_to_lolipop.sh                  # upload all
#   shell-cad/scripts/upload_to_lolipop.sh path/to/file.html # upload one file

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CREDS="$REPO_ROOT/.ftp_credentials"

if [[ ! -f "$CREDS" ]]; then
  echo "❌  .ftp_credentials not found. Copy .ftp_credentials.example and fill in FTP_PASS."
  exit 1
fi

# shellcheck disable=SC1090
source "$CREDS"

upload_file() {
  local local_path="$1"
  local rel_path="${local_path#"$REPO_ROOT"/}"   # strip repo root prefix
  local remote_url="ftp://${FTP_HOST}/${FTP_PROJECT_ROOT}/${rel_path}"

  echo "  ↑ ${rel_path}"
  curl --silent --show-error \
       -T "$local_path" \
       "$remote_url" \
       --user "${FTP_USER}:${FTP_PASS}" \
       --ftp-create-dirs
}

if [[ $# -ge 1 ]]; then
  # Single file mode
  upload_file "$1"
else
  # Bulk mode: upload everything under web/output/
  WEB_DIR="$REPO_ROOT/web/output"
  if [[ ! -d "$WEB_DIR" ]]; then
    echo "❌  $WEB_DIR does not exist. Run generate_stl_viewer.py first."
    exit 1
  fi

  echo "Uploading $WEB_DIR → ftp://${FTP_HOST}/${FTP_PROJECT_ROOT}/web/output/"
  while IFS= read -r -d '' file; do
    upload_file "$file"
  done < <(find "$WEB_DIR" -type f \( -name "*.html" -o -name "*.stl" \) -print0)

  echo "✅  Done.  Public URL: ${FTP_BASE_URL}/web/output/"
fi
