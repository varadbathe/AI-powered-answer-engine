import 'dart:async';
import 'dart:convert';
import 'package:ai_answer_engine/utils/app_logger.dart';
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

  Stream<Map<String, dynamic>> get searchResultStream =>
      _searchResultController.stream;
  Stream<Map<String, dynamic>> get contentStream => _contentController.stream;
  Stream<Map<String, dynamic>> get followUpStream => _followUpController.stream;

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

          if (type == 'search_result' || type == 'search_results') {
            AppLogger.info(
              'Received search results: ${(data['data'] as List?)?.length ?? 0} items',
              tag: 'WebSocket',
            );
            _searchResultController.add(data);
          } else if (type == 'content') {
            AppLogger.debug(
              'Received content chunk: "${data['data']}"',
              tag: 'WebSocket',
            );
            _contentController.add(data);
          } else if (type == 'done') {
            AppLogger.info(
              'Received content stream complete signal',
              tag: 'WebSocket',
            );
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

  void chat(String query, {List<Map<String, String>>? history}) {
    AppLogger.info(
      'Initiating chat query: "$query" (history: ${history?.length ?? 0} turns)',
      tag: 'ChatWebService',
    );

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