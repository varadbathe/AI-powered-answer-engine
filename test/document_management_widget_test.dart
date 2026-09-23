import 'package:research_os/models/document_item.dart';
import 'package:research_os/widget/document_management_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('DocumentItem model formats file size and status accurately', () {
    final doc1 = DocumentItem(
      id: 'doc-1',
      filename: 'sample.pdf',
      fileType: 'pdf',
      fileSize: 1048576, // 1 MB
      fileHash: 'abc123hash',
      status: 'READY',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      chunkCount: 8,
    );

    expect(doc1.formattedFileSize, '1.0 MB');
    expect(doc1.isReady, isTrue);
    expect(doc1.isProcessing, isFalse);
    expect(doc1.isFailed, isFalse);

    final doc2 = DocumentItem(
      id: 'doc-2',
      filename: 'notes.txt',
      fileType: 'txt',
      fileSize: 2048, // 2 KB
      fileHash: 'def456hash',
      status: 'INDEXING',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      chunkCount: 2,
    );

    expect(doc2.formattedFileSize, '2.0 KB');
    expect(doc2.isReady, isFalse);
    expect(doc2.isProcessing, isTrue);
  });

  testWidgets('DocumentManagementDialog renders header and empty state cleanly', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: DocumentManagementDialog(),
        ),
      ),
    );

    // Initial pump
    await tester.pump();

    // Verify title and upload button
    expect(find.text('Document Knowledge Base'), findsOneWidget);
    expect(find.text('Upload Document'), findsOneWidget);
  });
}
