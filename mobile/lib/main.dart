import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_state.dart';
import 'models/job.dart';
import 'screens/video_preview.dart';
import 'services/native.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const CliporaApp());
}

class CliporaApp extends StatelessWidget {
  const CliporaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Clipora',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF090D15),
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF4D9DE0),
          brightness: Brightness.dark,
          surface: const Color(0xFF111827),
        ),
        appBarTheme: const AppBarTheme(backgroundColor: Color(0xFF090D15)),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final AppState app = AppState.instance;

  bool _ready = false;
  String? _initError;

  // tabs
  bool _urlTab = true;

  // url mode
  JobMode _urlMode = JobMode.video;
  String _urlFormat = 'mp4';
  String _quality = 'สูงสุด';
  String _fps = 'สูงสุด';
  String _audioFormat = 'mp3';
  bool _authorized = false;
  bool _playlists = false;
  String _url = '';

  // file mode
  JobMode _fileMode = JobMode.video;
  String _fileFormat = 'mp4';
  String _fileQuality = 'Balanced';
  String _fileFps = 'สูงสุด';
  String _fileAudioFormat = 'mp3';
  File? _selectedFile;
  bool _fileBusy = false;

  @override
  void initState() {
    super.initState();
    app.addListener(_onState);
    _bootstrap();
  }

  @override
  void dispose() {
    app.removeListener(_onState);
    super.dispose();
  }

  void _onState() => setState(() {});

  Future<void> _bootstrap() async {
    await app.init();
    if (!mounted) return;
    setState(() {
      _ready = true;
      _initError = app.initError;
      // กู้คืนการตั้งค่าล่าสุดที่ผู้ใช้เคยเลือก
      _urlTab = app.settingBool('urlTab', true);
      _urlMode = app.setting('urlMode', 'video') == 'audio'
          ? JobMode.audio
          : JobMode.video;
      _urlFormat = app.setting('urlFormat', 'mp4');
      _quality = app.setting('quality', 'สูงสุด');
      _fps = app.setting('fps', 'สูงสุด');
      _audioFormat = app.setting('audioFormat', 'mp3');
      _playlists = app.settingBool('playlists', false);
      _fileMode = app.setting('fileMode', 'video') == 'audio'
          ? JobMode.audio
          : JobMode.video;
      _fileFormat = app.setting('fileFormat', 'mp4');
      _fileQuality = app.setting('fileQuality', 'Balanced');
      _fileFps = app.setting('fileFps', 'สูงสุด');
      _fileAudioFormat = app.setting('fileAudioFormat', 'mp3');
    });
  }

  Future<void> _startUrl() async {
    final text = _url.trim();
    if (text.isEmpty) {
      _toast('กรุณาวางลิงก์ก่อน');
      return;
    }
    final uri = Uri.tryParse(text);
    if (uri == null ||
        !uri.hasScheme ||
        !(uri.scheme == 'http' || uri.scheme == 'https')) {
      _toast('กรุณาวางลิงก์ที่ถูกต้อง (ขึ้นต้นด้วย http:// หรือ https://)',
          bad: true);
      return;
    }
    if (!_authorized) {
      _toast('กรุณายืนยันว่าคุณมีสิทธิ์ดาวน์โหลดสื่อนี้', bad: true);
      return;
    }
    setState(() {
      _authorized = false;
      _url = '';
      _urlController.clear();
    });
    await app.startUrlDownload(
      url: text,
      mode: _urlMode,
      videoFormat: _urlFormat,
      quality: _quality,
      fps: _fps,
      audioFormat: _audioFormat,
      playlist: _playlists,
    );
  }

  final _urlController = TextEditingController();

  Future<void> _pickFile() async {
    try {
      final path = await NativeService.instance.pickMediaFile();
      if (path == null) return;
      if (!mounted) return;
      setState(() => _selectedFile = File(path));
    } catch (e) {
      _toast('เลือกไฟล์ไม่สำเร็จ: $e', bad: true);
    }
  }

  Future<void> _startFile() async {
    final file = _selectedFile;
    if (file == null) {
      _toast('กรุณาเลือกไฟล์ก่อน');
      return;
    }
    setState(() => _fileBusy = true);
    try {
      await app.startFileJob(
        source: file,
        mode: _fileMode,
        videoFormat: _fileFormat,
        quality: _fileQuality,
        fps: _fileFps,
        audioFormat: _fileAudioFormat,
      );
    } finally {
      if (mounted) setState(() => _fileBusy = false);
    }
  }

  void _toast(String message, {bool bad = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: bad ? const Color(0xFFB3261E) : null,
      ),
    );
  }

  void _preview(Job job) {
    final path = job.resultPath;
    if (path == null) return;
    final file = File(path);
    if (!file.existsSync()) return;
    final name = job.resultName ?? 'Clipora';
    if (!_isPlayable(name)) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => VideoPreviewScreen(file: file, title: name),
      ),
    );
  }

  bool _isPlayable(String name) {
    final ext = name.split('.').last.toLowerCase();
    return const {
      'mp4', 'mov', 'webm', 'mkv', 'm4v',
      'mp3', 'm4a', 'wav', 'flac', 'opus', 'aac', 'ogg',
    }.contains(ext);
  }

  String _formatBytes(int bytes) {
    if (bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    var value = bytes.toDouble();
    var unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    return unit == 0 ? '$bytes B' : '${value.toStringAsFixed(1)} ${units[unit]}';
  }

  String _formatEta(int seconds) {
    if (seconds <= 0) return '';
    final m = (seconds ~/ 60).toString().padLeft(2, '0');
    final s = (seconds % 60).toString().padLeft(2, '0');
    return 'เหลือประมาณ $m:$s';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: !_ready
            ? const Center(child: CircularProgressIndicator())
            : _initError != null
                ? Center(child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(_initError!, textAlign: TextAlign.center),
                  ))
                : _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    return Column(
      children: [
        _header(),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              _tabSelector(),
              if (_urlTab) _urlPanel() else _filePanel(),
              const SizedBox(height: 8),
              if (app.jobs.isNotEmpty) _jobsSection(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _header() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: const Row(
        children: [
          Icon(Icons.movie_filter, color: Color(0xFF4D9DE0)),
          SizedBox(width: 8),
          Text('Clipora',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }

  Widget _tabSelector() {
    return Row(
      children: [
        Expanded(
          child: _segButton('ลิงก์', _urlTab, () {
            setState(() => _urlTab = true);
            app.setSetting('urlTab', true);
          }),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _segButton('ไฟล์', !_urlTab, () {
            setState(() => _urlTab = false);
            app.setSetting('urlTab', false);
          }),
        ),
      ],
    );
  }

  Widget _segButton(String label, bool active, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: active ? const Color(0xFF1D2A3A) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: active ? const Color(0xFF4D9DE0) : Colors.white12,
          ),
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontWeight: FontWeight.w600,
            color: active ? Colors.white : Colors.white54,
          ),
        ),
      ),
    );
  }

  Widget _modeToggles(JobMode mode, ValueChanged<JobMode> onChanged) {
    return Row(
      children: [
        Expanded(
          child: _miniButton('วิดีโอ', mode == JobMode.video,
              () => onChanged(JobMode.video)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _miniButton('เสียง', mode == JobMode.audio,
              () => onChanged(JobMode.audio)),
        ),
      ],
    );
  }

  Widget _checkRow({
    required bool value,
    required String label,
    required ValueChanged<bool?> onChanged,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Checkbox(value: value, onChanged: onChanged),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(
              label,
              style: const TextStyle(fontSize: 13, color: Colors.white70),
            ),
          ),
        ),
      ],
    );
  }

  Widget _miniButton(String label, bool active, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: active ? const Color(0xFF16202E) : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
              color: active ? const Color(0xFF4D9DE0) : Colors.white12),
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: active ? Colors.white : Colors.white54,
          ),
        ),
      ),
    );
  }

  Widget _fieldLabel(String text) {
    return Padding(
      padding: const EdgeInsets.only(top: 14, bottom: 6),
      child: Text(text, style: const TextStyle(color: Colors.white54, fontSize: 12)),
    );
  }

  Widget _dropdown<T>(T value, List<T> items, ValueChanged<T> onChanged) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white12),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T>(
          value: value,
          isExpanded: true,
          dropdownColor: const Color(0xFF111827),
          items: items
              .map((item) => DropdownMenuItem(value: item, child: Text('$item')))
              .toList(),
          onChanged: (v) {
            if (v != null) onChanged(v);
          },
        ),
      ),
    );
  }

  // ---------------- URL panel ----------------

  Widget _urlPanel() {
    return _card(Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _modeToggles(_urlMode, (mode) {
          setState(() => _urlMode = mode);
          app.setSetting('urlMode', mode.name);
        }),
        _fieldLabel('ลิงก์สาธารณะ'),
        TextField(
          controller: _urlController,
          onChanged: (v) => _url = v,
          style: const TextStyle(fontSize: 15),
          decoration: InputDecoration(
            hintText: 'https://www.youtube.com/watch?v=…',
            filled: true,
            fillColor: const Color(0xFF0D1520),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide.none,
            ),
            suffixIcon: IconButton(
              icon: const Icon(Icons.content_paste, size: 20),
              onPressed: _pasteUrl,
            ),
          ),
        ),
        _checkRow(
          value: _playlists,
          label: 'โหลดทั้งเพลย์ลิสต์ (ถ้าลิงก์เป็นเพลย์ลิสต์)',
          onChanged: (v) {
            setState(() => _playlists = v ?? false);
            app.setSetting('playlists', _playlists);
          },
        ),
        if (_urlMode == JobMode.video) ...[
          _fieldLabel('รูปแบบไฟล์'),
          _dropdown<String>(_urlFormat, const ['mp4', 'mov'], (v) {
            setState(() => _urlFormat = v);
            app.setSetting('urlFormat', v);
          }),
          _fieldLabel('ระดับคุณภาพ'),
          _dropdown<String>(_quality, const [
            'สูงสุด', '2160p', '1080p', '720p', '480p', '360p'
          ], (v) {
            setState(() => _quality = v);
            app.setSetting('quality', v);
          }),
          _fieldLabel('เฟรมเรต'),
          _dropdown<String>(_fps, const ['สูงสุด', '60', '30'],
              (v) {
            setState(() => _fps = v);
            app.setSetting('fps', v);
          }),
        ] else ...[
          _fieldLabel('รูปแบบเสียง'),
          _dropdown<String>(_audioFormat,
              const ['mp3', 'm4a', 'wav', 'flac', 'opus'],
              (v) {
            setState(() => _audioFormat = v);
            app.setSetting('audioFormat', v);
          }),
        ],
        const SizedBox(height: 12),
        _checkRow(
          value: _authorized,
          label: 'ฉันยืนยันว่ามีสิทธิ์ดาวน์โหลดสื่อนี้',
          onChanged: (v) => setState(() => _authorized = v ?? false),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            backgroundColor: const Color(0xFF4D9DE0),
          ),
          onPressed: _authorized ? _startUrl : null,
          icon: const Icon(Icons.download),
          label: Text(_urlMode == JobMode.video
              ? 'เริ่มดาวน์โหลดวิดีโอ'
              : 'เริ่มดาวน์โหลดเสียง'),
        ),
      ],
    ));
  }

  Future<void> _pasteUrl() async {
    try {
      final text = await Clipboard.getData(Clipboard.kTextPlain);
      final value = text?.text?.trim();
      if (value != null && value.isNotEmpty) {
        _urlController.text = value;
        setState(() => _url = value);
      }
    } catch (_) {
      _toast('ไม่สามารถอ่านคลิปบอร์ดได้', bad: true);
    }
  }

  // ---------------- File panel ----------------

  Widget _filePanel() {
    return _card(Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _modeToggles(_fileMode, (mode) {
          setState(() => _fileMode = mode);
          app.setSetting('fileMode', mode.name);
        }),
        _fieldLabel('เลือกวิดีโอในเครื่อง'),
        GestureDetector(
          onTap: _fileBusy ? null : _pickFile,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: _selectedFile != null
                    ? const Color(0xFF4D9DE0)
                    : Colors.white12,
              ),
            ),
            child: Column(
              children: [
                Icon(
                  _selectedFile != null
                      ? Icons.check_circle
                      : Icons.video_file_outlined,
                  color: _selectedFile != null
                      ? const Color(0xFF4D9DE0)
                      : Colors.white38,
                  size: 32,
                ),
                const SizedBox(height: 8),
                Text(
                  _selectedFile != null
                      ? '${_selectedFile!.uri.pathSegments.last}\n'
                          '(${_formatBytes(_selectedFile!.lengthSync())})'
                      : 'แตะเพื่อเลือกวิดีโอ',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 13,
                    color: _selectedFile != null ? Colors.white : Colors.white54,
                  ),
                ),
                if (_selectedFile != null)
                  TextButton(
                    onPressed: () => setState(() => _selectedFile = null),
                    child: const Text('ลบไฟล์'),
                  ),
              ],
            ),
          ),
        ),
        if (_fileMode == JobMode.video) ...[
          _fieldLabel('รูปแบบไฟล์'),
          _dropdown<String>(_fileFormat, const ['mp4', 'mov'], (v) {
            setState(() => _fileFormat = v);
            app.setSetting('fileFormat', v);
          }),
          _fieldLabel('ระดับคุณภาพ'),
          _dropdown<String>(_fileQuality, const ['High', 'Balanced', 'Small'],
              (v) {
            setState(() => _fileQuality = v);
            app.setSetting('fileQuality', v);
          }),
          _fieldLabel('เฟรมเรต'),
          _dropdown<String>(_fileFps, const ['สูงสุด', '60', '30'],
              (v) {
            setState(() => _fileFps = v);
            app.setSetting('fileFps', v);
          }),
        ] else ...[
          _fieldLabel('รูปแบบเสียง'),
          _dropdown<String>(_fileAudioFormat,
              const ['mp3', 'm4a', 'wav', 'flac', 'opus'],
              (v) {
            setState(() => _fileAudioFormat = v);
            app.setSetting('fileAudioFormat', v);
          }),
        ],
        const SizedBox(height: 16),
        FilledButton.icon(
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            backgroundColor: const Color(0xFF4D9DE0),
          ),
          onPressed: (_fileBusy || _selectedFile == null) ? null : _startFile,
          icon: const Icon(Icons.transform),
          label: Text(_fileMode == JobMode.video ? 'เริ่มแปลงวิดีโอ' : 'เริ่มแยกเสียง'),
        ),
      ],
    ));
  }

  Widget _card(Widget child) {
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF111827),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white10),
      ),
      child: child,
    );
  }

  // ---------------- jobs ----------------

  Widget _jobsSection() {
    final jobs = app.jobs;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(top: 16, bottom: 4),
          child: Text('รายการงาน',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        ),
        if (jobs.isEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text(
              'ยังไม่มีงาน — วางลิงก์หรือเลือกไฟล์เพื่อเริ่ม',
              style: TextStyle(fontSize: 12, color: Colors.white38),
            ),
          )
        else
          ...jobs.map(_jobCard),
      ],
    );
  }

  String _statusLabel(JobStatus status) => switch (status) {
        JobStatus.queued => 'กำลังรอ',
        JobStatus.running => 'กำลังทำงาน',
        JobStatus.done => 'เสร็จแล้ว',
        JobStatus.cancelled => 'ยกเลิกแล้ว',
        JobStatus.failed => 'ไม่สำเร็จ',
      };

  Color _statusColor(JobStatus status) => switch (status) {
        JobStatus.done => const Color(0xFF2E7D32),
        JobStatus.failed => const Color(0xFFB3261E),
        JobStatus.cancelled => Colors.white38,
        _ => const Color(0xFF4D9DE0),
      };

  Widget _jobCard(Job job) {
    final running = job.status == JobStatus.running ||
        job.status == JobStatus.queued;
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1520),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  job.resultName ?? '',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: _statusColor(job.status).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  _statusLabel(job.status),
                  style: TextStyle(
                      fontSize: 11, color: _statusColor(job.status)),
                ),
              ),
            ],
          ),
          if (job.message.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(job.message,
                style: const TextStyle(fontSize: 12, color: Colors.white54)),
          ],
          if (job.etaSeconds != null && job.etaSeconds! > 0) ...[
            const SizedBox(height: 2),
            Text(_formatEta(job.etaSeconds!),
                style: const TextStyle(fontSize: 11, color: Colors.white38)),
          ],
          if (job.error != null && job.status == JobStatus.failed) ...[
            const SizedBox(height: 4),
            Text(job.error!,
                style: const TextStyle(fontSize: 12, color: Color(0xFFFF8A80))),
          ],
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: job.progress,
              minHeight: 4,
              backgroundColor: Colors.white10,
              color: const Color(0xFF4D9DE0),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              if (running)
                _jobAction('ยกเลิก', Icons.close, () => app.cancelJob(job))
              else if (job.status == JobStatus.done) ...[
                _jobAction('เล่น', Icons.play_circle_outline,
                    () => _preview(job)),
                _jobAction('แชร์', Icons.share, () => app.shareJob(job)),
              ] else if (job.status == JobStatus.failed) ...[
                _jobAction('ลองใหม่', Icons.refresh, () => app.retryJob(job)),
                _jobAction('ลบ', Icons.delete_outline,
                    () => app.removeJob(job)),
              ] else
                _jobAction('ลบ', Icons.delete_outline, () => app.removeJob(job)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _jobAction(String label, IconData icon, VoidCallback onTap) {
    return TextButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 16),
      label: Text(label, style: const TextStyle(fontSize: 12)),
    );
  }
}