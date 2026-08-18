/// Metadata ของไฟล์เสียง (mp3/m4a/flac/opus) ที่ผู้ใช้แก้ไขได้
class MediaMetadata {
  final String? title;
  final String? artist;
  final String? album;
  final String? albumArtist;
  final String? genre;
  final int? track;
  final int? year;
  final bool hasCover;

  const MediaMetadata({
    this.title,
    this.artist,
    this.album,
    this.albumArtist,
    this.genre,
    this.track,
    this.year,
    this.hasCover = false,
  });
}