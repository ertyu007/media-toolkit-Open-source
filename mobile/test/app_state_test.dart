import 'package:clipora_mobile/app_state.dart';
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
}