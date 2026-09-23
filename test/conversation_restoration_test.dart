import 'dart:convert';
import 'package:research_os/models/conversation.dart';
import 'package:research_os/pages/chat_page.dart';
import 'package:research_os/services/conversation_service.dart';
import 'package:research_os/widget/follow_up_section.dart';
import 'package:research_os/widget/sources_section.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('Conversation Data Model Tests', () {
    test('ConversationSummary serialization and parsing', () {
      final jsonMap = {
        'id': 'conv-123',
        'title': 'Test Conversation',
        'created_at': '2026-09-22T10:00:00Z',
        'updated_at': '2026-09-22T10:05:00Z',
      };

      final summary = ConversationSummary.fromJson(jsonMap);
      expect(summary.id, 'conv-123');
      expect(summary.title, 'Test Conversation');
      expect(summary.createdAt.year, 2026);
      expect(summary.updatedAt.minute, 5);

      final outJson = summary.toJson();
      expect(outJson['id'], 'conv-123');
      expect(outJson['title'], 'Test Conversation');
    });

    test('ConversationDetail parsing and toChatTurns multi-turn restoration with sources & follow-ups', () {
      final detailJson = {
        'id': 'conv-456',
        'title': 'Multi-turn Quantum Search',
        'created_at': '2026-09-22T10:00:00Z',
        'updated_at': '2026-09-22T10:15:00Z',
        'turns': [
          {
            'turn_index': 0,
            'question': 'What is quantum superposition?',
            'answer': 'Quantum superposition is a fundamental principle of quantum mechanics...',
            'sources': [
              {
                'title': 'Quantum Superposition - Wikipedia',
                'url': 'https://en.wikipedia.org/wiki/Quantum_superposition',
                'score': 0.89,
              },
            ],
            'follow_ups': [
              'How does superposition differ from entanglement?',
              'What are practical applications?',
            ],
            'created_at': '2026-09-22T10:00:00Z',
          },
          {
            'turn_index': 1,
            'question': 'How does superposition differ from entanglement?',
            'answer': 'While superposition involves a single quantum state existing in multiple possibilities...',
            'sources': [
              {
                'title': 'Entanglement vs Superposition',
                'url': 'https://physics.stackexchange.com/questions/1234',
                'score': 0.81,
              },
            ],
            'follow_ups': [
              'Can quantum computers break RSA?',
            ],
            'created_at': '2026-09-22T10:15:00Z',
          },
        ],
      };

      final detail = ConversationDetail.fromJson(detailJson);
      expect(detail.id, 'conv-456');
      expect(detail.turns.length, 2);

      // Convert to Flutter ChatTurn list
      final chatTurns = detail.toChatTurns();
      expect(chatTurns.length, 2);

      // Turn 0
      final turn0 = chatTurns[0];
      expect(turn0.question, 'What is quantum superposition?');
      expect(turn0.answer, contains('principle of quantum mechanics'));
      expect(turn0.isLoadingSources, isFalse);
      expect(turn0.isLoadingAnswer, isFalse);
      expect(turn0.isStreaming, isFalse);
      expect(turn0.sources.length, 1);
      expect(turn0.sources.first['title'], 'Quantum Superposition - Wikipedia');
      expect(turn0.suggestedFollowUps.length, 2);

      // Turn 1
      final turn1 = chatTurns[1];
      expect(turn1.question, 'How does superposition differ from entanglement?');
      expect(turn1.answer, contains('single quantum state'));
      expect(turn1.isLoadingSources, isFalse);
      expect(turn1.isLoadingAnswer, isFalse);
      expect(turn1.isStreaming, isFalse);
      expect(turn1.sources.length, 1);
      expect(turn1.suggestedFollowUps.length, 1);
    });
  });

  group('ConversationService HTTP REST Tests', () {
    test('listConversations parses multiple conversations', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/conversations');
        return http.Response(
          json.encode([
            {
              'id': 'conv-1',
              'title': 'First Conversation',
              'created_at': '2026-09-22T08:00:00Z',
              'updated_at': '2026-09-22T08:30:00Z',
            },
            {
              'id': 'conv-2',
              'title': 'Second Conversation',
              'created_at': '2026-09-22T09:00:00Z',
              'updated_at': '2026-09-22T09:15:00Z',
            },
          ]),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final service = ConversationService();
      service.setClientForTesting(mockClient);

      final list = await service.listConversations();
      expect(list.length, 2);
      expect(list[0].id, 'conv-1');
      expect(list[1].id, 'conv-2');
    });

    test('getConversation loads detail with multiple turns and metadata', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/conversations/conv-1');
        return http.Response(
          json.encode({
            'id': 'conv-1',
            'title': 'First Conversation',
            'created_at': '2026-09-22T08:00:00Z',
            'updated_at': '2026-09-22T08:30:00Z',
            'turns': [
              {
                'turn_index': 0,
                'question': 'Test query',
                'answer': 'Test answer',
                'sources': [{'title': 'Source A', 'url': 'https://a.com'}],
                'follow_ups': ['Next Q?'],
                'created_at': '2026-09-22T08:00:00Z',
              }
            ],
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final service = ConversationService();
      service.setClientForTesting(mockClient);

      final detail = await service.getConversation('conv-1');
      expect(detail, isNotNull);
      expect(detail!.title, 'First Conversation');
      expect(detail.turns.length, 1);
      expect(detail.turns[0].sources.length, 1);
    });

    test('renameConversation sends PATCH and updates title', () async {
      final mockClient = MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.path, '/api/conversations/conv-1');
        final body = json.decode(request.body) as Map;
        expect(body['title'], 'Renamed Title');

        return http.Response(
          json.encode({
            'id': 'conv-1',
            'title': 'Renamed Title',
            'created_at': '2026-09-22T08:00:00Z',
            'updated_at': '2026-09-22T08:35:00Z',
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final service = ConversationService();
      service.setClientForTesting(mockClient);

      final result = await service.renameConversation('conv-1', 'Renamed Title');
      expect(result, isNotNull);
      expect(result!.title, 'Renamed Title');
    });

    test('deleteConversation sends DELETE and returns true on success', () async {
      final mockClient = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/api/conversations/conv-1');
        return http.Response(json.encode({'status': 'deleted'}), 200);
      });

      final service = ConversationService();
      service.setClientForTesting(mockClient);

      final success = await service.deleteConversation('conv-1');
      expect(success, isTrue);
    });
  });

  group('ChatPage Restoration Widget Tests', () {
    testWidgets('Restores multiple turns, answers, sources, and follow-ups on app start/reinitialization', (tester) async {
      final restoredTurns = [
        ChatTurn(
          question: 'What is photosynthesis?',
          answer: 'Photosynthesis is the process used by plants to convert light into energy.',
          isLoadingSources: false,
          isLoadingAnswer: false,
          isStreaming: false,
          sources: [
            {
              'title': 'Photosynthesis Overview',
              'url': 'https://biology.org/photosynthesis',
            },
          ],
          suggestedFollowUps: [
            'What pigments are involved in photosynthesis?',
          ],
        ),
        ChatTurn(
          question: 'What pigments are involved in photosynthesis?',
          answer: 'The primary pigment is chlorophyll, which absorbs blue and red light.',
          isLoadingSources: false,
          isLoadingAnswer: false,
          isStreaming: false,
          sources: [
            {
              'title': 'Chlorophyll and Pigments',
              'url': 'https://biology.org/pigments',
            },
          ],
          suggestedFollowUps: [
            'Why are leaves green?',
          ],
        ),
      ];

      // Pump ChatPage with restored turns
      await tester.pumpWidget(
        MaterialApp(
          home: ChatPage(
            conversationId: 'restored-conv-id',
            initialTurns: restoredTurns,
          ),
        ),
      );

      // Verify questions are rendered
      expect(find.text('What is photosynthesis?'), findsOneWidget);
      expect(find.text('What pigments are involved in photosynthesis?'), findsOneWidget);

      // Verify answers are rendered in Markdown
      expect(find.textContaining('process used by plants to convert light into energy'), findsOneWidget);
      expect(find.textContaining('primary pigment is chlorophyll'), findsOneWidget);

      // Verify SourcesSection is rendered for each turn
      expect(find.byType(SourcesSection), findsNWidgets(2));

      // Verify FollowUpSection is rendered with latest follow-up suggestions
      expect(find.byType(FollowUpSection), findsOneWidget);
      expect(find.text('Why are leaves green?'), findsOneWidget);
    });

    testWidgets('ChatPage restores single turn properly', (tester) async {
      final singleTurn = [
        ChatTurn(
          question: 'Single Turn Question',
          answer: 'Single Turn Answer content text.',
          isLoadingSources: false,
          isLoadingAnswer: false,
          isStreaming: false,
          sources: [],
          suggestedFollowUps: ['Followup Q1'],
        ),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: ChatPage(
            conversationId: 'conv-single',
            initialTurns: singleTurn,
          ),
        ),
      );

      expect(find.text('Single Turn Question'), findsOneWidget);
      expect(find.textContaining('Single Turn Answer content text'), findsOneWidget);
      expect(find.text('Followup Q1'), findsOneWidget);
    });
  });
}
