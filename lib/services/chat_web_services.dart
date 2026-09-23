import 'dart:async';
import 'dart:convert';
import 'package:research_os/utils/app_logger.dart';
import 'package:web_socket_client/web_socket_client.dart';

class ChatWebService {
  static final _instance = ChatWebService._internal();
  WebSocket? _socket;

  factory ChatWebService() => _instance;

  ChatWebService._internal();

  // Broadcast controllers allow multiple listeners (e.g. across screen transitions)
  final _searchResultController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _contentController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _followUpController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _conversationIdController =
      StreamController<String>.broadcast();
  final _errorController =
      StreamController<String>.broadcast();

  Map<String, dynamic>? lastSearchResults;
  String accumulatedAnswer = '';
  bool isStreamingAnswer = false;

  Stream<Map<String, dynamic>> get searchResultStream =>
      _searchResultController.stream;
  Stream<Map<String, dynamic>> get contentStream => _contentController.stream;
  Stream<Map<String, dynamic>> get followUpStream => _followUpController.stream;
  Stream<String> get conversationIdStream => _conversationIdController.stream;
  Stream<String> get errorStream => _errorController.stream;

  void connect() {
    AppLogger.info(
      'Connecting to WebSocket at ws://localhost:8000/ws/chat',
      tag: 'WebSocket',
    );

    try {
      _socket?.close();
    } catch (_) {}

    _socket = WebSocket(
      Uri.parse("ws://localhost:8000/ws/chat"),
      timeout: const Duration(seconds: 10),
    );

    _socket!.connection.listen(
      (state) {
        AppLogger.info('WebSocket state: $state', tag: 'WebSocket');
      },
      onError: (error) {
        AppLogger.error('WebSocket connection error: $error', tag: 'WebSocket');
      },
    );

    _socket!.messages.listen(
      (message) {
        try {
          final data = json.decode(message.toString());
          final type = data['type'];

          final convId = data['conversation_id'];
          if (convId != null && convId is String && convId.isNotEmpty) {
            _conversationIdController.add(convId);
          }

          if (type == 'search_result' || type == 'search_results') {
            AppLogger.info(
              'Received search results: ${(data['data'] as List?)?.length ?? 0} items',
              tag: 'WebSocket',
            );
            lastSearchResults = data;
            _searchResultController.add(data);
          } else if (type == 'content') {
            AppLogger.debug(
              'Received content chunk: "${data['data']}"',
              tag: 'WebSocket',
            );
            accumulatedAnswer += (data['data'] ?? '');
            isStreamingAnswer = true;
            _contentController.add(data);
          } else if (type == 'done') {
            AppLogger.info(
              'Received content stream complete signal (conv: $convId)',
              tag: 'WebSocket',
            );
            isStreamingAnswer = false;
            _contentController.add(data);
          } else if (type == 'follow_ups' || type == 'follow_up') {
            AppLogger.info(
              'Received follow-up suggestions: ${(data['data'] as List?)?.length ?? 0} items',
              tag: 'WebSocket',
            );
            _followUpController.add(data);
          } else if (type == 'error') {
            AppLogger.error(
              'Backend error: ${data['data']}',
              tag: 'WebSocket',
            );
            _errorController.add(data['data']?.toString() ?? 'Error occurred');
          } else {
            AppLogger.warn(
              'Unknown message type: $type',
              tag: 'WebSocket',
            );
          }
        } catch (e, stackTrace) {
          AppLogger.error(
            'Failed to parse WebSocket message: $e',
            tag: 'WebSocket',
            error: e,
            stackTrace: stackTrace,
          );
        }
      },
      onError: (error) {
        AppLogger.error(
          'Error on WebSocket message stream: $error',
          tag: 'WebSocket',
        );
      },
      onDone: () {
        AppLogger.info('WebSocket connection closed.', tag: 'WebSocket');
      },
    );
  }

  void chat(
    String query, {
    List<Map<String, String>>? history,
    String? conversationId,
    String? mode,
    List<String>? documentIds,
    String? retrievalMode,
  }) {
    AppLogger.info(
      'Initiating chat query: "$query" (conv: $conversationId, mode: $mode, docs: ${documentIds?.length ?? 0}, history: ${history?.length ?? 0} turns, retrievalMode: $retrievalMode)',
      tag: 'ChatWebService',
    );

    lastSearchResults = null;
    accumulatedAnswer = '';
    isStreamingAnswer = false;

    if (_socket == null) {
      AppLogger.warn(
        'WebSocket not connected yet. Connecting now...',
        tag: 'ChatWebService',
      );
      connect();
    }

    try {
      final payload = <String, dynamic>{
        'query': query,
        if (history != null && history.isNotEmpty) 'history': history,
        if (conversationId != null && conversationId.isNotEmpty) 'conversation_id': conversationId,
        if (mode != null && mode.isNotEmpty) 'mode': mode,
        if (documentIds != null && documentIds.isNotEmpty) 'document_ids': documentIds,
        if (retrievalMode != null && retrievalMode.isNotEmpty) 'retrieval_mode': retrievalMode,
      };

      _socket!.send(json.encode(payload));
      AppLogger.info(
        'Query sent to backend successfully.',
        tag: 'ChatWebService',
      );
    } catch (e, stackTrace) {
      AppLogger.error(
        'Failed to send query: $e',
        tag: 'ChatWebService',
        error: e,
        stackTrace: stackTrace,
      );
      // Try to re-connect for recovery
      connect();
    }
  }
}