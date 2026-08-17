package com.clipora.clipora_mobile

import android.app.Activity
import android.content.ContentValues
import android.content.Intent
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import dev.ffmpegkit_maintained.ytdlp.DownloadProgressCallback
import dev.ffmpegkit_maintained.ytdlp.LogCallback
import dev.ffmpegkit_maintained.ytdlp.YtDlp
import dev.ffmpegkit_maintained.ytdlp.YtDlpException
import dev.ffmpegkit_maintained.ytdlp.YtDlpRequest
import dev.ffmpegkit_maintained.ytdlp.YtDlpResponse
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.ExecutionException
import java.util.concurrent.Executors
import java.util.concurrent.Future

class MainActivity : FlutterActivity() {

    private companion object {
        const val CHANNEL = "com.clipora/ytdlp"
        const val EVENTS = "com.clipora/ytdlp/events"
        const val NATIVE_CHANNEL = "com.clipora/native"
        const val PICK_MEDIA_REQUEST = 9101
        const val PICK_COOKIES_REQUEST = 9102
    }

    private val runningJobs = ConcurrentHashMap<String, Future<YtDlpResponse>>()
    private val completionExecutor = Executors.newSingleThreadExecutor()
    private var eventSink: EventChannel.EventSink? = null
    private var pendingPickResult: MethodChannel.Result? = null

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != PICK_MEDIA_REQUEST && requestCode != PICK_COOKIES_REQUEST) return
        val result = pendingPickResult
        pendingPickResult = null
        if (result == null) return
        val uri = data?.data
        if (resultCode != Activity.RESULT_OK || uri == null) {
            result.success(null)
            return
        }
        try {
            val cacheDir = File(cacheDir, "clipora-picks")
            cacheDir.mkdirs()
            val name = queryDisplayName(uri) ?: "picked_file"
            val dest = File(cacheDir, name)
            contentResolver.openInputStream(uri).use { input ->
                if (input == null) throw IllegalStateException("ไม่สามารถเปิดไฟล์ได้")
                dest.outputStream().use { output -> input.copyTo(output) }
            }
            result.success(dest.absolutePath)
        } catch (e: Exception) {
            result.error("pick_error", e.message ?: "เลือกไฟล์ไม่สำเร็จ", null)
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        val channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        channel.setMethodCallHandler { call, result ->
            try {
                when (call.method) {
                    "init" -> {
                        ensureInitialized()
                        result.success(true)
                    }
                    "download" -> handleDownload(call, result)
                    "cancel" -> {
                        val id = call.argument<String>("id")
                        if (id != null) {
                            runningJobs.remove(id)?.cancel(true)
                        }
                        result.success(true)
                    }
                    else -> result.notImplemented()
                }
            } catch (e: Exception) {
                result.error("error", e.message ?: e.javaClass.simpleName, null)
            }
        }

        val nativeChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, NATIVE_CHANNEL)
        nativeChannel.setMethodCallHandler { call, result ->
            try {
                when (call.method) {
                    "pickMediaFile" -> {
                        pendingPickResult = result
                        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            type = "*/*"
                            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("video/*", "audio/*"))
                        }
                        startActivityForResult(intent, PICK_MEDIA_REQUEST)
                    }
                    "pickCookiesFile" -> {
                        pendingPickResult = result
                        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            type = "*/*"
                            // ครอบคลุมทั้งไฟล์ .txt (Netscape cookies) และไม่มีนามสกุล
                            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("text/plain", "text/*", "application/octet-stream"))
                        }
                        startActivityForResult(intent, PICK_COOKIES_REQUEST)
                    }
                    "saveToDownloads" -> {
                        val source = call.argument<String>("sourcePath")
                        val name = call.argument<String>("displayName")
                        val mime = call.argument<String>("mimeType")
                        if (source == null || name == null) {
                            result.error("bad_args", "missing sourcePath or displayName", null)
                        } else {
                            val uri = saveToDownloads(source, name, mime ?: "application/octet-stream")
                            result.success(uri)
                        }
                    }
                    else -> result.notImplemented()
                }
            } catch (e: Exception) {
                result.error("error", e.message ?: e.javaClass.simpleName, null)
            }
        }

        val events = EventChannel(flutterEngine.dartExecutor.binaryMessenger, EVENTS)
        events.setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                eventSink = events
            }

            override fun onCancel(arguments: Any?) {
                eventSink = null
            }
        })
    }

    private fun ensureInitialized() {
        try {
            YtDlp.init(applicationContext)
        } catch (e: YtDlpException) {
            throw e
        }
    }

    private fun handleDownload(call: MethodCall, result: MethodChannel.Result) {
        val id = call.argument<String>("id") ?: throw IllegalArgumentException("missing id")
        val url = call.argument<String>("url") ?: throw IllegalArgumentException("missing url")
        val outputTemplate = call.argument<String>("outputTemplate") ?: ""
        val options = call.argument<List<*>>("options")?.map { it.toString() } ?: emptyList()

        ensureInitialized()

        val request = YtDlpRequest(url)
        if (outputTemplate.isNotEmpty()) {
            request.setOutputTemplate(outputTemplate)
        }
        for (option in options) {
            request.addOption(option)
        }

        // เก็บ log ระดับ ERROR/WARNING ไว้แสดง error ที่แท้จริง
        val errorLog = StringBuilder()
        // ใช้ explicit anonymous object (ไม่ใช่ Kotlin SAM lambda) เพราะ Chaquopy
        // ฝั่ง Python เรียก method ของ callback ผ่าน Java reflection — SAM lambda
        // ที่ compile ด้วย invokedynamic จะไม่ expose `onLog` ให้ Python เรียกได้
        val logCallback = object : LogCallback {
            override fun onLog(level: String, message: String) {
                if (level == "ERROR" || level == "WARNING") {
                    errorLog.append(message).append('\n')
                    if (errorLog.length > 4000) {
                        errorLog.delete(0, errorLog.length - 4000)
                    }
                }
            }
        }

        val future = YtDlp.executeDebug(request, logCallback, object : DownloadProgressCallback {
            override fun onProgressUpdate(progress: Float, etaInSeconds: Long, line: String) {
                postEvent(mapOf(
                    "id" to id,
                    "type" to "progress",
                    "progress" to (progress / 100.0),
                    "eta" to etaInSeconds,
                ))
            }
        })
        runningJobs[id] = future
        completionExecutor.execute {
            try {
                val response = future.get()
                if (response.isSuccess()) {
                    postEvent(mapOf(
                        "id" to id,
                        "type" to "done",
                        "exitCode" to 0,
                    ))
                } else {
                    val message = friendlyError(errorLog.toString())
                    postEvent(mapOf(
                        "id" to id,
                        "type" to "error",
                        "message" to message,
                    ))
                }
            } catch (e: Exception) {
                if (e is java.util.concurrent.CancellationException) {
                    postEvent(mapOf("id" to id, "type" to "cancelled"))
                } else {
                    val cause = (e as? ExecutionException)?.cause
                    val raw = cause?.message ?: e.message ?: ""
                    val message = friendlyError(raw)
                    postEvent(mapOf(
                        "id" to id,
                        "type" to "error",
                        "message" to message,
                    ))
                }
            } finally {
                runningJobs.remove(id)
            }
        }
        result.success(true)
    }

    /// แปลง error ดิบจาก yt-dlp เป็นข้อความภาษาไทยที่เข้าใจง่าย
    /// (บล็อก bot, ไม่รองรับ, ต้อง login, ลิขสิทธิ์ ฯลฯ)
    private fun friendlyError(log: String): String {
        val lower = log.lowercase()
        return when {
            lower.contains("confirm you're not a bot") ||
                lower.contains("captcha") ||
                lower.contains("unusual traffic") ||
                lower.contains("automated access") ||
                lower.contains("this request has been blocked") ||
                lower.contains("http error 403") ||
                lower.contains("http error 429") ||
                lower.contains("temporary block") ||
                lower.contains("robot") ->
                "แพลตฟอร์มนี้บล็อกการดาวน์โหลดอัตโนมัติ (กัน bot) — " +
                    "ลิงก์นี้ต้องเข้าสู่ระบบหรือใช้คุกกี้ จึงยังดาวน์โหลดไม่ได้"
            lower.contains("no video formats") ||
                lower.contains("requested format is not available") ||
                lower.contains("no formats") ->
                "ไม่พบวิดีโอในคุณภาพที่เลือก — ลองลดคุณภาพ/เฟรมเรต หรือลิงก์นี้ไม่รองรับ"
            lower.contains("unsupported url") ||
                lower.contains("is not a valid url") ||
                lower.contains("invalid url") ->
                "ลิงก์นี้ไม่รองรับ (ไม่ใช่ลิงก์วิดีโอสาธารณะที่ถูกต้อง)"
            lower.contains("unable to extract") ||
                lower.contains("is not supported") ||
                lower.contains("not supported by") ->
                "แพลตฟอร์ม/ลิงก์นี้ยังไม่รองรับ หรือวิดีโอถูกลบ/เป็นส่วนตัว"
            lower.contains("video unavailable") ||
                lower.contains("this video is unavailable") ->
                "วิดีโอนี้ไม่พร้อมใช้งาน (ถูกลบ เป็นส่วนตัว หรือจำกัดสิทธิ์)"
            lower.contains("private video") ->
                "วิดีโอนี้เป็นส่วนตัว (private)"
            lower.contains("age-restricted") ||
                lower.contains("age restricted") ||
                lower.contains("confirm your age") ->
                "วิดีโอจำกัดอายุ — ต้องเข้าสู่ระบบเพื่อยืนยัน"
            lower.contains("copyright") ||
                lower.contains("dmca") ->
                "วิดีโอนี้ถูกบล็อกด้วยลิขสิทธิ์"
            lower.contains("login") ||
                lower.contains("sign in") ||
                lower.contains("authentication") ->
                "วิดีโอ/เพจนี้ต้องเข้าสู่ระบบก่อน จึงดาวน์โหลดไม่ได้"
            lower.contains("geo-restricted") ||
                lower.contains("georestricted") ||
                lower.contains("not available in your country") ->
                "วิดีโอนี้จำกัดเฉพาะบางประเทศ/ภูมิภาค"
            lower.contains("ffmpeg") ||
                lower.contains("merging of multiple formats") ->
                "วิดีโอชนิดนี้ต้องใช้ ffmpeg เพิ่มเติม — ยังดาวน์โหลดไม่ได้"
            else -> extractError(log) ?: "ดาวน์โหลดไม่สำเร็จ"
        }
    }

    private fun extractError(log: String): String? {
        if (log.isBlank()) return null
        val lines = log.trim().split('\n')
        val errors = lines.filter { it.startsWith("ERROR:") }
        val last = errors.lastOrNull() ?: lines.last()
        return last.trim().take(500)
    }

    private fun queryDisplayName(uri: Uri): String? {
        val projection = arrayOf(OpenableColumns.DISPLAY_NAME)
        contentResolver.query(uri, projection, null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) {
                return cursor.getString(index)
            }
        }
        return null
    }

    private fun saveToDownloads(sourcePath: String, displayName: String, mimeType: String): String {
        val file = File(sourcePath)
        if (!file.exists() || !file.isFile) {
            throw IllegalArgumentException("ไม่พบไฟล์ผลลัพธ์")
        }
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.Q) {
            throw UnsupportedOperationException("ต้องใช้ Android 10+")
        }
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
            put(MediaStore.MediaColumns.MIME_TYPE, mimeType)
            put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Clipora")
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }
        val uri: Uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: throw IllegalStateException("ไม่สามารถบันทึกลงโฟลเดอร์ดาวน์โหลดได้")
        contentResolver.openOutputStream(uri).use { out ->
            if (out == null) throw IllegalStateException("ไม่สามารถเปิดไฟล์ปลายทางได้")
            file.inputStream().use { input -> input.copyTo(out) }
        }
        val pendingValues = ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }
        contentResolver.update(uri, pendingValues, null, null)
        return uri.toString()
    }

    private fun postEvent(map: Map<String, Any?>) {
        runOnUiThread {
            eventSink?.success(map)
        }
    }
}