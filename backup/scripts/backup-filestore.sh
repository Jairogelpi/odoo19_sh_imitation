#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <source_filestore_dir> <backup_dir>"
  exit 1
fi

source_dir="$1"
backup_dir="$2"
timestamp="$(date +%Y%m%d-%H%M%S)"
archive_path="${backup_dir}/filestore-${timestamp}.tar.gz"

mkdir -p "$backup_dir"
tar -czf "$archive_path" -C "$source_dir" .

echo "Filestore backup created at: $archive_path"
