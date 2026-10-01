# Clipora for Android

Offline media toolkit for Android. Same product as the PC build, running
entirely on the device: no server, no account, no upload.

Built with [Kivy](https://kivy.org) and [buildozer](https://buildozer.readthedocs.io)
(python-for-android). The conversion core is a port of the PC modules, not a
rewrite — see [Code layout](#code-layout).

## What works

| Feature | Status |
|---|---|
| Convert to mp3 / m4a / wav / flac / opus | yes |
| Convert video to mp4 (H.264 + AAC, 3 quality levels) | yes |
| Frame-rate cap (max / 60 / 30) | yes |
| Trim by start + length (`90`, `MM:SS`, `HH:MM:SS`) | yes |
| Batch convert (multi-select) | yes |
| Cancel a running job | yes |
| Public single-item URL download via yt-dlp (audio / video) | yes |
| Stem separation (Demucs) | **no** — no PyTorch wheel for Android |
| ProRes / After Effects export | **no** — dropped from the port |
| Batch URL download, playlists | **no** — PC-only for now |

## Build

Prerequisites: Linux or WSL2, Python 3.11+, JDK 17, Android SDK/NDK. Buildozer
downloads the SDK/NDK itself on first run if you point it at one.

```bash
python -m pip install buildozer "cython==0.29.36"
cd android
buildozer -v android debug          # -> bin/clipora-0.1.0-arm64-v8a-debug.apk
```

Install with `adb install -r bin/*.apk`.

### WSL2 notes (no sudo)

Everything works without root: install pip with `get-pip.py --user`, then
`pip install --user buildozer`. The one gap is Java — Ubuntu's `openjdk-17-jdk`
needs apt, so unpack a Temurin 17 tarball into `~/jdk-17` instead and export
`JAVA_HOME=~/jdk-17 PATH=$JAVA_HOME/bin:$PATH` before building. Buildozer
fetches the SDK, NDK and platform tools into `~/.buildozer` on first run
(several GB — the first build is mostly downloading).

### Release signing

The keystore must never enter git or CI. Create it once, locally:

```bash
keytool -genkey -v -keystore ~/.clipora-release.keystore -alias clipora \
  -keyalg RSA -keysize 2048 -validity 10000
```

Then build unsigned and sign by hand (buildozer has no keystore options, so
this path works on every version):

```bash
cd android
buildozer -v android release       # -> bin/*-release-unsigned.apk
BT=~/.buildozer/android/platform/android-sdk/build-tools/<ver>
$BT/zipalign -f 4 bin/*-release-unsigned.apk bin/clipora-aligned.apk
$BT/apksigner sign --ks ~/.clipora-release.keystore --out bin/clipora-release.apk bin/clipora-aligned.apk
$BT/apksigner verify --print-certs bin/clipora-release.apk
```

Back the keystore up somewhere safe — lose it and you can never publish an
update for the same package name again. For Google Play, switch
`android.release_artifact` to `aab` in `buildozer.spec` and upload the bundle
instead.

## Code layout

```
android/
├── main.py             # Kivy UI: convert screen + download screen
├── theme.py            # colours, ported from clipora/ui_components/theme.py
├── buildozer.spec      # APK config
├── core/               # ported, no Kivy imports — unit tested on desktop
│   ├── tools.py        # finds ffmpeg / yt-dlp inside the APK
│   ├── ffmpeg.py       # port of clipora/ffmpeg.py
│   └── ytdlp.py        # port of the URL half of clipora/importer.py
└── icon.png
```

### Ported vs rewritten

`core/` is a copy of the PC logic, because that logic is pure stdlib and
`subprocess` — which is exactly the part that is expensive to get right
(argument building, progress parsing, never clobbering a good output file with
a partial one). The Tkinter UI is 184 KB and has no Android equivalent, so
`main.py` is written from scratch against Kivy.

`tests/test_android_core.py` imports both sides and asserts they still agree.
If you change `clipora/ffmpeg.py` or `clipora/importer.py`, mirror the change
into `android/core/` — the parity test will tell you when you forget.

## Platform constraints worth knowing

* **No ffprobe.** The p4a `ffmpeg` recipe ships only `ffmpeg`, so
  `core.ffmpeg.probe()` parses the stream table out of `ffmpeg -i` instead. If
  you ever bundle an `ffprobe`, `probe()` picks it up automatically.
* **`ffpyplayer_codecs` + `libx264` are required entries.** Without them the
  recipe builds an mp4/aac-only ffmpeg with no H.264 encoder and video
  conversion cannot work.
* **`ffmpeg` is not a normal executable.** Android only allows `execve` from
  app-owned native paths, so the recipe ships it as `libffmpegbin.so` inside
  `nativeLibraryDir`. `core/tools.py` resolves it there and sets
  `LD_LIBRARY_PATH` so the loader finds `libav*.so`.
* **No storage permission.** Inputs are picked through SAF (plyer); outputs go
  to the app's own external files dir, which needs no runtime grant. That
  folder is deleted when the app is uninstalled — see the `ponytail:` note in
  `core/tools.py` if that becomes a problem.
* **Dark theme only.** The PC light palette is not ported yet.
* **No yt-dlp JS runtime or browser impersonation.** `curl_cffi` and Deno/Node
  have no Android build, so some sites that work on PC may still be blocked.
  `--impersonate` was dropped rather than faked.

## Threading contract

Worker threads never touch a Kivy widget. `JobRunner` in `main.py` runs each
job on a thread, pushes `(kind, payload)` events onto a queue, and the screen
drains that queue from `Clock` on the main thread. Every job is snapshotted
into a frozen dataclass before its thread starts.

## Testing

```bash
python -m unittest tests.test_android_core -v
```

The full desktop suite also covers it:

```bash
python -m compileall -q app.py clipora tests scripts
python -W error::ResourceWarning -m unittest discover -s tests -v
```

`main.py` and `theme.py` need Kivy and a device, so they are not imported by
the test suite.
