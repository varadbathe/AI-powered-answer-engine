import 'dart:convert';
import 'package:research_os/models/document_item.dart';
import 'package:research_os/utils/app_logger.dart';
import 'package:http/http.dart' as http;

class DocumentService {
  static final DocumentService _instance = DocumentService._internal();
  factory DocumentService() => _instance;
  DocumentService._internal();

  final String baseUrl = "http://localhost:8000";

  Future<List<DocumentItem>> listDocuments() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/documents'));
      if (response.statusCode == 200) {
        final List<dynamic> jsonList = jsonDecode(response.body);
        return jsonList.map((item) => DocumentItem.fromJson(item)).toList();
      } else {
        AppLogger.error('Failed to list documents: ${response.statusCode} - ${response.body}', tag: 'DocumentService');
        return [];
      }
    } catch (e) {
      AppLogger.error('Error listing documents: $e', tag: 'DocumentService');
      return [];
    }
  }

  Future<DocumentItem?> uploadDocument(String filename, List<int> bytes) async {
    try {
      final uri = Uri.parse('$baseUrl/api/documents');
      final request = http.MultipartRequest('POST', uri);
      request.files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: filename),
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 201) {
        final data = jsonDecode(response.body);
        return DocumentItem.fromJson(data);
      } else if (response.statusCode == 409) {
        final data = jsonDecode(response.body);
        final msg = data['detail']?['message'] ?? 'Document with identical content already exists';
        throw Exception(msg);
      } else {
        final data = jsonDecode(response.body);
        final detail = data['detail'] ?? 'Failed to upload document';
        throw Exception(detail.toString());
      }
    } catch (e) {
      AppLogger.error('Error uploading document: $e', tag: 'DocumentService');
      rethrow;
    }
  }

  Future<bool> deleteDocument(String documentId) async {
    try {
      final response = await http.delete(Uri.parse('$baseUrl/api/documents/$documentId'));
      return response.statusCode == 200;
    } catch (e) {
      AppLogger.error('Error deleting document: $e', tag: 'DocumentService');
      return false;
    }
  }

  Future<DocumentItem?> reindexDocument(String documentId) async {
    try {
      final response = await http.post(Uri.parse('$baseUrl/api/documents/$documentId/reindex'));
      if (response.statusCode == 200) {
        return DocumentItem.fromJson(jsonDecode(response.body));
      }
      return null;
    } catch (e) {
      AppLogger.error('Error re-indexing document: $e', tag: 'DocumentService');
      return null;
    }
  }
}
