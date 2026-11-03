#!/usr/bin/env bash
# This runs ONLY inside GitHub Actions with a real Android emulator and adb.
set -euo pipefail
: "${TEST_APK:?must be an actual compiled APK path}"
: "${TEST_PACKAGE:?Android applicationId required}"
mkdir -p dist
capture_failure() {
  local code=$?
  echo "APK verification failed with exit code $code. Collecting emulator diagnostics..." >&2
  adb logcat -d -s ZIP2APK_BOOT:I AndroidRuntime:E '*:S' > dist/emulator-error.txt 2>&1 || true
  adb shell screencap -p /sdcard/zip2apk-error.png >/dev/null 2>&1 || true
  adb pull /sdcard/zip2apk-error.png dist/emulator-error-screenshot.png >/dev/null 2>&1 || true
  exit "$code"
}
trap capture_failure ERR
[ -s "$TEST_APK" ] || { echo 'Compiled APK missing' >&2; exit 1; }

echo 'Checking emulator connectivity and Android version:'
adb wait-for-device
adb shell getprop ro.build.version.release

echo 'Installing the signed APK on the Android emulator:'
adb install -r "$TEST_APK"

echo 'Ensuring Android Package Manager has the exact package:'
adb shell pm path "$TEST_PACKAGE" | tee dist/emulator-package.txt
grep -q '^package:' dist/emulator-package.txt

echo 'Launching the actual MainActivity (not merely installing the APK):'
adb logcat -c
adb shell am start -W -n "$TEST_PACKAGE/com.zip2apk.generated.MainActivity" | tee dist/emulator-start.txt
grep -E -q 'Status: ok|Complete' dist/emulator-start.txt

# The built Android app emits ZIP2APK_BOOT page="READY" only after its local WebView
# has loaded a non-empty index.html DOM. This checks much more than a launch result.
echo 'Waiting for the WebView to render its packaged HTML:'
ready=0
for _ in $(seq 1 24); do
  if adb logcat -d -s ZIP2APK_BOOT:I '*:S' | grep -Fq 'page="READY"'; then
    ready=1
    break
  fi
  sleep 2
done
adb logcat -d -s ZIP2APK_BOOT:I '*:S' | tee dist/emulator-webview.txt
if [ "$ready" -ne 1 ]; then
  echo 'WebView did not confirm a rendered HTML DOM. APK smoke test FAILED.' >&2
  exit 1
fi

# Require the app to remain alive after the page has loaded.
pid=$(adb shell pidof -s "$TEST_PACKAGE" | tr -d '\r')
[ -n "$pid" ] || { echo 'Android app process exited unexpectedly' >&2; exit 1; }
echo "App alive with Android PID $pid, HTML is rendered."

adb shell screencap -p /sdcard/zip2apk-screenshot.png
adb pull /sdcard/zip2apk-screenshot.png dist/emulator-screenshot.png
[ "$(wc -c < dist/emulator-screenshot.png)" -gt 2000 ]
echo 'EMULATOR_INSTALL_LAUNCH_RENDER_SUCCESS'
