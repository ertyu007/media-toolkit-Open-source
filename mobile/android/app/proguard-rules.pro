# yt-dlp Chaquopy AAR: Python (ytdlp_runner) calls Java methods by reflection.
# R8 must not obfuscate/rename these classes or methods.
-keep class dev.ffmpegkit_maintained.ytdlp.** { *; }
-keep class com.chaquo.python.** { *; }

# Anonymous Kotlin objects passed to yt-dlp as LogCallback / DownloadProgressCallback.
# Python invokes onLog/onProgressUpdate via reflection, so keep their method names.
-keepclasseswithmembers class * implements dev.ffmpegkit_maintained.ytdlp.LogCallback { <methods>; }
-keepclasseswithmembers class * implements dev.ffmpegkit_maintained.ytdlp.DownloadProgressCallback { <methods>; }
