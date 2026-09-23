import 'package:research_os/models/document_item.dart';
import 'package:research_os/services/document_service.dart';
import 'package:research_os/theme/colors.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

class DocumentManagementDialog extends StatefulWidget {
  final Set<String> initialSelectedIds;
  final ValueChanged<Set<String>>? onSelectionChanged;

  const DocumentManagementDialog({
    super.key,
    this.initialSelectedIds = const {},
    this.onSelectionChanged,
  });

  @override
  State<DocumentManagementDialog> createState() => _DocumentManagementDialogState();
}

class _DocumentManagementDialogState extends State<DocumentManagementDialog> {
  late Future<List<DocumentItem>> _futureDocuments;
  late Set<String> _selectedIds;
  bool _isUploading = false;
  String? _uploadStatusText;

  @override
  void initState() {
    super.initState();
    _selectedIds = Set.from(widget.initialSelectedIds);
    _refresh();
  }

  void _refresh() {
    setState(() {
      _futureDocuments = DocumentService().listDocuments();
    });
  }

  Future<void> _handleUpload() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'docx', 'txt', 'md'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) return;

      final file = result.files.single;
      final bytes = file.bytes;
      if (bytes == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to read file data')),
          );
        }
        return;
      }

      setState(() {
        _isUploading = true;
        _uploadStatusText = 'Ingesting and indexing ${file.name}...';
      });

      await DocumentService().uploadDocument(file.name, bytes);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('"${file.name}" indexed successfully!'),
            backgroundColor: Colors.green.shade800,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Upload failed: $e'),
            backgroundColor: Colors.redAccent.shade700,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
          _uploadStatusText = null;
        });
        _refresh();
      }
    }
  }

  Future<void> _handleDelete(DocumentItem doc) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.cardColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.cardBorder),
        ),
        title: const Text('Delete Document', style: TextStyle(color: AppColors.whiteColor, fontSize: 16)),
        content: Text('Are you sure you want to delete "${doc.filename}"?', style: const TextStyle(color: AppColors.textSecondary)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel', style: TextStyle(color: AppColors.textGrey)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.redAccent.shade700,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await DocumentService().deleteDocument(doc.id);
      _selectedIds.remove(doc.id);
      widget.onSelectionChanged?.call(_selectedIds);
      _refresh();
    }
  }

  Future<void> _handleReindex(DocumentItem doc) async {
    setState(() {
      _isUploading = true;
      _uploadStatusText = 'Re-indexing ${doc.filename}...';
    });

    try {
      await DocumentService().reindexDocument(doc.id);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Re-index failed: $e'), backgroundColor: Colors.redAccent.shade700),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
          _uploadStatusText = null;
        });
        _refresh();
      }
    }
  }

  void _toggleSelection(String id) {
    setState(() {
      if (_selectedIds.contains(id)) {
        _selectedIds.remove(id);
      } else {
        _selectedIds.add(id);
      }
    });
    widget.onSelectionChanged?.call(_selectedIds);
  }

  Widget _buildFileIcon(String fileType) {
    IconData iconData = Icons.description_outlined;
    Color iconColor = AppColors.submitButton;

    final ft = fileType.toLowerCase();
    if (ft == 'pdf') {
      iconData = Icons.picture_as_pdf_outlined;
      iconColor = Colors.redAccent.shade200;
    } else if (ft == 'docx') {
      iconData = Icons.article_outlined;
      iconColor = Colors.blueAccent.shade200;
    } else if (ft == 'md') {
      iconData = Icons.code_rounded;
      iconColor = Colors.amberAccent.shade200;
    }

    return Container(
      padding: const EdgeInsets.all(7),
      decoration: BoxDecoration(
        color: iconColor.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(iconData, color: iconColor, size: 18),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.cardColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppColors.cardBorder),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 680, maxHeight: 600),
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  const Icon(Icons.folder_copy_outlined, color: AppColors.submitButton, size: 22),
                  const SizedBox(width: 10),
                  const Text(
                    'Document Knowledge Base',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.whiteColor),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close, color: AppColors.iconGrey, size: 20),
                    onPressed: () => Navigator.of(context).pop(_selectedIds),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              const Text(
                'Upload documents (.pdf, .docx, .txt, .md) to search and ground AI answers locally.',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: 16),
              const Divider(color: AppColors.cardBorder, height: 1),
              const SizedBox(height: 14),

              // Upload Action Row
              Row(
                children: [
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.submitButton,
                      foregroundColor: AppColors.background,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    icon: const Icon(Icons.upload_file_rounded, size: 18),
                    label: const Text('Upload Document', style: TextStyle(fontWeight: FontWeight.w600)),
                    onPressed: _isUploading ? null : _handleUpload,
                  ),
                  const SizedBox(width: 12),
                  if (_isUploading) ...[
                    const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.submitButton)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _uploadStatusText ?? 'Processing...',
                        style: const TextStyle(color: AppColors.textGrey, fontSize: 12),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ] else ...[
                    Text(
                      '${_selectedIds.length} selected for query',
                      style: const TextStyle(color: AppColors.textGrey, fontSize: 12),
                    ),
                    const Spacer(),
                    if (_selectedIds.isNotEmpty)
                      TextButton(
                        onPressed: () {
                          setState(() => _selectedIds.clear());
                          widget.onSelectionChanged?.call(_selectedIds);
                        },
                        child: const Text('Clear Selection', style: TextStyle(color: AppColors.textGrey, fontSize: 12)),
                      ),
                  ],
                ],
              ),
              const SizedBox(height: 14),

              // Document list
              Expanded(
                child: FutureBuilder<List<DocumentItem>>(
                  future: _futureDocuments,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting && !_isUploading) {
                      return const Center(child: CircularProgressIndicator(color: AppColors.submitButton, strokeWidth: 2));
                    }

                    final documents = snapshot.data ?? [];
                    if (documents.isEmpty) {
                      return Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.description_outlined, size: 44, color: AppColors.iconGrey),
                            SizedBox(height: 12),
                            Text('No documents uploaded yet', style: TextStyle(color: AppColors.textGrey, fontSize: 14)),
                            SizedBox(height: 4),
                            Text('Upload a PDF, DOCX, TXT, or Markdown file to get started.', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
                          ],
                        ),
                      );
                    }

                    return ListView.separated(
                      itemCount: documents.length,
                      separatorBuilder: (_, _) => const Divider(color: AppColors.searchBarBorder, height: 1),
                      itemBuilder: (context, index) {
                        final doc = documents[index];
                        final isSelected = _selectedIds.contains(doc.id);

                        return ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          leading: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Checkbox(
                                value: isSelected,
                                activeColor: AppColors.submitButton,
                                checkColor: AppColors.background,
                                onChanged: doc.isReady ? (_) => _toggleSelection(doc.id) : null,
                              ),
                              _buildFileIcon(doc.fileType),
                            ],
                          ),
                          title: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  doc.filename,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: isSelected ? AppColors.whiteColor : AppColors.textPrimary,
                                    fontSize: 13.5,
                                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              // Status badge
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: doc.isReady
                                      ? Colors.green.shade900.withValues(alpha: 0.3)
                                      : (doc.isFailed ? Colors.red.shade900.withValues(alpha: 0.3) : Colors.amber.shade900.withValues(alpha: 0.3)),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(
                                    color: doc.isReady
                                        ? Colors.green.shade600
                                        : (doc.isFailed ? Colors.redAccent : Colors.amber),
                                    width: 0.8,
                                  ),
                                ),
                                child: Text(
                                  doc.status,
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: doc.isReady
                                        ? Colors.green.shade300
                                        : (doc.isFailed ? Colors.redAccent.shade100 : Colors.amber.shade300),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          subtitle: Text(
                            '${doc.formattedFileSize} • ${doc.chunkCount} chunks • ${doc.createdAt.month}/${doc.createdAt.day}/${doc.createdAt.year}',
                            style: const TextStyle(color: AppColors.textMuted, fontSize: 11),
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.refresh_rounded, size: 16, color: AppColors.iconGrey),
                                tooltip: 'Re-index',
                                onPressed: () => _handleReindex(doc),
                              ),
                              IconButton(
                                icon: const Icon(Icons.delete_outline, size: 16, color: AppColors.iconGrey),
                                tooltip: 'Delete',
                                onPressed: () => _handleDelete(doc),
                              ),
                            ],
                          ),
                          onTap: doc.isReady ? () => _toggleSelection(doc.id) : null,
                        );
                      },
                    );
                  },
                ),
              ),

              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.submitButton,
                      foregroundColor: AppColors.background,
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: () => Navigator.of(context).pop(_selectedIds),
                    child: Text(
                      _selectedIds.isEmpty ? 'Close' : 'Use Selected (${_selectedIds.length})',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
