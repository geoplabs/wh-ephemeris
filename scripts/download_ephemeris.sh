#!/usr/bin/env bash
set -euo pipefail

# Download a curated set of Swiss Ephemeris files into data/ephemeris/ so
# they are available when building the Docker image.

EPHEMERIS_DIR=${1:-data/ephemeris}
BASE_URL="https://www.astro.com/ftp/swisseph/ephe"

# shellcheck disable=SC2034 # values are URL suffixes used below
FILES=(
  "seas_18.se1"
  "semo_18.se1"
  "sepl_18.se1"
  "de406.eph"
)

mkdir -p "${EPHEMERIS_DIR}"

for file in "${FILES[@]}"; do
  target_path="${EPHEMERIS_DIR}/${file}"
  if [[ -f "${target_path}" ]]; then
    echo "✔ ${file} already exists — skipping"
    continue
  fi

  url="${BASE_URL}/${file}"
  echo "⬇️  Downloading ${file}"
  if curl -fL "${url}" -o "${target_path}.download"; then
    mv "${target_path}.download" "${target_path}"
    echo "✅ Saved ${file}"
    continue
  fi

  # Some mirrors only expose zipped variants. Attempt to download the ZIP and
  # extract the requested file.
  zip_url="${BASE_URL}/${file%.*}.zip"
  echo "   Direct download failed, trying ${zip_url}" >&2
  tmp_zip="${target_path}.zip"
  if curl -fL "${zip_url}" -o "${tmp_zip}"; then
    unzip -p "${tmp_zip}" "${file}" > "${target_path}.download"
    rm -f "${tmp_zip}"
    mv "${target_path}.download" "${target_path}"
    echo "✅ Extracted ${file} from ZIP"
    continue
  fi

  echo "❌ Failed to download ${file}. Please download it manually from ${BASE_URL}" >&2
  exit 1
done

echo "Swiss Ephemeris files available in ${EPHEMERIS_DIR}"
