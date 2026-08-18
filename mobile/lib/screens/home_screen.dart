import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../app_state.dart';
import '../models/job.dart';
import '../services/native.dart';
import '../widgets/ui.dart';
import 'metadata_editor.dart';
import 'video_preview.dart';

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
  final List<File> _selectedFiles = [];
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
      showToast(context, 'กรุณาวางลิงก์ก่อน');
      return;
    }
    final uri = Uri.tryParse(text);
    if (uri == null ||
        !uri.hasScheme ||
        !(uri.scheme == 'http' || uri.scheme == 'https')) {
      showToast(context, 'กรุณาวางลิงก์ที่ถูกต้อง (ขึ้นต้นด้วย http:// หรือ https://)',
          bad: true);
      return;
    }
    if (!_authorized) {
      showToast(context, 'กรุณายืนยันว่าคุณมีสิทธิ์ดาวน์โหลดสื่อนี้', bad: true);
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

  Future<void> _pickFiles() async {
    if (_fileBusy) return;
    try {
      final paths = await NativeService.instance.pickMultipleMediaFiles();
      if (paths.isEmpty) return;
      if (!mounted) return;
      setState(() {
        for (final path in paths) {
          final f = File(path);
          if (_selectedFiles.any((x) => x.path == f.path)) continue;
          _selectedFiles.add(f);
        }
      });
    } catch (e) {
      showToast(context, 'เลือกไฟล์ไม่สำเร็จ: $e', bad: true);
    }
  }

  Future<void> _startFile() async {
    if (_selectedFiles.isEmpty) {
      showToast(context, 'กรุณาเลือกไฟล์ก่อน');
      return;
    }
    setState(() => _fileBusy = true);
    try {
      final params = (
        mode: _fileMode,
        videoFormat: _fileFormat,
        quality: _fileQuality,
        fps: _fileFps,
        audioFormat: _fileAudioFormat,
      );
      if (_selectedFiles.length == 1) {
        await app.startFileJob(
          source: _selectedFiles.first,
          mode: params.mode,
          videoFormat: params.videoFormat,
          quality: params.quality,
          fps: params.fps,
          audioFormat: params.audioFormat,
        );
      } else {
        await app.startFileBatch(
          sources: List.of(_selectedFiles),
          mode: params.mode,
          videoFormat: params.videoFormat,
          quality: params.quality,
          fps: params.fps,
          audioFormat: params.audioFormat,
        );
      }
      setState(() => _selectedFiles.clear());
    } finally {
      if (mounted) setState(() => _fileBusy = false);
    }
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
              if (_urlTab)
                _urlPanel()
              else
                _filePanel(),
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
          Icon(Icons.movie_filter, color: kAccent),
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
          child: segButton('ลิงก์', _urlTab, () {
            setState(() => _urlTab = true);
            app.setSetting('urlTab', true);
          }),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: segButton('ไฟล์', !_urlTab, () {
            setState(() => _urlTab = false);
            app.setSetting('urlTab', false);
          }),
        ),
      ],
    );
  }

  Widget _modeToggles(JobMode mode, ValueChanged<JobMode> onChanged) {
    return Row(
      children: [
        Expanded(
          child: miniButton('วิดีโอ', mode == JobMode.video,
              () => onChanged(JobMode.video)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: miniButton('เสียง', mode == JobMode.audio,
              () => onChanged(JobMode.audio)),
        ),
      ],
    );
  }

  // ---------------- URL panel ----------------

  Widget _urlPanel() {
    return cliporaCard(Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _modeToggles(_urlMode, (mode) {
          setState(() => _urlMode = mode);
          app.setSetting('urlMode', mode.name);
        }),
        fieldLabel('ลิงก์สาธารณะ'),
        TextField(
          controller: _urlController,
          onChanged: (v) => _url = v,
          style: const TextStyle(fontSize: 15),
          decoration: InputDecoration(
            hintText: 'https://www.youtube.com/watch?v=…',
            filled: true,
            fillColor: kSurface2,
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
        checkRow(
          value: _playlists,
          label: 'โหลดทั้งเพลย์ลิสต์ (ถ้าลิงก์เป็นเพลย์ลิสต์)',
          onChanged: (v) {
            setState(() => _playlists = v ?? false);
            app.setSetting('playlists', _playlists);
          },
        ),
        if (_urlMode == JobMode.video) ...[
          fieldLabel('รูปแบบไฟล์'),
          cliporaDropdown<String>(_urlFormat, const ['mp4', 'mov'], (v) {
            setState(() => _urlFormat = v);
            app.setSetting('urlFormat', v);
          }),
          fieldLabel('ระดับคุณภาพ'),
          cliporaDropdown<String>(_quality, const [
            'สูงสุด', '2160p', '1080p', '720p', '480p', '360p'
          ], (v) {
            setState(() => _quality = v);
            app.setSetting('quality', v);
          }),
          fieldLabel('เฟรมเรต'),
          cliporaDropdown<String>(_fps, const ['สูงสุด', '60', '30'], (v) {
            setState(() => _fps = v);
            app.setSetting('fps', v);
          }),
        ] else ...[
          fieldLabel('รูปแบบเสียง'),
          cliporaDropdown<String>(_audioFormat,
              const ['mp3', 'm4a', 'wav', 'flac', 'opus'], (v) {
            setState(() => _audioFormat = v);
            app.setSetting('audioFormat', v);
          }),
        ],
        const SizedBox(height: 12),
        checkRow(
          value: _authorized,
          label: 'ฉันยืนยันว่ามีสิทธิ์ดาวน์โหลดสื่อนี้',
          onChanged: (v) => setState(() => _authorized = v ?? false),
        ),
        const SizedBox(height: 8),
        primaryButton(
          icon: const Icon(Icons.download),
          label: Text(_urlMode == JobMode.video
              ? 'เริ่มดาวน์โหลดวิดีโอ'
              : 'เริ่มดาวน์โหลดเสียง'),
          onPressed: _authorized ? _startUrl : null,
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
      if (!mounted) return;
      showToast(context, 'ไม่สามารถอ่านคลิปบอร์ดได้', bad: true);
    }
  }

  // ---------------- File panel ----------------

  Widget _filePanel() {
    return cliporaCard(Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _modeToggles(_fileMode, (mode) {
          setState(() => _fileMode = mode);
          app.setSetting('fileMode', mode.name);
        }),
        fieldLabel(_selectedFiles.isEmpty ? 'เลือกวิดีโอในเครื่อง (เลือกหลายไฟล์ได้)' : 'ไฟล์ที่เลือก (${_selectedFiles.length})'),
        _pickArea(),
        if (_selectedFiles.isNotEmpty) ...[
          const SizedBox(height: 8),
          _selectedFileList(),
        ],
        if (_fileMode == JobMode.video) ...[
          fieldLabel('รูปแบบไฟล์'),
          cliporaDropdown<String>(_fileFormat, const ['mp4', 'mov'], (v) {
            setState(() => _fileFormat = v);
            app.setSetting('fileFormat', v);
          }),
          fieldLabel('ระดับคุณภาพ'),
          cliporaDropdown<String>(_fileQuality, const ['High', 'Balanced', 'Small'],
              (v) {
            setState(() => _fileQuality = v);
            app.setSetting('fileQuality', v);
          }),
          fieldLabel('เฟรมเรต'),
          cliporaDropdown<String>(_fileFps, const ['สูงสุด', '60', '30'], (v) {
            setState(() => _fileFps = v);
            app.setSetting('fileFps', v);
          }),
        ] else ...[
          fieldLabel('รูปแบบเสียง'),
          cliporaDropdown<String>(_fileAudioFormat,
              const ['mp3', 'm4a', 'wav', 'flac', 'opus'], (v) {
            setState(() => _fileAudioFormat = v);
            app.setSetting('fileAudioFormat', v);
          }),
        ],
        const SizedBox(height: 16),
        primaryButton(
          icon: const Icon(Icons.transform),
          label: Text(
            _fileMode == JobMode.video
                ? (_selectedFiles.length > 1
                    ? 'แปลงวิดีโอ ${_selectedFiles.length} ไฟล์'
                    : 'เริ่มแปลงวิดีโอ')
                : (_selectedFiles.length > 1
                    ? 'แยกเสียง ${_selectedFiles.length} ไฟล์'
                    : 'เริ่มแยกเสียง'),
          ),
          onPressed: (_fileBusy || _selectedFiles.isEmpty) ? null : _startFile,
        ),
        const SizedBox(height: 8),
        TextButton.icon(
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const MetadataEditorScreen()),
            );
          },
          icon: const Icon(Icons.music_note, size: 18),
          label: const Text('แก้ไข metadata เพลง (ชื่อ ศิลปิน หน้าปก)'),
        ),
      ],
    ));
  }

  Widget _pickArea() {
    return GestureDetector(
      onTap: _fileBusy ? null : _pickFiles,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: _selectedFiles.isNotEmpty ? kAccent : Colors.white12,
          ),
        ),
        child: Column(
          children: [
            Icon(
              _selectedFiles.isNotEmpty
                  ? Icons.check_circle
                  : Icons.video_file_outlined,
              color: _selectedFiles.isNotEmpty ? kAccent : Colors.white38,
              size: 32,
            ),
            const SizedBox(height: 8),
            Text(
              _selectedFiles.isNotEmpty
                  ? 'แตะเพื่อเพิ่มไฟล์อีก'
                  : 'แตะเพื่อเลือกวิดีโอ/เสียง',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color: _selectedFiles.isNotEmpty ? Colors.white : Colors.white54,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _selectedFileList() {
    return Column(
      children: [
        for (var i = 0; i < _selectedFiles.length; i++)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.insert_drive_file_outlined, size: 20),
            title: Text(
              _selectedFiles[i].uri.pathSegments.last,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13),
            ),
            subtitle: Text(
              formatBytes(_selectedFiles[i].lengthSync()),
              style: const TextStyle(fontSize: 11, color: Colors.white38),
            ),
            trailing: IconButton(
              icon: const Icon(Icons.close, size: 18),
              onPressed: _fileBusy
                  ? null
                  : () => setState(() => _selectedFiles.removeAt(i)),
            ),
          ),
      ],
    );
  }

  // ---------------- jobs ----------------

  Widget _jobsSection() {
    final jobs = app.jobs;
    // จัดกลุ่มงาน batch ให้อยู่ด้วยกัน
    final groups = <String?, List<Job>>{};
    for (final job in jobs) {
      final key = job.batchId;
      groups.putIfAbsent(key, () => []).add(job);
    }
    final ordered = <List<Job>>[];
    for (final job in jobs) {
      final key = job.batchId;
      if (key == null) {
        if (!ordered.contains([job])) ordered.add([job]);
      } else {
        final group = groups[key]!;
        if (!ordered.contains(group)) ordered.add(group);
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 16, bottom: 4),
          child: Row(
            children: [
              const Expanded(
                child: Text('รายการงาน',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              ),
              if (app.jobs.any((j) => j.status == JobStatus.done ||
                  j.status == JobStatus.failed ||
                  j.status == JobStatus.cancelled))
                TextButton(
                  onPressed: () => app.clearFinished(),
                  child: const Text('ล้างงานเสร็จ', style: TextStyle(fontSize: 12)),
                ),
            ],
          ),
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
          ...ordered.map(_jobGroup),
      ],
    );
  }

  Widget _jobGroup(List<Job> group) {
    if (group.length == 1) return _jobCard(group.first);
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 4),
      decoration: BoxDecoration(
        color: kSurface2,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.playlist_play, size: 16, color: kAccent),
              const SizedBox(width: 6),
              const Text('งาน batch',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
              const Spacer(),
              if (group.any((j) => j.status == JobStatus.running))
                TextButton(
                  onPressed: () => app.cancelBatch(group.first),
                  child: const Text('ยกเลิกทั้งหมด', style: TextStyle(fontSize: 11)),
                ),
            ],
          ),
          ...group.map((j) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: _jobCard(j, compact: true),
              )),
        ],
      ),
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
        JobStatus.done => kSuccess,
        JobStatus.failed => kDanger,
        JobStatus.cancelled => Colors.white38,
        _ => kAccent,
      };

  Widget _jobCard(Job job, {bool compact = false}) {
    final running = job.status == JobStatus.running ||
        job.status == JobStatus.queued;
    return Container(
      margin: EdgeInsets.only(top: compact ? 0 : 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: compact ? kSurface : kSurface2,
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
            Text(formatEta(job.etaSeconds!),
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
              color: kAccent,
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
                if (job.kind == JobKind.metadata)
                  _jobAction('แก้ metadata', Icons.edit,
                      () => _editMetadata(job)),
              ] else if (job.status == JobStatus.failed) ...[
                if (job.kind == JobKind.metadata)
                  _jobAction('ลบ', Icons.delete_outline,
                      () => app.removeJob(job))
                else ...[
                  _jobAction('ลองใหม่', Icons.refresh, () => app.retryJob(job)),
                  _jobAction('ลบ', Icons.delete_outline,
                      () => app.removeJob(job)),
                ],
              ] else
                _jobAction('ลบ', Icons.delete_outline, () => app.removeJob(job)),
            ],
          ),
        ],
      ),
    );
  }

  void _editMetadata(Job job) {
    final path = job.resultPath;
    if (path == null || !File(path).existsSync()) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => MetadataEditorScreen(initialFile: File(path)),
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