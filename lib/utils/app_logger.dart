import 'dart:developer' as developer;
import 'package:flutter/foundation.dart';

/// Centralized logger for the Flutter frontend.
/// Outputs formatted, tagged logs to the VS Code Debug Console (via dart:developer)
/// and standard debug streams across Web, Desktop, and Mobile.
class AppLogger {
  static const String _defaultTag = 'Frontend';

  /// Log general debug information
  static void debug(
    String message, {
    String tag = _defaultTag,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _log('DEBUG', message, tag: tag, error: error, stackTrace: stackTrace, level: 500);
  }

  /// Log informational events (e.g. connections, requests, data streams)
  static void info(
    String message, {
    String tag = _defaultTag,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _log('INFO', message, tag: tag, error: error, stackTrace: stackTrace, level: 800);
  }

  /// Log warnings
  static void warn(
    String message, {
    String tag = _defaultTag,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _log('WARN', message, tag: tag, error: error, stackTrace: stackTrace, level: 900);
  }

  /// Log errors with optional error details and stack traces
  static void error(
    String message, {
    String tag = _defaultTag,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _log('ERROR', message, tag: tag, error: error, stackTrace: stackTrace, level: 1000);
  }

  static void _log(
    String levelName,
    String message, {
    required String tag,
    Object? error,
    StackTrace? stackTrace,
    int level = 800,
  }) {
    final now = DateTime.now();
    final timeStr =
        '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:${now.second.toString().padLeft(2, '0')}';
    final formattedMessage = '[$timeStr] [$tag] [$levelName] $message';

    // 1. Sends directly to Dart VM Service / DevTools & VS Code Debug Console
    developer.log(
      message,
      name: tag,
      level: level,
      error: error,
      stackTrace: stackTrace,
    );

    // 2. Also prints to debug stream for browser console and terminal visibility
    if (kDebugMode) {
      debugPrint(formattedMessage);
      if (error != null) {
        debugPrint('  Error: $error');
      }
      if (stackTrace != null) {
        debugPrint('  StackTrace:\n$stackTrace');
      }
    }
  }
}
