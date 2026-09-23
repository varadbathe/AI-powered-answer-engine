import 'dart:convert';
import 'package:research_os/models/conversation.dart';
import 'package:research_os/utils/app_logger.dart';
import 'package:http/http.dart' as http;

class ConversationService {
  static final ConversationService _instance = ConversationService._internal();
  factory ConversationService() => _instance;

  ConversationService._internal();

  String baseUrl = 'http://localhost:8000/api/conversations';
  http.Client? _client;

  http.Client get client => _client ?? http.Client();

  // For testing dependency injection
  void setClientForTesting(http.Client? testClient) {
    _client = testClient;
  }

  Future<List<ConversationSummary>> listConversations({int limit = 50, int offset = 0}) async {
    try {
      final uri = Uri.parse('$baseUrl?limit=$limit&offset=$offset');
      final response = await client.get(uri);

      if (response.statusCode == 200) {
        final List list = json.decode(utf8.decode(response.bodyBytes)) as List;
        return list.map((item) => ConversationSummary.fromJson(Map<String, dynamic>.from(item as Map))).toList();
      } else {
        AppLogger.error('Failed to list conversations: ${response.statusCode}', tag: 'ConversationService');
        return [];
      }
    } catch (e, st) {
      AppLogger.error('Error listing conversations: $e', tag: 'ConversationService', error: e, stackTrace: st);
      return [];
    }
  }

  Future<ConversationDetail?> getConversation(String conversationId) async {
    try {
      final uri = Uri.parse('$baseUrl/$conversationId');
      final response = await client.get(uri);

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return ConversationDetail.fromJson(data);
      } else {
        AppLogger.error('Failed to get conversation $conversationId: ${response.statusCode}', tag: 'ConversationService');
        return null;
      }
    } catch (e, st) {
      AppLogger.error('Error getting conversation $conversationId: $e', tag: 'ConversationService', error: e, stackTrace: st);
      return null;
    }
  }

  Future<ConversationSummary?> renameConversation(String conversationId, String newTitle) async {
    try {
      final uri = Uri.parse('$baseUrl/$conversationId');
      final response = await client.patch(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'title': newTitle}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return ConversationSummary.fromJson(data);
      } else {
        AppLogger.error('Failed to rename conversation $conversationId: ${response.statusCode}', tag: 'ConversationService');
        return null;
      }
    } catch (e, st) {
      AppLogger.error('Error renaming conversation $conversationId: $e', tag: 'ConversationService', error: e, stackTrace: st);
      return null;
    }
  }

  Future<bool> deleteConversation(String conversationId) async {
    try {
      final uri = Uri.parse('$baseUrl/$conversationId');
      final response = await client.delete(uri);

      if (response.statusCode == 200) {
        return true;
      } else {
        AppLogger.error('Failed to delete conversation $conversationId: ${response.statusCode}', tag: 'ConversationService');
        return false;
      }
    } catch (e, st) {
      AppLogger.error('Error deleting conversation $conversationId: $e', tag: 'ConversationService', error: e, stackTrace: st);
      return false;
    }
  }
}
