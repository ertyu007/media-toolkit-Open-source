[app]

# (str) Title of your application
title = Clipora

# (str) Package name
package.name = clipora

# (str) Package domain (needed for android/ios packaging)
package.domain = com.clipora

# (str) Source directory where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (str) Application versioning (method 1)
version = 0.1.0

# (list) Application requirements
# python3 + kivy     : runtime and UI
# ffmpeg             : compiled by the p4a recipe (ffprobe is NOT included)
# ffpyplayer_codecs  : opt-dep that flips the ffmpeg build to full codec set
# libx264            : H.264 encoder; without it video conversion is impossible
# yt-dlp             : pure-python pip module, runs as "python -m yt_dlp" (no managed binary)
# plyer              : SAF file picker
# android            : jnius bridge (nativeLibraryDir / app dirs)
requirements = python3,kivy,ffmpeg,ffpyplayer_codecs,libx264,yt-dlp,plyer,android

# (str) Supported orientation. p4a only accepts portrait / landscape /
# portrait-reverse / landscape-reverse (no "all"), so this stays portrait:
# phone-first, still usable letterboxed on tablets. Flip to landscape for a
# tablet-only build.
orientation = portrait

# (list) Permissions
# No storage permission: inputs are picked through SAF (plyer) and outputs land
# in the app's own external files dir, which needs no runtime grant.
# WAKE_LOCK (normal level, auto-granted) keeps long conversions alive in Doze.
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK


# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# NDK intentionally unpinned: buildozer/p4a picks the NDK its current release
# is tested against. Pinning an old NDK breaks newer p4a (missing llvm tools).

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (list) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = False

# (str) The format used to package the app for release mode (aab or apk or aar).
android.release_artifact = apk

# (bool) Skip byte compiling for .py files
android.no-bytecode = False

# (str) Path to a custom signing configuration
# android.custom_signing = <path>

android.accept_sdk_license = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
build_dir = ./build
# (str) Path to build output (i.e. .apk, .aab, .aar) storage
bin_dir = ./bin

# (str) Path to the Android SDK
# sdk = /opt/android-sdk

[app:fullscreen]
