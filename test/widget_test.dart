import 'package:flutter_test/flutter_test.dart';
import 'package:ai_answer_engine/widget/answer_section.dart';
import 'package:flutter/material.dart';

void main() {
  testWidgets('Smoke test verifying answer widget hierarchy', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: AnswerSection(),
        ),
      ),
    );
    expect(find.text('Answer'), findsOneWidget);
  });
}
