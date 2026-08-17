import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:ffmpeg_kit_flutter_new/ffmpeg_kit.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../models/job.dart';
import 'services/media.dart';
import 'services/native.dart';
import 'services/ytdlp.dart';

class AppState extends ChangeNotifier {
  AppState._();
  static final AppState instance = AppState._();

  final List<Job> _jobs = [];
  List<Job> get jobs => List.unmodifiable(_jobs);

  bool initialized = false;
  String? initError;

  /// การตั้งค่าที่ผู้ใช้เลือกไว้ล่าสุด (เก็บเป็น JSON ข้ามครั้ง)
  final Map<String, dynamic> settings = {};

  Future<String> _settingsFile() async {
    final dir = Directory('${await _appDir()}/clipora');
    await dir.create(recursive: true);
    return '${dir.path}/settings.json';
  }

  Future<void> loadSettings() async {
    try {
      final f = File(await _settingsFile());
      if (f.existsSync()) {
        final json = jsonDecode(f.readAsStringSync());
        if (json is Map<String, dynamic>) {
          settings
            ..clear()
            ..addAll(json);
        }
      }
    } catch (_) {}
  }

  Future<void> saveSettings() async {
    try {
      final f = File(await _settingsFile());
      await f.writeAsString(jsonEncode(settings));
    } catch (_) {}
  }

  String setting(String key, String fallback) =>
      settings[key] is String ? settings[key] as String : fallback;

  bool settingBool(String key, bool fallback) =>
      settings[key] is bool ? settings[key] as bool : fallback;

  void setSetting(String key, Object value) {
    settings[key] = value;
    saveSettings();
  }

  final Map<String, FfmpegRun> _ffmpegRuns = {};

  Future<void> init() async {
    try {
      await YtDlpService.instance.init();
      initialized = true;
    } catch (e) {
      initError = 'ไม่สามารถเริ่มต้นระบบได้: ${e.toString()}';
    }
    await loadSettings();
    notifyListeners();
  }

  Future<String> _appDir() async {
    final dir = await getExternalStorageDirectory();
    return dir?.path ?? (await getApplicationDocumentsDirectory()).path;
  }

  String _newId() =>
      'job-${DateTime.now().millisecondsSinceEpoch}-${_jobs.length}';

  Job _addJob(JobKind kind, JobMode mode, String name) {
    final job = Job(
      id: _newId(),
      kind: kind,
      mode: mode,
      status: JobStatus.running,
      message: kind == JobKind.url ? 'กำลังตรวจสอบลิงก์…' : 'กำลังเตรียมไฟล์…',
      resultName: name,
    );
    _jobs.insert(0, job);
    notifyListeners();
    return job;
  }

  // ---------------- URL download ----------------

  Future<void> startUrlDownload({
    required String url,
    required JobMode mode,
    required String videoFormat,
    required String quality,
    required String fps,
    required String audioFormat,
    bool playlist = false,
  }) async {
    final job = _addJob(JobKind.url, mode, url);
    job.retryUrl = url;
    job.retryVideoFormat = videoFormat;
    job.retryQuality = quality;
    job.retryFps = fps;
    job.retryAudioFormat = audioFormat;
    job.retryPlaylist = playlist;
    try {
      final baseDir = Directory('${await _appDir()}/clipora/dl/${job.id}');
      await baseDir.create(recursive: true);
      // ใส่ %(format_id)s เพื่อไม่ให้ไฟล์วิดีโอ/เสียง (โหลดแยกกัน) เขียนทับกัน
      final outputTemplate =
          '${baseDir.path}/%(title).160B [%(id)s].%(format_id)s.%(ext)s';

      final options = <String>[];
      if (mode == JobMode.audio) {
        options.addAll(['-f', 'bestaudio/best']);
      } else {
        options.addAll(['-f', buildVideoFormat(quality, fps)]);
      }
      if (!playlist) {
        options.add('--no-playlist');
      }

      final ok = await _runYtDlp(job, url, outputTemplate, options);
      if (!ok) {
        if (job.status != JobStatus.cancelled) {
          job.status = JobStatus.failed;
        }
        notifyListeners();
        return;
      }

      await _postProcessUrlJob(
        job,
        baseDir,
        mode: mode,
        videoFormat: videoFormat,
        quality: quality,
        fps: fps,
        audioFormat: audioFormat,
      );
    } catch (e) {
      if (job.status != JobStatus.cancelled) {
        job.status = JobStatus.failed;
        job.error = e is TimeoutException ? 'หมดเวลาดาวน์โหลด' : e.toString();
      }
      notifyListeners();
    }
  }

  Future<bool> _runYtDlp(
    Job job,
    String url,
    String outputTemplate,
    List<String> options,
  ) async {
    final completer = Completer<bool>();
    late final StreamSubscription sub;
    sub = YtDlpService.instance.events.listen((event) {
      if (event['id'] != job.id) return;
      switch (event['type']) {
        case 'progress':
          final raw = (event['progress'] as num?)?.toDouble() ?? 0;
          final p = raw.clamp(0.0, 1.0);
          job.progress = p * 0.85;
          job.etaSeconds = (event['eta'] as num?)?.toInt();
          job.message = 'กำลังดาวน์โหลด… ${(p * 100).toStringAsFixed(0)}%';
          notifyListeners();
          break;
        case 'done':
          sub.cancel();
          if (!completer.isCompleted) completer.complete(true);
          break;
        case 'cancelled':
          sub.cancel();
          job.status = JobStatus.cancelled;
          if (!completer.isCompleted) completer.complete(false);
          break;
        case 'error':
          sub.cancel();
          job.error = event['message'] as String? ?? 'ดาวน์โหลดไม่สำเร็จ';
          if (!completer.isCompleted) completer.complete(false);
          break;
      }
    });

    try {
      await YtDlpService.instance.download(job.id, url, outputTemplate, options);
    } catch (e) {
      sub.cancel();
      job.error = e.toString();
      if (!completer.isCompleted) completer.complete(false);
      return false;
    }
    try {
      return await completer.future.timeout(const Duration(minutes: 60));
    } on TimeoutException {
      sub.cancel();
      // ต้องยกเลิกงานฝั่ง native ด้วย ไม่งั้น yt-dlp ยังดาวน์โหลดค้างอยู่เบื้องหลัง
      await YtDlpService.instance.cancel(job.id);
      job.error = 'หมดเวลาดาวน์โหลด';
      return false;
    }
  }

  @visibleForTesting
  static String buildVideoFormat(String quality, String fps) {
    final height = switch (quality) {
      '2160p' => 2160,
      '1080p' => 1080,
      '720p' => 720,
      '480p' => 480,
      '360p' => 360,
      _ => null,
    };
    final fpsDigits = fps.replaceAll(RegExp(r'[^0-9]'), '');
    final fpsFilter = fpsDigits.isNotEmpty ? '[fps<=$fpsDigits]' : '';
    final heightFilter = height != null ? '[height<=$height]' : '';
    // yt-dlp ฝั่ง Android ไม่มี ffmpeg → ห้ามใช้ '+' (สั่งให้ yt-dlp merge เอง)
    // โหลดวิดีโอ+เสียงเป็นไฟล์แยก (คั่นด้วย ,) แล้ว app รวมด้วย ffmpeg-kit
    // เลือก H.264 (avc) ก่อน เพราะ TikTok/YouTube ส่ง HEVC (bytevc1) เป็น "ดีที่สุด"
    // แต่เล่นยากกว่า เลือก mp4+h264/m4a เป็นหลัก
    return 'bv[ext=mp4][vcodec^=avc]$heightFilter$fpsFilter,ba[ext=m4a]'
        '/bv[ext=mp4]$heightFilter$fpsFilter,ba'
        '/bv,ba'
        '/b[ext=mp4][vcodec^=avc]$heightFilter$fpsFilter'
        '/b[ext=mp4]$heightFilter$fpsFilter'
        '/b';
  }

  List<File> _validFiles(Directory dir) => dir
      .listSync()
      .whereType<File>()
      .where((f) =>
          f.existsSync() &&
          f.lengthSync() > 0 &&
          !f.path.toLowerCase().endsWith('.part'))
      .toList();

  Future<(List<File>, List<File>)> _classifyFiles(List<File> files) async {
    final videos = <File>[];
    final audios = <File>[];
    for (final f in files) {
      try {
        final info = await probeMedia(f.path);
        if (info.hasVideo) {
          videos.add(f);
        } else if (info.hasAudio) {
          audios.add(f);
        }
      } catch (_) {
        // ไฟล์ที่ probe ไม่ได้ (เช่น .part ค้าง) ข้ามไป
      }
    }
    return (videos, audios);
  }

  Future<void> _postProcessUrlJob(
    Job job,
    Directory dir, {
    required JobMode mode,
    required String videoFormat,
    required String quality,
    required String fps,
    required String audioFormat,
  }) async {
    final files = _validFiles(dir);
    if (files.isEmpty) {
      throw StateError('ดาวน์โหลดเสร็จแต่ไม่พบไฟล์ผลลัพธ์');
    }
    job.message = 'กำลังประมวลผล…';
    job.progress = 0.85;
    job.etaSeconds = null;
    notifyListeners();

    File finalFile;
    if (mode == JobMode.audio) {
      final source = await _firstFileWithAudio(files);
      final info = await probeMedia(source.path);
      final target = _uniquePath('${dir.path}/audio', audioFormat);
      final run = await _trackFfmpeg(job, extractAudioArgs(
        source.path,
        target,
        audioFormat,
      ), duration: info.duration, onProgress: (p) {
        job.progress = 0.85 + p * 0.15;
        notifyListeners();
      });
      await run.completed;
      if (run.cancelled) return;
      finalFile = File(target);
    } else {
      final (videos, audios) = await _classifyFiles(files);
      if (videos.length > 1) {
        throw StateError('พบไฟล์วิดีโอมากกว่า 1 ไฟล์');
      }
      if (videos.isEmpty) {
        throw StateError('ไม่พบวิดีโอในผลลัพธ์ที่ดาวน์โหลด');
      }
      final video = videos.first;

      if (videoFormat == 'mov') {
        final merged = audios.isNotEmpty
            ? await _mergeToFile(job, dir, video, audios.first,
                'merged', 'mp4', quality, fps)
            : video;
        if (job.status == JobStatus.cancelled) return;
        final info = await probeMedia(merged.path);
        final target = _uniquePath('${dir.path}/result', 'mov');
        final run = await _trackFfmpeg(job, convertVideoArgs(
          merged.path,
          target,
          'mov',
          quality,
          fps,
        ), duration: info.duration, onProgress: (p) {
          job.progress = 0.92 + p * 0.08;
          notifyListeners();
        });
        await run.completed;
        if (run.cancelled) return;
        finalFile = File(target);
      } else if (audios.isNotEmpty) {
        finalFile =
            await _mergeToFile(job, dir, video, audios.first,
                'result', 'mp4', quality, fps);
        if (job.status == JobStatus.cancelled) return;
      } else {
        final target = _uniquePath('${dir.path}/result', 'mp4');
        if (video.path.toLowerCase().endsWith('.mp4')) {
          video.copySync(target);
          finalFile = File(target);
        } else {
          final info = await probeMedia(video.path);
          final args = canCopyToMp4(info)
              ? remuxToMp4Args(video.path, target)
              : convertVideoArgs(video.path, target, 'mp4', quality, fps);
          final run = await _trackFfmpeg(job, args,
              duration: info.duration, onProgress: (p) {
            job.progress = 0.85 + p * 0.15;
            notifyListeners();
          });
          await run.completed;
          if (run.cancelled) return;
          finalFile = File(target);
        }
      }
    }

    await _finalizeJob(job, finalFile);
  }

  /// รวมวิดีโอ+เสียง โดย copy ถ้า codec วิดีโอใส่ mp4 ได้
  /// ไม่เช่นนั้น re-encode ใหม่ (เช่น vp9/av1 จากเว็บ)
  Future<File> _mergeToFile(
    Job job,
    Directory dir,
    File video,
    File audio,
    String name,
    String ext,
    String quality,
    String fps,
  ) async {
    final info = await probeMedia(video.path);
    final target = _uniquePath('${dir.path}/$name', ext);
    final args = canCopyToMp4(info)
        ? mergeIntoMp4Args(video.path, audio.path, target)
        : mergeAndConvertVideoArgs(
            video.path, audio.path, target, 'mp4', quality, fps);
    final run = await _trackFfmpeg(job, args,
        duration: info.duration, onProgress: (p) {
      job.progress = 0.85 + p * 0.15;
      notifyListeners();
    });
    await run.completed;
    return File(target);
  }

  Future<File> _firstFileWithAudio(List<File> files) async {
    for (final f in files) {
      if ((await probeMedia(f.path)).hasAudio) return f;
    }
    throw StateError('ไฟล์นี้ไม่มีเสียงให้แยก');
  }

  // ---------------- File conversion ----------------

  Future<void> startFileJob({
    required File source,
    required JobMode mode,
    required String videoFormat,
    required String quality,
    required String fps,
    required String audioFormat,
  }) async {
    final job = _addJob(JobKind.file, mode, source.uri.pathSegments.last);
    try {
      final workDir = Directory('${await _appDir()}/clipora/work/${job.id}');
      await workDir.create(recursive: true);
      final workFile =
          File('${workDir.path}/source${_extensionOf(source.path)}');
      job.retrySourcePath = workFile.path;
      job.retryVideoFormat = videoFormat;
      job.retryQuality = quality;
      job.retryFps = fps;
      job.retryAudioFormat = audioFormat;
      job.message = 'กำลังคัดลอกไฟล์…';
      notifyListeners();
      await source.copy(workFile.path);

      final info = await probeMedia(workFile.path);
      final ext = mode == JobMode.audio ? audioFormat : videoFormat;
      if (mode == JobMode.audio && !info.hasAudio) {
        throw StateError('ไฟล์นี้ไม่มีเสียงให้แยก');
      }
      if (mode == JobMode.video && !info.hasVideo) {
        throw StateError('ไฟล์นี้ไม่มีภาพวิดีโอสำหรับแปลง');
      }
      final target = '${workDir.path}/output.$ext';
      job.message = 'กำลังแปลงไฟล์…';
      job.progress = 0;
      notifyListeners();

      final args = mode == JobMode.audio
          ? extractAudioArgs(workFile.path, target, audioFormat)
          : convertVideoArgs(workFile.path, target, videoFormat, quality, fps);
      final run = await _trackFfmpeg(job, args, duration: info.duration,
        onProgress: (p) {
          job.progress = p;
          notifyListeners();
        });
      await run.completed;
      if (run.cancelled) return;
      await _finalizeJob(job, File(target));
    } catch (e) {
      if (job.status != JobStatus.cancelled) {
        job.status = JobStatus.failed;
        job.error = e.toString();
      }
      notifyListeners();
    }
  }

  Future<FfmpegRun> _trackFfmpeg(
    Job job,
    List<String> args, {
    double? duration,
    void Function(double)? onProgress,
  }) async {
    final run = await runFfmpeg(args, duration: duration, onProgress: onProgress);
    _ffmpegRuns[job.id] = run;
    run.completed.whenComplete(() => _ffmpegRuns.remove(job.id));
    return run;
  }

  // ---------------- finalize / cancel / share ----------------

  Future<void> _finalizeJob(Job job, File file) async {
    if (job.status == JobStatus.cancelled) return;
    if (!file.existsSync() || file.lengthSync() == 0) {
      throw StateError('ไฟล์ผลลัพธ์ไม่สมบูรณ์');
    }
    job.message = 'กำลังบันทึกไฟล์…';
    job.progress = 1.0;
    notifyListeners();
    final name = file.uri.pathSegments.last;
    try {
      await NativeService.instance
          .saveToDownloads(file.path, name, _mimeOf(name));
    } catch (_) {
      // ผลลัพธ์ยังอยู่ในโฟลเดอร์แอป ใช้งานแชร์ได้
    }
    job.status = JobStatus.done;
    job.resultPath = file.path;
    job.resultName = name;
    job.message = '';
    job.progress = 1.0;
    notifyListeners();
  }

  Future<void> cancelJob(Job job) async {
    if (job.status != JobStatus.running) return;
    if (job.kind == JobKind.url) {
      await YtDlpService.instance.cancel(job.id);
    }
    final run = _ffmpegRuns[job.id];
    if (run?.sessionId != null) {
      await FFmpegKit.cancel(run!.sessionId);
    }
    job.status = JobStatus.cancelled;
    notifyListeners();
  }

  /// ลองทำงานที่ล้มเหลวใหม่ด้วยพารามิเตอร์เดิม (ลบงานเก่าแล้วสร้างงานใหม่)
  Future<void> retryJob(Job job) async {
    final url = job.retryUrl;
    final src = job.retrySourcePath;
    final mode = job.mode;
    final vf = job.retryVideoFormat ?? 'mp4';
    final q = job.retryQuality ?? (job.kind == JobKind.url ? 'สูงสุด' : 'Balanced');
    final f = job.retryFps ?? 'สูงสุด';
    final af = job.retryAudioFormat ?? 'mp3';
    final playlist = job.retryPlaylist;
    removeJob(job);
    if (job.kind == JobKind.url && url != null) {
      await startUrlDownload(
        url: url,
        mode: mode,
        videoFormat: vf,
        quality: q,
        fps: f,
        audioFormat: af,
        playlist: playlist,
      );
    } else if (src != null) {
      await startFileJob(
        source: File(src),
        mode: mode,
        videoFormat: vf,
        quality: q,
        fps: f,
        audioFormat: af,
      );
    }
  }

  Future<void> shareJob(Job job) async {
    final path = job.resultPath;
    if (path == null) return;
    final file = File(path);
    if (!file.existsSync()) return;
    await SharePlus.instance.share(ShareParams(
      files: [XFile(file.path, mimeType: _mimeOf(file.uri.pathSegments.last))],
      text: job.resultName ?? 'Clipora',
    ));
  }

  void removeJob(Job job) {
    _jobs.removeWhere((j) => j.id == job.id);
    // ลบไฟล์งานออกจากเครื่องด้วย ไม่ให้เหลือขยะสะสมในเครื่อง
    _deleteJobDir(job);
    notifyListeners();
  }

  Future<void> _deleteJobDir(Job job) async {
    try {
      final sub = job.kind == JobKind.url ? 'dl' : 'work';
      final dir = Directory('${await _appDir()}/clipora/$sub/${job.id}');
      if (dir.existsSync()) await dir.delete(recursive: true);
    } catch (_) {}
  }

  String _uniquePath(String base, String ext) {
    var target = '$base.$ext';
    var index = 1;
    while (File(target).existsSync()) {
      target = '$base ($index).$ext';
      index += 1;
    }
    return target;
  }

  String _extensionOf(String path) {
    final dot = path.lastIndexOf('.');
    if (dot == -1) return '';
    return path.substring(dot);
  }

  String _mimeOf(String name) {
    final ext = name.split('.').last.toLowerCase();
    return switch (ext) {
      'mp3' => 'audio/mpeg',
      'm4a' => 'audio/mp4',
      'wav' => 'audio/wav',
      'flac' => 'audio/flac',
      'opus' => 'audio/opus',
      'mov' => 'video/quicktime',
      'webm' => 'video/webm',
      _ => 'video/mp4',
    };
  }
}