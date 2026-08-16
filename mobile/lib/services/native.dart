import 'package:flutter/services.dart';

class NativeService {
  NativeService._();
  static final NativeService instance = NativeService._();

  static const _channel = MethodChannel('com.clipora/native');

  /// เปิดตัวเลือกไฟล์วิดีโอในเครื่อง คัดลอกไปยังแคช แล้วคืน path
  /// คืน `null` ถ้าผู้ใช้ยกเลิก
  Future<String?> pickMediaFile() async {
    final path = await _channel.invokeMethod('pickMediaFile');
    return path as String?;
  }

  /// บันทึกไฟล์ไปยังโฟลเดอร์ Downloads/Clipora สาธารณะ คืน content Uri
  Future<String> saveToDownloads(
    String sourcePath,
    String displayName,
    String mimeType,
  ) async {
    final uri = await _channel.invokeMethod('saveToDownloads', {
      'sourcePath': sourcePath,
      'displayName': displayName,
      'mimeType': mimeType,
    });
    return uri as String;
  }
}