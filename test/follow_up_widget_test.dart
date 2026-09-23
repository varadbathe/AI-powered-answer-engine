import 'package:research_os/widget/follow_up_section.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('FollowUpSection renders input bar and handles typing submission',
      (WidgetTester tester) async {
    String? submittedQuery;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: FollowUpSection(
            onSubmitted: (query) {
              submittedQuery = query;
            },
          ),
        ),
      ),
    );

    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('Ask a follow up...'), findsOneWidget);

    // Enter text
    await tester.enterText(find.byType(TextField), 'What is quantum entanglement?');
    await tester.pump();

    // Tap submit button (arrow icon)
    await tester.tap(find.byIcon(Icons.arrow_forward));
    await tester.pump();

    expect(submittedQuery, equals('What is quantum entanglement?'));
  });

  testWidgets('FollowUpSection renders suggested question chips and handles taps',
      (WidgetTester tester) async {
    String? submittedQuery;
    final suggestions = [
      'What are qubits?',
      'How does superposition work?',
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: FollowUpSection(
            suggestedQuestions: suggestions,
            onSubmitted: (query) {
              submittedQuery = query;
            },
          ),
        ),
      ),
    );

    expect(find.text('Follow-up questions'), findsOneWidget);
    expect(find.text('What are qubits?'), findsOneWidget);
    expect(find.text('How does superposition work?'), findsOneWidget);

    // Tap first suggested question
    await tester.tap(find.text('What are qubits?'));
    await tester.pump();

    expect(submittedQuery, equals('What are qubits?'));
  });

  testWidgets('FollowUpSection disables interaction when isGenerating is true',
      (WidgetTester tester) async {
    String? submittedQuery;
    final suggestions = ['Sample question?'];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: FollowUpSection(
            suggestedQuestions: suggestions,
            isGenerating: true,
            onSubmitted: (query) {
              submittedQuery = query;
            },
          ),
        ),
      ),
    );

    expect(find.text('Generating response...'), findsOneWidget);

    // Try tapping suggestion
    await tester.tap(find.text('Sample question?'));
    await tester.pump();

    expect(submittedQuery, isNull);
  });
}
