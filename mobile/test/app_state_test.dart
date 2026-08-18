import 'package:clipora_mobile/app_state.dart';
import 'package:clipora_mobile/models/media_metadata.dart';
import 'package:clipora_mobile/services/media.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('buildVideoFormat', () {
    test('prefers H.264 (avc) video before HEVC', () {
      final f = AppState.buildVideoFormat('สูงสุด', 'สูงสุด');
      expect(f.startsWith('bv[ext=mp4][vcodec^=avc],ba[ext=m4a]'), isTrue);
    });

    test('never asks yt-dlp to merge (no "+" since no ffmpeg on device)', () {
      final f = AppState.buildVideoFormat('สูงสุด', 'สูงสุด');
      expect(f.contains('+'), isFalse);
    });

    test('keeps height and fps filters', () {
      final f = AppState.buildVideoFormat('1080p', '30');
      expect(f.contains('[height<=1080]'), isTrue);
      expect(f.contains('[fps<=30]'), isTrue);
    });

    test('keeps combined-format fallback chain', () {
      final f = AppState.buildVideoFormat('สูงสุด', 'สูงสุด');
      expect(f.endsWith('/b'), isTrue);
    });
  });

  group('siteWorkaroundHeaders', () {
    test('adds TikTok referer header for tiktok.com URLs', () {
      final h = AppState.siteWorkaroundHeaders('https://www.tiktok.com/@x/video/123');
      expect(h, ['--add-header', 'Referer:https://www.tiktok.com/']);
    });

    test('adds TikTok referer header for short tiktok URLs', () {
      final h = AppState.siteWorkaroundHeaders('https://vt.tiktok.com/abc/');
      expect(h, ['--add-header', 'Referer:https://www.tiktok.com/']);
    });

    test('returns no extra options for non-TikTok URLs', () {
      final h = AppState.siteWorkaroundHeaders('https://www.youtube.com/watch?v=abc');
      expect(h, isEmpty);
    });
  });

  group('writeMetadataArgs', () {
    test('writes fields with -metadata without re-encoding', () {
      final args = writeMetadataArgs(
        'in.mp3',
        'out.mp3',
        const MediaMetadata(
          title: 'ชื่อเพลง',
          artist: 'ศิลปิน',
          album: 'อัลบั้ม',
          genre: 'Pop',
          track: 3,
          year: 2024,
        ),
      );
      expect(args, contains('out.mp3'));
      expect(args.join(' '), contains('-c:a copy'));
      expect(args.join(' '), contains('title=ชื่อเพลง'));
      expect(args.join(' '), contains('artist=ศิลปิน'));
      expect(args.join(' '), contains('track=3'));
      expect(args.join(' '), contains('date=2024'));
      expect(args.join(' '), contains('-id3v2_version'));
    });

    test('omits empty fields', () {
      final args = writeMetadataArgs(
        'in.m4a',
        'out.m4a',
        const MediaMetadata(title: '  '),
      );
      expect(args.join(' ').contains('title='), isFalse);
    });

    test('maps cover image as input 0 with attached_pic', () {
      final args = writeMetadataArgs(
        'in.flac',
        'out.flac',
        const MediaMetadata(title: 't'),
        coverPath: 'cover.jpg',
      );
      final joined = args.join(' ');
      expect(joined, contains('-i cover.jpg'));
      expect(joined, contains('attached_pic'));
      expect(joined, contains('Cover (front)'));
      // ต้อง copy ทั้งวิดีโอ(หน้าปก) และเสียง ไม่ให้ re-encode ลดคุณภาพ
      expect(joined, contains('-c:v copy'));
      expect(joined, contains('-c:a copy'));
    });
  });
}