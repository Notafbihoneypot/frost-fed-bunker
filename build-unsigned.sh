#!/usr/bin/env bash
# Build the UNSIGNED ARM64 Frost Fed Bunker release APK:
# pinned upstream Keep Android + Keep Rust core, plus patches/*.patch.
# Needs: git, JDK 21, Android SDK (platform android-37.0, build-tools 37.0.0,
# NDK 29.0.14206865), Rust 1.89.0 + aarch64-linux-android, cargo-ndk 4.1.2, ninja.
# The owner signs the output offline (OFFLINE-APK-SIGNING.md).
set -euo pipefail

KEEP_ANDROID_SHA=09ca787c06257cc99e5574b14192a79e6117e088 # keep-android main 2026-11-13
KEEP_CORE_SHA=e895a38c8f02ba711129bc224f70fbde27721723    # keep main 2026-11-14
APP_ID=org.glowstr.frostfedbunker
VERSION=0.4.0-frostr
BUILD_TOOLS=37.0.0

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/build}"
OUT="${OUT:-$HERE/dist}"
: "${ANDROID_HOME:?set ANDROID_HOME to the Android SDK}"

fetch_pinned() { # url dir sha: exactly the pinned commit, no history
  git init -q "$2"
  git -C "$2" fetch -q --depth 1 "$1" "$3"
  git -C "$2" -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
  test "$(git -C "$2" rev-parse HEAD)" = "$3"
}

rm -rf "$WORK"
fetch_pinned https://github.com/privkeyio/keep-android.git "$WORK" "$KEEP_ANDROID_SHA"
fetch_pinned https://github.com/privkeyio/keep.git "$WORK/keep" "$KEEP_CORE_SHA"
git -C "$WORK" apply "$HERE/patches/keep-android.patch"
git -C "$WORK/keep" apply "$HERE/patches/keep.patch"

# Gradle refuses a dirty keep tree and checks it against keep.version, so commit
# the patched core with a fixed identity and the upstream commit date: the same
# patches always give the same keep.version and SOURCE_DATE_EPOCH.
KEEP_DATE="$(git -C "$WORK/keep" log -1 --format=%ct)"
GIT_AUTHOR_DATE="@$KEEP_DATE +0000" GIT_COMMITTER_DATE="@$KEEP_DATE +0000" \
  git -C "$WORK/keep" -c user.name="Frost Fed Bunker" -c user.email=build@frost-fed-bunker.invalid \
  commit -qam "frost-fed-bunker patches"
git -C "$WORK/keep" rev-parse HEAD > "$WORK/keep.version"
SOURCE_DATE_EPOCH="$(KEEP_REPO="$WORK/keep" "$WORK/scripts/derive-sde.sh")"
export SOURCE_DATE_EPOCH

unset KEYSTORE_FILE KEYSTORE_PASSWORD KEY_ALIAS KEY_PASSWORD
(cd "$WORK" && KEEP_REPO="$WORK/keep" TARGETS=aarch64-linux-android ./gradlew --no-daemon assembleRelease)

shopt -s nullglob
APKS=("$WORK"/app/build/outputs/apk/release/*-unsigned.apk)
test "${#APKS[@]}" -eq 1
NAME="Frost-Fed-Bunker-$VERSION-arm64-unsigned.apk"
mkdir -p "$OUT"
cp "${APKS[0]}" "$OUT/$NAME"
cd "$OUT"

# Positively unsigned from the bytes themselves (a crashing apksigner also exits
# non-zero): no v1 signature entries, no APK Signing Block; native core present.
python3 - "$NAME" <<'PY'
import re, struct, sys, zipfile
path = sys.argv[1]
names = zipfile.ZipFile(path).namelist()
assert not [n for n in names if re.fullmatch(r"META-INF/[^/]+\.(RSA|DSA|EC|SF)", n, re.I)], "v1 signature present"
assert "lib/arm64-v8a/libkeep_mobile.so" in names, "Rust core missing"
data = open(path, "rb").read()
cd = struct.unpack_from("<I", data, data.rfind(b"PK\x05\x06") + 16)[0]
assert data[cd - 16:cd] != b"APK Sig Block 42", "APK Signing Block present"
PY
if "$ANDROID_HOME/build-tools/$BUILD_TOOLS/apksigner" verify "$NAME" >/dev/null 2>&1; then
  echo "refusing: release APK is already signed" >&2; exit 1
fi
BADGING="$("$ANDROID_HOME/build-tools/$BUILD_TOOLS/aapt2" dump badging "$NAME")"
grep -q "^package: name='$APP_ID' .*versionName='$VERSION'" <<<"$BADGING"
if grep -q '^application-debuggable' <<<"$BADGING"; then
  echo "refusing: release APK is debuggable" >&2; exit 1
fi
sha256sum "$NAME" > "$NAME.sha256"
cat "$NAME.sha256"
