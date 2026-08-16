enum JobKind { url, file }
enum JobMode { video, audio }
enum JobStatus { queued, running, done, failed, cancelled }

class Job {
  final String id;
  final JobKind kind;
  final JobMode mode;
  JobStatus status;
  double progress;
  String message;
  String? resultName;
  String? resultPath;
  String? error;
  final DateTime createdAt;

  Job({
    required this.id,
    required this.kind,
    required this.mode,
    required this.status,
    this.progress = 0,
    this.message = '',
    this.resultName,
    this.resultPath,
    this.error,
    DateTime? createdAt,
  }) : createdAt = createdAt ?? DateTime.now();
}