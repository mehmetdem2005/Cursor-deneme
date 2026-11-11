#!/usr/bin/env bash
# Reassemble the actual Blender APK with an experimental Android API 30 manifest.
set -Eeuo pipefail

SOURCE_APK="${1:?Usage: repack.sh upstream.apk output.apk}"
OUTPUT_APK="${2:?Usage: repack.sh upstream.apk output.apk}"
APKTOOL_JAR="${APKTOOL_JAR:-apktool.jar}"
ANDROID_BUILD_TOOLS="${ANDROID_BUILD_TOOLS:-${ANDROID_HOME:?ANDROID_HOME required}/build-tools/35.0.0}"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
mkdir -p "$(dirname "$OUTPUT_APK")"
SOURCE_APK="$(realpath "$SOURCE_APK")"
OUTPUT_APK="$(realpath -m "$OUTPUT_APK")"
APKTOOL_JAR="$(realpath "$APKTOOL_JAR")"

echo "[1/6] Decode without disassembling Blender code"
java -Xmx4g -jar "$APKTOOL_JAR" d -s -f -o "$WORKDIR/decoded" "$SOURCE_APK"

echo "[2/6] Set experimental minSdkVersion 30"
python3 scripts/patch_sdk.py "$WORKDIR/decoded"

echo "[3/6] Rebuild original Blender application, assets and native libraries"
java -Xmx4g -jar "$APKTOOL_JAR" b -o "$WORKDIR/unsigned.apk" "$WORKDIR/decoded"

echo "[4/6] Align"
"$ANDROID_BUILD_TOOLS/zipalign" -p -f 4 "$WORKDIR/unsigned.apk" "$WORKDIR/aligned.apk"

echo "[5/6] Sign test package"
KEYSTORE="$WORKDIR/experimental.jks"
if [[ -n "${BLENDER_SIGNING_KEYSTORE_BASE64:-}" ]]; then
  printf '%s' "$BLENDER_SIGNING_KEYSTORE_BASE64" | base64 -d > "$KEYSTORE"
  : "${BLENDER_KEYSTORE_PASS:?Required for supplied signing keystore}"
  : "${BLENDER_KEY_ALIAS:?Required for supplied signing keystore}"
  : "${BLENDER_KEY_PASS:?Required for supplied signing keystore}"
  KEYSTORE_PASS="$BLENDER_KEYSTORE_PASS"
  KEY_ALIAS="$BLENDER_KEY_ALIAS"
  KEY_PASS="$BLENDER_KEY_PASS"
else
  KEYSTORE_PASS="android"
  KEY_PASS="android"
  KEY_ALIAS="blender-api30-test"
  keytool -genkeypair -noprompt -keystore "$KEYSTORE" -storepass "$KEYSTORE_PASS" \
    -keypass "$KEY_PASS" -alias "$KEY_ALIAS" -keyalg RSA -keysize 3072 \
    -validity 3650 -dname "CN=Blender Android 11 Experiment, O=Community, C=TR"
fi

"$ANDROID_BUILD_TOOLS/apksigner" sign --ks "$KEYSTORE" \
  --ks-key-alias "$KEY_ALIAS" --ks-pass "pass:$KEYSTORE_PASS" \
  --key-pass "pass:$KEY_PASS" \
  --min-sdk-version 30 --v2-signing-enabled true --v3-signing-enabled true \
  --out "$OUTPUT_APK" "$WORKDIR/aligned.apk"

echo "[6/6] Verify package, signature, SDK and native libraries"
"$ANDROID_BUILD_TOOLS/apksigner" verify --min-sdk-version 30 --print-certs "$OUTPUT_APK"
"$ANDROID_BUILD_TOOLS/zipalign" -c -p 4 "$OUTPUT_APK"
BADGING="$("$ANDROID_BUILD_TOOLS/aapt" dump badging "$OUTPUT_APK")"
printf '%s\n' "$BADGING" | grep -E "^(package:|sdkVersion:|targetSdkVersion:|native-code:)"
grep -q "^sdkVersion:'30'$" <<<"$BADGING" || { echo "Unexpected minSdkVersion"; exit 1; }
grep -q "^native-code:.*'arm64-v8a'" <<<"$BADGING" || {
  unzip -Z -1 "$OUTPUT_APK" | grep -q '^lib/arm64-v8a/.*\.so$' ||
  { echo "No arm64 native libraries detected"; exit 1; }
}
sha256sum "$OUTPUT_APK"
echo "APK packaging validated. Android 11 runtime is NOT tested."
