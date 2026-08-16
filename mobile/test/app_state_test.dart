import 'dart:io';

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

  group('looksLikeNetscapeCookies', () {
    late Directory dir;
    late File file;

    setUp(() {
      dir = Directory.systemTemp.createTempSync('clipora_cookie_test');
      file = File('${dir.path}/cookies.txt');
    });

    tearDown(() {
      if (dir.existsSync()) dir.deleteSync(recursive: true);
    });

    test('accepts a Netscape cookie file with header', () {
      file.writeAsStringSync(
          '# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tFALSE\t0\tSID\tabc\n');
      expect(AppState.looksLikeNetscapeCookies(file), isTrue);
    });

    test('accepts tab-separated cookie lines without header', () {
      file.writeAsStringSync('.google.com\tTRUE\t/\tFALSE\t2145916800\tNID\tsomevalue\n');
      expect(AppState.looksLikeNetscapeCookies(file), isTrue);
    });

    test('rejects a random text file', () {
      file.writeAsStringSync('hello this is not a cookie file\njust some text\n');
      expect(AppState.looksLikeNetscapeCookies(file), isFalse);
    });

    test('rejects an empty file', () {
      file.writeAsStringSync('');
      expect(AppState.looksLikeNetscapeCookies(file), isFalse);
    });

    test('rejects a file with only comments', () {
      file.writeAsStringSync('# just a comment\n# nothing else\n');
      expect(AppState.looksLikeNetscapeCookies(file), isFalse);
    });
  });
}