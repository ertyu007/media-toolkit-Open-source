import 'dart:io';

import 'package:flutter/material.dart';

import '../app_state.dart';
import '../models/media_metadata.dart';
import '../services/media.dart';
import '../services/native.dart';
import '../widgets/ui.dart';

class MetadataEditorScreen extends StatefulWidget {
  final File? initialFile;

  const MetadataEditorScreen({super.key, this.initialFile});

  @override
  State<MetadataEditorScreen> createState() => _MetadataEditorScreenState();
}

class _MetadataEditorScreenState extends State<MetadataEditorScreen> {
  final AppState app = AppState.instance;

  File? _file;
  MediaMetadata? _meta;
  String? _coverPath;
  bool _busy = false;

  final _title = TextEditingController();
  final _artist = TextEditingController();
  final _album = TextEditingController();
  final _albumArtist = TextEditingController();
  final _genre = TextEditingController();
  final _track = TextEditingController();
  final _year = TextEditingController();

  @override
  void initState() {
    super.initState();
    if (widget.initialFile != null) {
      _file = widget.initialFile;
      _load();
    }
  }

  @override
  void dispose() {
    _title.dispose();
    _artist.dispose();
    _album.dispose();
    _albumArtist.dispose();
    _genre.dispose();
    _track.dispose();
    _year.dispose();
    super.dispose();
  }

  bool get _isAudioExt {
    final ext = _file?.path.toLowerCase().split('.').last ?? '';
    return const {'mp3', 'm4a', 'flac', 'opus', 'wav', 'aac', 'ogg'}
        .contains(ext);
  }

  Future<void> _pick() async {
    if (_busy) return;
    try {
      final path = await NativeService.instance.pickMediaFile();
      if (path == null) return;
      if (!mounted) return;
      setState(() {
        _file = File(path);
        _coverPath = null;
      });
      await _load();
    } catch (e) {
      if (!mounted) return;
      showToast(context, 'เลือกไฟล์ไม่สำเร็จ: $e', bad: true);
    }
  }

  Future<void> _load() async {
    final file = _file;
    if (file == null) return;
    setState(() => _busy = true);
    try {
      final meta = await readMetadata(file.path);
      if (!mounted) return;
      setState(() {
        _meta = meta;
        _title.text = meta.title ?? '';
        _artist.text = meta.artist ?? '';
        _album.text = meta.album ?? '';
        _albumArtist.text = meta.albumArtist ?? '';
        _genre.text = meta.genre ?? '';
        _track.text = meta.track?.toString() ?? '';
        _year.text = meta.year?.toString() ?? '';
      });
    } catch (e) {
      showToast(context, 'อ่าน metadata ไม่สำเร็จ: $e', bad: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickCover() async {
    try {
      final path = await NativeService.instance.pickImageFile();
      if (path == null) return;
      if (!mounted) return;
      setState(() => _coverPath = path);
    } catch (e) {
      showToast(context, 'เลือกรูปไม่สำเร็จ: $e', bad: true);
    }
  }

  MediaMetadata _collect() => MediaMetadata(
        title: _title.text.trim().isEmpty ? null : _title.text.trim(),
        artist: _artist.text.trim().isEmpty ? null : _artist.text.trim(),
        album: _album.text.trim().isEmpty ? null : _album.text.trim(),
        albumArtist: _albumArtist.text.trim().isEmpty
            ? null
            : _albumArtist.text.trim(),
        genre: _genre.text.trim().isEmpty ? null : _genre.text.trim(),
        track: int.tryParse(_track.text.trim()),
        year: int.tryParse(_year.text.trim()),
      );

  Future<void> _save() async {
    final file = _file;
    if (file == null) return;
    if (!_isAudioExt) {
      showToast(context, 'แก้ metadata ได้เฉพาะไฟล์เสียง (mp3/m4a/flac/opus)',
          bad: true);
      return;
    }
    setState(() => _busy = true);
    try {
      await app.editMetadata(
        source: file,
        metadata: _collect(),
        coverPath: _coverPath,
      );
      if (!mounted) return;
      showToast(context, 'บันทึก metadata เรียบร้อย (อยู่ใน Downloads/Clipora)');
    } catch (e) {
      showToast(context, 'บันทึกไม่สำเร็จ: $e', bad: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: kBg,
        title: const Text('แก้ไข metadata เพลง'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            _filePicker(),
            if (_file != null) ...[
              const SizedBox(height: 12),
              cliporaCard(Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_meta?.hasCover ?? false) ...[
                    Row(
                      children: const [
                        Icon(Icons.image, size: 16, color: kAccent),
                        SizedBox(width: 6),
                        Text('ไฟล์นี้มีหน้าปกอยู่แล้ว',
                            style: TextStyle(fontSize: 12, color: Colors.white54)),
                      ],
                    ),
                    const SizedBox(height: 8),
                  ],
                  _textField(_title, 'ชื่อเพลง (title)'),
                  _textField(_artist, 'ศิลปิน (artist)'),
                  _textField(_album, 'อัลบั้ม (album)'),
                  _textField(_albumArtist, 'ศิลปินอัลบั้ม (album artist)'),
                  _textField(_genre, 'แนวเพลง (genre)'),
                  Row(
                    children: [
                      Expanded(
                        child: _textField(_track, 'ลำดับแทร็ก (เช่น 1)',
                            numeric: true),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _textField(_year, 'ปี (เช่น 2024)',
                            numeric: true),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _coverRow(),
                  const SizedBox(height: 16),
                  primaryButton(
                    icon: const Icon(Icons.save),
                    label: Text(_busy ? 'กำลังบันทึก…' : 'บันทึก metadata'),
                    onPressed: _busy ? null : _save,
                  ),
                ],
              )),
            ],
          ],
        ),
      ),
    );
  }

  Widget _filePicker() {
    final file = _file;
    return cliporaCard(Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        fieldLabel('ไฟล์เสียง'),
        GestureDetector(
          onTap: _busy ? null : _pick,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: file != null ? kAccent : Colors.white12),
            ),
            child: Column(
              children: [
                Icon(
                  file != null ? Icons.music_note : Icons.audio_file_outlined,
                  color: file != null ? kAccent : Colors.white38,
                  size: 32,
                ),
                const SizedBox(height: 8),
                Text(
                  file != null
                      ? '${file.uri.pathSegments.last}\n'
                          '(${formatBytes(file.lengthSync())})'
                      : 'แตะเพื่อเลือกไฟล์เสียง (mp3/m4a/flac/opus)',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 13,
                    color: file != null ? Colors.white : Colors.white54,
                  ),
                ),
              ],
            ),
          ),
        ),
        if (file != null && !_isAudioExt)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text(
              'ไฟล์ที่เลือกไม่ใช่ไฟล์เสียง — กรุณาเลือก mp3/m4a/flac/opus',
              style: TextStyle(fontSize: 12, color: Color(0xFFFF8A80)),
            ),
          ),
      ],
    ));
  }

  Widget _coverRow() {
    final hasCover = _coverPath != null;
    return Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            onPressed: _pickCover,
            icon: Icon(hasCover ? Icons.image : Icons.add_photo_alternate,
                size: 18),
            label: Text(
              hasCover ? 'เปลี่ยนหน้าปก (${_coverName()})' : 'แนบหน้าปก',
              style: const TextStyle(fontSize: 13),
            ),
          ),
        ),
        if (hasCover) ...[
          const SizedBox(width: 8),
          IconButton(
            onPressed: () => setState(() => _coverPath = null),
            icon: const Icon(Icons.close, size: 18),
            tooltip: 'ลบหน้าปก',
          ),
        ],
      ],
    );
  }

  String _coverName() {
    final path = _coverPath;
    if (path == null) return '';
    return path.split('/').last.split('\\').last;
  }

  Widget _textField(TextEditingController controller, String label,
      {bool numeric = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: controller,
        enabled: !_busy,
        keyboardType: numeric ? TextInputType.number : TextInputType.text,
        style: const TextStyle(fontSize: 15),
        decoration: InputDecoration(
          labelText: label,
          filled: true,
          fillColor: kSurface2,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: BorderSide.none,
          ),
        ),
      ),
    );
  }
}