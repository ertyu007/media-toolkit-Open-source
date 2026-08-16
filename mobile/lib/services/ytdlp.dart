import 'dart:async';

import 'package:flutter/services.dart';

class YtDlpService {
  YtDlpService._();
  static final YtDlpService instance = YtDlpService._();

  static const _channel = MethodChannel('com.clipora/ytdlp');
  static const _events = EventChannel('com.clipora/ytdlp/events');

  final _controller = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get events => _controller.stream;

  bool _listening = false;
  bool _initialized = false;

  Future<void> init() async {
    _listen();
    if (!_initialized) {
      await _channel.invokeMethod('init');
      _initialized = true;
    }
  }

  void _listen() {
    if (_listening) return;
    _listening = true;
    _events.receiveBroadcastStream().listen((data) {
      _controller.add(Map<String, dynamic>.from(data as Map));
    });
  }

  Future<void> download(
    String id,
    String url,
    String outputTemplate,
    List<String> options,
  ) =>
      _channel.invokeMethod('download', {
        'id': id,
        'url': url,
        'outputTemplate': outputTemplate,
        'options': options,
      });

  Future<void> cancel(String id) => _channel.invokeMethod('cancel', {'id': id});
}