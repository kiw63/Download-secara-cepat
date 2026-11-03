#!/usr/bin/env python3
"""Prepare and compile a REAL signed Android WebView APK from a static-site ZIP.
Only Python stdlib required; Gradle + Android SDK required for --build.
"""
import argparse
import base64
import html
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

MAX_ARCHIVE = 18 * 1024 * 1024
MAX_EXPANDED = 110 * 1024 * 1024
MAX_ENTRIES = 1500
MAX_ENTRY = 35 * 1024 * 1024
VALID_EXT = {'.html', '.htm', '.css', '.js', '.mjs', '.json', '.txt', '.xml', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.eot', '.wasm', '.bin', '.data', '.webmanifest', '.map', '.mp3', '.m4a', '.wav', '.ogg', '.mp4', '.webm', '.pdf', '.bmp', '.glb', '.gltf'}
PACKAGE_RE = re.compile(r'^(?:[a-z][a-z0-9_]*\.){2,}[a-z][a-z0-9_]*$')
INPUT_RE = re.compile(r'^uploads/[a-f0-9]{32}\.zip$')


def check_archive(archive):
    archive = pathlib.Path(archive)
    if not archive.is_file() or not (20 <= archive.stat().st_size <= MAX_ARCHIVE):
        raise ValueError('ZIP must be 20 bytes to 18 MiB.')
    with zipfile.ZipFile(archive) as z:
        items = z.infolist()
        if len(items) > MAX_ENTRIES:
            raise ValueError('Too many ZIP entries.')
        total = 0
        names = set()
        for item in items:
            name = item.filename
            p = pathlib.PurePosixPath(name)
            if ('\\' in name or '\x00' in name or name.startswith('/') or
                    '..' in p.parts or (len(name) > 1 and name[1] == ':')):
                raise ValueError('Unsafe ZIP entry path: ' + repr(name))
            mode = item.external_attr >> 16
            if stat.S_IFMT(mode) == stat.S_IFLNK:
                raise ValueError('ZIP symlinks not allowed')
            if item.flag_bits & 1:
                raise ValueError('Password-protected ZIP is not supported')
            if item.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):
                raise ValueError('Unsupported ZIP compression')
            if item.file_size > MAX_ENTRY:
                raise ValueError('One ZIP entry is too large')
            total += item.file_size
            if total > MAX_EXPANDED:
                raise ValueError('ZIP expands beyond limit')
            if not item.is_dir():
                if name in names:
                    raise ValueError('Duplicate ZIP entry')
                names.add(name)
        roots = [n for n in names if n == 'index.html']
        if roots:
            prefix = ''
        else:
            roots = [n for n in names if n.endswith('/index.html')]
            if len(roots) != 1:
                raise ValueError('ZIP requires an index.html at root or inside one folder')
            prefix = roots[0][:-len('index.html')]
        return prefix


def extract_site(archive, dest):
    prefix = check_archive(archive)
    dest = pathlib.Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if item.is_dir() or not item.filename.startswith(prefix):
                continue
            relative = item.filename[len(prefix):]
            if not relative or pathlib.PurePosixPath(relative).suffix.lower() not in VALID_EXT:
                continue
            output = dest.joinpath(*pathlib.PurePosixPath(relative).parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as source, open(output, 'wb') as sink:
                shutil.copyfileobj(source, sink, 1024 * 1024)
            if output.stat().st_size != item.file_size:
                raise ValueError('Extracted size mismatch for ZIP entry')
            count += 1
    if not (dest / 'index.html').is_file():
        raise ValueError('Extracted site is missing index.html')
    return count


MAIN_ACTIVITY = r'''package com.zip2apk.generated;
import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.util.Log;
import java.io.InputStream;
import java.io.ByteArrayInputStream;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

public class MainActivity extends Activity {
  private WebView web;
  private ValueCallback<Uri[]> chooser;
  private PermissionRequest cameraRequest;
  private final int PICK_FILE = 3041;
  private final int ASK_CAMERA = 3042;
  private static final String HOST = "appassets.androidplatform.net";

  private String mime(String name) {
    String n = name.toLowerCase(Locale.US);
    if (n.endsWith(".html") || n.endsWith(".htm")) return "text/html";
    if (n.endsWith(".js") || n.endsWith(".mjs")) return "text/javascript";
    if (n.endsWith(".css")) return "text/css";
    if (n.endsWith(".json") || n.endsWith(".webmanifest") || n.endsWith(".map")) return "application/json";
    if (n.endsWith(".wasm")) return "application/wasm";
    if (n.endsWith(".svg")) return "image/svg+xml";
    if (n.endsWith(".png")) return "image/png";
    if (n.endsWith(".jpg") || n.endsWith(".jpeg")) return "image/jpeg";
    if (n.endsWith(".webp")) return "image/webp";
    if (n.endsWith(".gif")) return "image/gif";
    if (n.endsWith(".ico")) return "image/x-icon";
    if (n.endsWith(".woff2")) return "font/woff2";
    if (n.endsWith(".woff")) return "font/woff";
    if (n.endsWith(".pdf")) return "application/pdf";
    if (n.endsWith(".mp4")) return "video/mp4";
    return "application/octet-stream";
  }

  private WebResourceResponse missingAsset() {
    WebResourceResponse r = new WebResourceResponse("text/plain", "UTF-8", new ByteArrayInputStream(new byte[0]));
    r.setStatusCodeAndReasonPhrase(404, "Not Found");
    return r;
  }

  private WebResourceResponse localAsset(Uri u) {
    if (!"https".equals(u.getScheme()) || !HOST.equals(u.getHost())) return null;
    String rel = Uri.decode(u.getEncodedPath());
    if (rel == null || !rel.startsWith("/")) return missingAsset();
    rel = rel.substring(1);
    if (rel.length() == 0) rel = "index.html";
    for (String segment : rel.split("/")) {
      if (segment.equals("..") || segment.equals(".") || segment.isEmpty() || segment.indexOf('\\') >= 0)
        return missingAsset();
    }
    try {
      InputStream in = getAssets().open(rel);
      WebResourceResponse response = new WebResourceResponse(mime(rel), "UTF-8", in);
      Map<String,String> headers = new HashMap<>();
      headers.put("Access-Control-Allow-Origin", "*");
      headers.put("X-Content-Type-Options", "nosniff");
      response.setResponseHeaders(headers);
      return response;
    } catch (Exception missing) {
      // SPA routes load index.html. Do not silently turn missing asset files into HTML.
      if (!rel.contains(".")) {
        try { return new WebResourceResponse("text/html", "UTF-8", getAssets().open("index.html")); }
        catch (Exception ignored) { }
      }
      return missingAsset();
    }
  }

  @Override public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    getWindow().setStatusBarColor(Color.rgb(13, 18, 27));
    getWindow().setNavigationBarColor(Color.rgb(13, 18, 27));
    web = new WebView(this);
    web.setBackgroundColor(Color.rgb(13, 18, 27));
    setContentView(web);
    WebView.setWebContentsDebuggingEnabled(false);
    WebSettings s = web.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setAllowFileAccess(false);
    s.setAllowContentAccess(true);
    s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    s.setMediaPlaybackRequiresUserGesture(true);
    if (Build.VERSION.SDK_INT >= 26) s.setSafeBrowsingEnabled(true);
    web.setWebViewClient(new WebViewClient() {
      @Override public void onPageFinished(WebView view, String url) {
        if (url != null && url.startsWith("https://" + HOST + "/")) {
          view.evaluateJavascript("(function(){return document.body && document.body.innerHTML.length > 0 ? 'READY' : 'EMPTY'})()",
              result -> Log.i("ZIP2APK_BOOT", "page=" + result));
        }
      }
      @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
        return localAsset(req.getUrl());
      }
    });
    web.setWebChromeClient(new WebChromeClient() {
      @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
        if (chooser != null) chooser.onReceiveValue(null);
        chooser = callback;
        try { startActivityForResult(params.createIntent(), PICK_FILE); return true; }
        catch (Exception ex) { chooser = null; callback.onReceiveValue(null); return false; }
      }
      @Override public void onPermissionRequest(PermissionRequest req) {
        runOnUiThread(() -> {
          if (!HOST.equals(req.getOrigin().getHost()) || !"https".equals(req.getOrigin().getScheme())) {
            req.deny(); return;
          }
          boolean video = false;
          for (String resource : req.getResources()) {
            if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)) video = true;
            else { req.deny(); return; }
          }
          if (!video) { req.deny(); return; }
          if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            cameraRequest = req;
            requestPermissions(new String[]{Manifest.permission.CAMERA}, ASK_CAMERA);
          } else req.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
        });
      }
      @Override public void onPermissionRequestCanceled(PermissionRequest req) {
        if (cameraRequest == req) cameraRequest = null;
      }
    });
    web.loadUrl("https://appassets.androidplatform.net/index.html");
  }
  @Override public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
    super.onRequestPermissionsResult(code, perms, results);
    if (code == ASK_CAMERA && cameraRequest != null) {
      if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED)
        cameraRequest.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
      else cameraRequest.deny();
      cameraRequest = null;
    }
  }
  @Override protected void onActivityResult(int request, int result, Intent data) {
    super.onActivityResult(request, result, data);
    if (request == PICK_FILE && chooser != null) {
      chooser.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result, data));
      chooser = null;
    }
  }
  @Override public void onBackPressed() {
    if (web != null && web.canGoBack()) web.goBack(); else super.onBackPressed();
  }
  @Override protected void onDestroy() {
    if (chooser != null) chooser.onReceiveValue(null);
    if (web != null) { web.destroy(); web = null; }
    super.onDestroy();
  }
}
'''


def write(file, body):
    p = pathlib.Path(file)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding='utf8')


def make_project(project, title, appid, run_number=1):
    if not PACKAGE_RE.fullmatch(appid) or len(appid) > 110:
        raise ValueError('Invalid package name (example: com.example.myapp)')
    title = title.strip()
    if not 2 <= len(title) <= 42 or any(ord(c) < 32 for c in title):
        raise ValueError('App title must be 2–42 characters')
    if any(c in title for c in ['\x00','\n','\r']):
        raise ValueError('Invalid app title')
    run_number = max(1, min(int(run_number), 2000000000))
    project = pathlib.Path(project)
    write(project / 'settings.gradle', "pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\nrootProject.name = 'ZIP2APK'\ninclude ':app'\n")
    write(project / 'build.gradle', "plugins { id 'com.android.application' version '8.7.3' apply false }\n")
    write(project / 'gradle.properties', 'org.gradle.jvmargs=-Xmx1536m -Dfile.encoding=UTF-8\nandroid.useAndroidX=false\norg.gradle.parallel=false\n')
    write(project / 'app/build.gradle', f"""plugins {{ id 'com.android.application' }}
android {{
  namespace 'com.zip2apk.generated'
  compileSdk 35
  defaultConfig {{
    applicationId '{appid}'
    minSdk 23
    targetSdk 34
    versionCode {run_number}
    versionName '1.0.{run_number}'
  }}
  signingConfigs {{
    release {{
      storeFile file(System.getenv('ZIP2APK_KEYSTORE_PATH'))
      storePassword System.getenv('ZIP2APK_KEYSTORE_PASSWORD')
      keyAlias System.getenv('ZIP2APK_KEY_ALIAS')
      keyPassword System.getenv('ZIP2APK_KEY_PASSWORD')
    }}
  }}
  buildTypes {{
    release {{
      minifyEnabled false
      signingConfig signingConfigs.release
    }}
  }}
  compileOptions {{ sourceCompatibility JavaVersion.VERSION_17; targetCompatibility JavaVersion.VERSION_17 }}
}}
""")
    write(project / 'app/src/main/AndroidManifest.xml', '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-permission android:name="android.permission.INTERNET"/>
  <uses-permission android:name="android.permission.CAMERA"/>
  <uses-feature android:name="android.hardware.camera" android:required="false"/>
  <application android:label="@string/app_name" android:theme="@android:style/Theme.Material.Light.NoActionBar" android:usesCleartextTraffic="false">
    <activity android:name="com.zip2apk.generated.MainActivity" android:exported="true">
      <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>
    </activity>
  </application>
</manifest>
''')
    safe_title = html.escape(title.replace("'", "\\'"), quote=True)
    write(project / 'app/src/main/res/values/strings.xml', f'<?xml version="1.0" encoding="utf-8"?><resources><string name="app_name" formatted="false">{safe_title}</string></resources>\n')
    write(project / 'app/src/main/java/com/zip2apk/generated/MainActivity.java', MAIN_ACTIVITY)
    return project / 'app/src/main/assets'


def setup_signing(dir):
    dir = pathlib.Path(dir)
    dir.mkdir(parents=True, exist_ok=True)
    b64 = os.getenv('APK_KEYSTORE_BASE64', '').strip()
    passphrase = os.getenv('APK_KEYSTORE_PASSWORD', '').strip()
    raw_alias = os.getenv('APK_KEY_ALIAS', '').strip()
    alias = raw_alias or 'zip2apk'
    keypass = os.getenv('APK_KEY_PASSWORD', '').strip()
    keystore = dir / 'release.jks'
    if b64 or passphrase or keypass or raw_alias:
        if not (b64 and passphrase and keypass and alias):
            raise ValueError('Incomplete APK signing secrets. Need keystore, store password, key alias and key password')
        keystore.write_bytes(base64.b64decode(b64, validate=True))
        print('Using persistent keystore from GitHub Actions secrets.')
    else:
        import secrets
        passphrase = secrets.token_hex(20)
        keypass = passphrase
        alias = 'zip2apk'
        print('WARNING: Generated a new signing key for this build. To upgrade the same app, set persistent signing secrets.')
        subprocess.run(['keytool', '-genkeypair', '-noprompt', '-storetype', 'JKS', '-keystore', str(keystore), '-alias', alias, '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000', '-storepass', passphrase, '-keypass', keypass, '-dname', 'CN=ZIP2APK, OU=Build, O=ZIP2APK, L=Local, ST=Local, C=ID'], check=True)
    return {
        'ZIP2APK_KEYSTORE_PATH': str(keystore.resolve()),
        'ZIP2APK_KEYSTORE_PASSWORD': passphrase,
        'ZIP2APK_KEY_ALIAS': alias,
        'ZIP2APK_KEY_PASSWORD': keypass,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--package', required=True)
    parser.add_argument('--output', default='dist/app.apk')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--project-dir')
    args = parser.parse_args()
    if os.getenv('GITHUB_ACTIONS') == 'true' and not INPUT_RE.fullmatch(args.zip):
        raise ValueError('ZIP path must be uploads/<32 lowercase hex chars>.zip')
    project = pathlib.Path(args.project_dir).resolve() if args.project_dir else pathlib.Path('generated-project').resolve()
    if project.exists():
        raise ValueError('Project directory exists. Choose an empty path.')
    assets = make_project(project, args.name, args.package, os.getenv('GITHUB_RUN_NUMBER', '1'))
    count = extract_site(args.zip, assets)
    print(f'Prepared Android project, bundled {count} site assets at {project}')
    if args.prepare_only:
        return
    env = os.environ.copy()
    env.update(setup_signing(project / 'signing'))
    print('Running real Gradle assembleRelease...')
    subprocess.run(['gradle', '--no-daemon', '--console=plain', 'assembleRelease'], cwd=project, env=env, check=True)
    apk = project / 'app/build/outputs/apk/release/app-release.apk'
    if not apk.is_file() or apk.stat().st_size < 10240:
        raise RuntimeError('Gradle did not produce a real signed release APK')
    target = pathlib.Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(apk, target)
    print(f'BUILD_SUCCESS: {target} ({target.stat().st_size} bytes)')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('BUILD_FAILED:', type(e).__name__, str(e), file=sys.stderr)
        sys.exit(1)
