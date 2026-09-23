import 'package:research_os/pages/chat_page.dart';

class ConversationSummary {
  final String id;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;

  ConversationSummary({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ConversationSummary.fromJson(Map<String, dynamic> json) {
    return ConversationSummary(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? 'Untitled',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'created_at': createdAt.toIso8601String(),
    'updated_at': updatedAt.toIso8601String(),
  };
}

class ConversationTurnModel {
  final int turnIndex;
  final String question;
  final String answer;
  final List<dynamic> sources;
  final List<String> followUps;
  final DateTime createdAt;

  ConversationTurnModel({
    required this.turnIndex,
    required this.question,
    required this.answer,
    required this.sources,
    required this.followUps,
    required this.createdAt,
  });

  factory ConversationTurnModel.fromJson(Map<String, dynamic> json) {
    final rawSources = json['sources'] as List? ?? [];
    final rawFollowUps = json['follow_ups'] as List? ?? [];
    return ConversationTurnModel(
      turnIndex: json['turn_index'] as int? ?? 0,
      question: json['question'] as String? ?? '',
      answer: json['answer'] as String? ?? '',
      sources: rawSources,
      followUps: rawFollowUps.map((e) => e.toString()).toList(),
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }

  ChatTurn toChatTurn() {
    return ChatTurn(
      question: question,
      answer: answer,
      sources: sources,
      isLoadingSources: false,
      isLoadingAnswer: false,
      isStreaming: false,
      suggestedFollowUps: followUps,
    );
  }
}

class ConversationDetail {
  final String id;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<ConversationTurnModel> turns;

  ConversationDetail({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
    required this.turns,
  });

  factory ConversationDetail.fromJson(Map<String, dynamic> json) {
    final rawTurns = json['turns'] as List? ?? [];
    final parsedTurns = rawTurns
        .map((t) => ConversationTurnModel.fromJson(Map<String, dynamic>.from(t as Map)))
        .toList();

    return ConversationDetail(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? 'Untitled',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
      turns: parsedTurns,
    );
  }

  List<ChatTurn> toChatTurns() {
    return turns.map((t) => t.toChatTurn()).toList();
  }
}
