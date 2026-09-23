class DocumentItem {
  final String id;
  final String filename;
  final String fileType;
  final int fileSize;
  final String fileHash;
  final String status;
  final double progress;
  final String? errorMessage;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int chunkCount;

  DocumentItem({
    required this.id,
    required this.filename,
    required this.fileType,
    required this.fileSize,
    required this.fileHash,
    required this.status,
    this.progress = 0.0,
    this.errorMessage,
    required this.createdAt,
    required this.updatedAt,
    this.chunkCount = 0,
  });

  bool get isReady => status == 'READY';
  bool get isFailed => status == 'FAILED';
  bool get isProcessing => !isReady && !isFailed;

  String get formattedFileSize {
    if (fileSize < 1024) return '$fileSize B';
    if (fileSize < 1024 * 1024) {
      return '${(fileSize / 1024).toStringAsFixed(1)} KB';
    }
    return '${(fileSize / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  factory DocumentItem.fromJson(Map<String, dynamic> json) {
    return DocumentItem(
      id: json['document_id'] ?? json['id'] ?? '',
      filename: json['filename'] ?? 'Untitled',
      fileType: json['file_type'] ?? 'txt',
      fileSize: json['file_size'] is int ? json['file_size'] : (int.tryParse('${json['file_size']}') ?? 0),
      fileHash: json['file_hash'] ?? '',
      status: json['status'] ?? 'READY',
      progress: (json['progress'] is num) ? (json['progress'] as num).toDouble() : 0.0,
      errorMessage: json['error_message'],
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) ?? DateTime.now() : DateTime.now(),
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at']) ?? DateTime.now() : DateTime.now(),
      chunkCount: json['chunk_count'] is int ? json['chunk_count'] : (int.tryParse('${json['chunk_count']}') ?? 0),
    );
  }
}
