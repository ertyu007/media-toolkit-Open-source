import 'dart:async';

import 'package:ffmpeg_kit_flutter_new/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new/ffprobe_kit.dart';
import 'package:ffmpeg_kit_flutter_new/return_code.dart';

import '../models/media_metadata.dart';

class MediaInfo {
  final double? duration;
  final bool hasVideo;
  final bool hasAudio;
  final String? videoCodec;
  final String? audioCodec;

  const MediaInfo({
    this.duration,
    required this.hasVideo,
    required this.hasAudio,
    this.videoCodec,
    this.audioCodec,
  });
}

class FfmpegRun {
  final Future<void> completed;
  int? sessionId;
  bool cancelled = false;

  FfmpegRun._(this.completed);
}

Future<MediaInfo> probeMedia(String path) async {
  final session = await FFprobeKit.getMediaInformation(path);
  final info = session.getMediaInformation();
  double? duration;
  try {
    duration = double.tryParse(info?.getDuration() ?? '');
  } catch (_) {
    duration = null;
  }
  var hasVideo = false;
  var hasAudio = false;
  String? videoCodec;
  String? audioCodec;
  for (final stream in info?.getStreams() ?? const []) {
    final type = stream.getType();
    if (type == 'video') {
      hasVideo = true;
      videoCodec ??= stream.getCodec();
    }
    if (type == 'audio') {
      hasAudio = true;
      audioCodec ??= stream.getCodec();
    }
  }
  return MediaInfo(
    duration: duration,
    hasVideo: hasVideo,
    hasAudio: hasAudio,
    videoCodec: videoCodec,
    audioCodec: audioCodec,
  );
}

/// อ่าน metadata (title/artist/album/…) ของไฟล์เสียงผ่าน ffprobe
Future<MediaMetadata> readMetadata(String path) async {
  final session = await FFprobeKit.getMediaInformation(path);
  final info = session.getMediaInformation();
  final tags = _tagsOf(info?.getTags());

  String? tag(String key) {
    final v = tags[key];
    if (v == null || v.toString().isEmpty) return null;
    return v.toString();
  }

  var hasCover = false;
  for (final stream in info?.getStreams() ?? const []) {
    final type = stream.getType();
    if (type == 'video') {
      final codec = stream.getCodec()?.toLowerCase() ?? '';
      final mimetype = (_tagsOf(stream.getTags())['mimetype'] ?? '').toString();
      // ภาพหน้าปกที่ฝังในไฟล์เสียงจะเป็น video stream ที่เป็นภาพ (mjpeg/png/…)
      if (codec.contains('jpeg') ||
          codec.contains('png') ||
          codec.contains('bmp') ||
          mimetype.startsWith('image/')) {
        hasCover = true;
        break;
      }
    }
  }

  return MediaMetadata(
    title: tag('title'),
    artist: tag('artist'),
    album: tag('album'),
    albumArtist: tag('album_artist') ?? tag('albumartist'),
    genre: tag('genre'),
    track: _parseTrack(tag('track')),
    year: _parseYear(tag('date') ?? tag('year')),
    hasCover: hasCover,
  );
}

Map<String, dynamic> _tagsOf(Map<dynamic, dynamic>? tags) {
  final out = <String, dynamic>{};
  for (final entry in tags?.entries ?? const <MapEntry>[]) {
    out[entry.key.toString()] = entry.value;
  }
  return out;
}

int? _parseTrack(String? raw) {
  if (raw == null) return null;
  final match = RegExp(r'(\d+)').firstMatch(raw);
  return match == null ? null : int.tryParse(match.group(1)!);
}

int? _parseYear(String? raw) {
  if (raw == null) return null;
  final match = RegExp(r'^\s*(\d{4})').firstMatch(raw);
  return match == null ? null : int.tryParse(match.group(1)!);
}

Future<FfmpegRun> runFfmpeg(
  List<String> args, {
  double? duration,
  void Function(double progress)? onProgress,
}) async {
  final completer = Completer<void>();
  final run = FfmpegRun._(completer.future);
  await FFmpegKit.executeWithArgumentsAsync(
    args,
    (session) async {
      run.sessionId ??= session.getSessionId();
      final code = await session.getReturnCode();
      if (code != null && ReturnCode.isSuccess(code)) {
        completer.complete();
      } else if (code != null && ReturnCode.isCancel(code)) {
        run.cancelled = true;
        completer.complete();
      } else {
        final output = await session.getOutput();
        completer.completeError(StateError(output ?? 'FFmpeg ไม่สำเร็จ'));
      }
    },
    null,
    (statistics) {
      run.sessionId ??= statistics.getSessionId();
      final time = statistics.getTime();
      if (duration != null && duration > 0 && time > 0) {
        final progress = (time / 1000) / duration;
        onProgress?.call(progress.clamp(0.0, 1.0));
      }
    },
  );
  return run;
}

List<String> audioCodecArgs(String format) {
  switch (format.toLowerCase()) {
    case 'mp3':
      return ['-c:a', 'libmp3lame', '-q:a', '2'];
    case 'm4a':
      return ['-c:a', 'aac', '-b:a', '192k'];
    case 'wav':
      return ['-c:a', 'pcm_s16le'];
    case 'flac':
      return ['-c:a', 'flac'];
    case 'opus':
      return ['-c:a', 'libopus', '-b:a', '160k'];
    default:
      throw ArgumentError('ไม่รองรับรูปแบบเสียง: $format');
  }
}

List<String> extractAudioArgs(String source, String target, String format) => [
      '-y',
      '-loglevel',
      'error',
      '-i',
      source,
      '-map',
      '0:a:0',
      '-vn',
      ...audioCodecArgs(format),
      target,
    ];

List<String> videoEncodeArgs(String format, String quality) {
  final container = format.toLowerCase();
  final args = <String>[];
  if (container == 'mp4') {
    const crf = {
      'High': '18', 'Balanced': '23', 'Small': '28',
      'สูงสุด': '18', '2160p': '18', '1080p': '18',
      '720p': '20', '480p': '24', '360p': '26',
    };
    final value = crf[quality];
    if (value == null) throw ArgumentError('ไม่รองรับระดับคุณภาพ: $quality');
    args.addAll([
      '-c:v', 'libx264', '-crf', value, '-preset', 'medium',
      '-c:a', 'aac', '-b:a', '192k',
      '-movflags', '+faststart',
    ]);
  } else if (container == 'mov') {
    const profile = {
      'High': '3', 'Balanced': '2', 'Small': '1',
      'สูงสุด': '3', '2160p': '4', '1080p': '3', '720p': '2',
      '480p': '1', '360p': '1',
    };
    final value = profile[quality];
    if (value == null) throw ArgumentError('ไม่รองรับระดับคุณภาพ: $quality');
    args.addAll([
      '-c:v', 'prores_ks', '-profile:v', value,
      '-pix_fmt', 'yuv422p10le',
      '-c:a', 'pcm_s16le',
    ]);
  } else {
    throw ArgumentError('ไม่รองรับรูปแบบไฟล์วิดีโอ: $format');
  }
  return args;
}

List<String> fpsArgs(String fps) {
  final fpsDigits = fps.replaceAll(RegExp(r'[^0-9]'), '');
  if (fpsDigits.isEmpty) return const [];
  return ['-r', fpsDigits];
}

List<String> convertVideoArgs(
  String source,
  String target,
  String format,
  String quality,
  String fps,
) => [
      '-y',
      '-loglevel',
      'error',
      '-i',
      source,
      '-map',
      '0:v:0',
      '-map',
      '0:a:0?',
      ...videoEncodeArgs(format, quality),
      ...fpsArgs(fps),
      target,
    ];

/// รวมวิดีโอ (ไฟล์แยก) + เสียง แล้ว re-encode ใหม่ทั้งสองสตรีม
/// ใช้เมื่อวิดีโอต้นทางเป็น codec ที่ copy ลง mp4 ไม่ได้ (เช่น vp9/av1)
List<String> mergeAndConvertVideoArgs(
  String videoPath,
  String audioPath,
  String target,
  String format,
  String quality,
  String fps,
) => [
      '-y',
      '-loglevel',
      'error',
      '-i',
      videoPath,
      '-i',
      audioPath,
      '-map',
      '0:v:0',
      '-map',
      '1:a:0?',
      ...videoEncodeArgs(format, quality),
      ...fpsArgs(fps),
      target,
    ];

List<String> mergeIntoMp4Args(String videoPath, String audioPath, String target) => [
      '-y',
      '-loglevel',
      'error',
      '-i',
      videoPath,
      '-i',
      audioPath,
      '-map',
      '0:v:0',
      '-map',
      '1:a:0?',
      '-c:v',
      'copy',
      '-c:a',
      'aac',
      '-b:a',
      '192k',
      '-movflags',
      '+faststart',
      target,
    ];

List<String> remuxToMp4Args(String source, String target) => [
      '-y',
      '-loglevel',
      'error',
      '-i',
      source,
      '-map',
      '0:v:0',
      '-map',
      '0:a:0?',
      '-c',
      'copy',
      '-movflags',
      '+faststart',
      target,
    ];

/// วิดีโอ/เสียงที่ copy ไปใส่ mp4 container ได้ตรง ๆ โดยไม่ต้อง re-encode
/// (ถ้าไม่ตรงเงื่อนไขนี้ ต้อง re-encode ไม่งั้น output จะเสีย/ไม่เล่น)
bool canCopyToMp4(MediaInfo info) {
  const copySafeVideo = {'h264', 'hevc', 'h265', 'mpeg4'};
  const copySafeAudio = {'aac', 'mp3', 'mp4a'};
  final video = info.videoCodec?.toLowerCase();
  if (video == null || !copySafeVideo.contains(video)) return false;
  final audio = info.audioCodec?.toLowerCase();
  if (audio == null) return true;
  return copySafeAudio.contains(audio);
}

/// สร้าง ffmpeg args สำหรับเขียน metadata ลงไฟล์เสียง
/// (copy stream เดิม ไม่ re-encode เปลี่ยนคุณภาพ)
List<String> writeMetadataArgs(
  String source,
  String target,
  MediaMetadata meta, {
  String? coverPath,
}) {
  final ext = _extOf(target);
  final args = <String>[
    '-y',
    '-loglevel',
    'error',
    if (coverPath != null) ...[
      '-i',
      coverPath,
    ],
    '-i',
    source,
  ];
  if (coverPath != null) {
    // audio = input 1, cover = input 0
    args.addAll([
      '-map', '0:v:0',
      '-map', '1:a:0?',
      '-c:v', 'copy',
      '-c:a', 'copy',
      '-disposition:v:0', 'attached_pic',
    ]);
  } else {
    args.addAll([
      '-map', '0:a:0?',
      '-c:a', 'copy',
    ]);
  }
  if (ext == 'mp3') {
    args.addAll(['-id3v2_version', '3']);
  }
  args.addAll(_metadataArgs(meta, coverPath != null));
  args.add(target);
  return args;
}

List<String> _metadataArgs(MediaMetadata meta, bool hasCoverStream) {
  final args = <String>[];
  void put(String key, String? value) {
    if (value == null || value.trim().isEmpty) return;
    args.addAll(['-metadata', '$key=${value.trim()}']);
  }

  put('title', meta.title);
  put('artist', meta.artist);
  put('album', meta.album);
  put('album_artist', meta.albumArtist);
  put('genre', meta.genre);
  if (meta.track != null) put('track', meta.track.toString());
  if (meta.year != null) put('date', meta.year.toString());
  if (hasCoverStream) {
    args.addAll([
      '-metadata:s:v', 'title=Album cover',
      '-metadata:s:v', 'comment=Cover (front)',
    ]);
  }
  return args;
}

String _extOf(String path) {
  final dot = path.lastIndexOf('.');
  return dot == -1 ? '' : path.substring(dot + 1).toLowerCase();
}