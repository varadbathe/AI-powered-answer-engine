import 'dart:async';
import 'package:ai_answer_engine/services/chat_web_services.dart';
import 'package:ai_answer_engine/theme/colors.dart';
import 'package:ai_answer_engine/utils/app_logger.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:skeletonizer/skeletonizer.dart';

class AnswerSection extends StatefulWidget {
  final String? answer;
  final bool? isLoading;
  final bool? isStreaming;

  const AnswerSection({
    super.key,
    this.answer,
    this.isLoading,
    this.isStreaming,
  });

  @override
  State<AnswerSection> createState() => _AnswerSectionState();
}

class _AnswerSectionState extends State<AnswerSection> {
  bool isLoading = true;
  bool isStreaming = false;
  StreamSubscription? _subscription;
  String fullResponse = '';

  static const String _placeholderText = '''
Synthesizing real-time information from verified web sources across the globe to formulate an accurate and comprehensive answer.
Analyzing historical records, recent news, career statistics, and notable milestones to deliver structured and detailed context.
Structuring findings into a concise overview highlighting key achievements, performance metrics, and relevant updates.
Evaluating additional references and cross-verifying citations to ensure the highest standard of accuracy and relevance.
''';

  @override
  void initState() {
    super.initState();
    if (widget.answer != null) {
      fullResponse = widget.answer!;
      isLoading = widget.isLoading ?? false;
      isStreaming = widget.isStreaming ?? false;
      return;
    }

    _subscription = ChatWebService().contentStream.listen(
      (data) {
        final type = data['type'];
        if (type == 'done') {
          AppLogger.info('Answer generation finished.', tag: 'UI');
          if (mounted) {
            setState(() {
              isStreaming = false;
            });
          }
          return;
        }

        final chunk = data['data'] ?? '';
        if (mounted) {
          setState(() {
            if (isLoading) {
              fullResponse = "";
              isLoading = false;
              isStreaming = true;
            }
            fullResponse += chunk;
          });
        }
      },
      onError: (error) {
        AppLogger.error('AnswerSection stream error: $error', tag: 'UI');
        if (mounted) {
          setState(() {
            isLoading = false;
            isStreaming = false;
          });
        }
      },
      onDone: () {
        AppLogger.info('Answer streaming complete.', tag: 'UI');
        if (mounted) {
          setState(() {
            isStreaming = false;
          });
        }
      },
    );
  }

  @override
  void didUpdateWidget(covariant AnswerSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.answer != null) {
      setState(() {
        fullResponse = widget.answer!;
        isLoading = widget.isLoading ?? false;
        isStreaming = widget.isStreaming ?? false;
      });
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final activeAnswer = widget.answer ?? fullResponse;
    final activeLoading = widget.isLoading ?? isLoading;
    final activeStreaming = widget.isStreaming ?? isStreaming;
    final showBreathing = activeLoading || activeStreaming;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppColors.submitButton.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(
                Icons.auto_awesome,
                color: AppColors.submitButton,
                size: 16,
              ),
            ),
            const SizedBox(width: 10),
            const Text(
              'Answer',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: -0.2,
              ),
            ),
            if (showBreathing) ...[
              const SizedBox(width: 10),
              const _BreathingIndicator(),
            ],
            const Spacer(),
            if (!activeLoading && activeAnswer.isNotEmpty) ...[
              _AnswerActionButton(
                icon: Icons.copy_rounded,
                tooltip: 'Copy Answer',
                onTap: () {
                  Clipboard.setData(ClipboardData(text: activeAnswer));
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: const Row(
                        children: [
                          Icon(Icons.check_circle_outline, color: AppColors.submitButton, size: 18),
                          SizedBox(width: 8),
                          Text('Answer copied to clipboard', style: TextStyle(color: Colors.white)),
                        ],
                      ),
                      backgroundColor: AppColors.cardColor,
                      behavior: SnackBarBehavior.floating,
                      duration: const Duration(seconds: 2),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: const BorderSide(color: AppColors.searchBarBorder),
                      ),
                    ),
                  );
                },
              ),
            ],
          ],
        ),
        const SizedBox(height: 14),
        Skeletonizer(
          enabled: activeLoading,
          effect: const PulseEffect(
            from: AppColors.cardColor,
            to: Color(0xFF2E3235),
            duration: Duration(milliseconds: 1400),
          ),
          child: Markdown(
            data: activeLoading ? _placeholderText : activeAnswer,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
              p: const TextStyle(
                fontSize: 15.5,
                height: 1.68,
                color: Color(0xFFD6DADC),
                letterSpacing: 0.1,
              ),
              strong: const TextStyle(
                fontWeight: FontWeight.w700,
                color: Colors.white,
              ),
              h1: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: Colors.white,
                height: 1.4,
              ),
              h2: const TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w700,
                color: Colors.white,
                height: 1.4,
              ),
              h3: const TextStyle(
                fontSize: 16.5,
                fontWeight: FontWeight.w600,
                color: Color(0xFFF0F3F5),
                height: 1.4,
              ),
              listBullet: const TextStyle(
                color: AppColors.submitButton,
                fontSize: 15,
                fontWeight: FontWeight.bold,
              ),
              blockSpacing: 16.0,
              listIndent: 22.0,
              codeblockDecoration: BoxDecoration(
                color: const Color(0xFF181A1B),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.cardBorder),
              ),
              codeblockPadding: const EdgeInsets.all(16),
              code: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 13.5,
                color: Color(0xFF64D2FF),
                backgroundColor: Color(0xFF232628),
              ),
              horizontalRuleDecoration: const BoxDecoration(
                border: Border(
                  top: BorderSide(
                    color: AppColors.searchBarBorder,
                    width: 1,
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _AnswerActionButton extends StatefulWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  const _AnswerActionButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  State<_AnswerActionButton> createState() => _AnswerActionButtonState();
}

class _AnswerActionButtonState extends State<_AnswerActionButton> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      cursor: SystemMouseCursors.click,
      child: Tooltip(
        message: widget.tooltip,
        child: GestureDetector(
          onTap: widget.onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 140),
            padding: const EdgeInsets.all(7),
            decoration: BoxDecoration(
              color: _isHovered ? AppColors.cardHover : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: _isHovered ? AppColors.cardBorder : Colors.transparent,
              ),
            ),
            child: Icon(
              widget.icon,
              size: 16,
              color: _isHovered ? AppColors.whiteColor : AppColors.iconGrey,
            ),
          ),
        ),
      ),
    );
  }
}


/// A subtle, pulsing breathing indicator badge shown while the response is being generated
class _BreathingIndicator extends StatefulWidget {
  const _BreathingIndicator();

  @override
  State<_BreathingIndicator> createState() => _BreathingIndicatorState();
}

class _BreathingIndicatorState extends State<_BreathingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacityAnimation;
  late final Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    _opacityAnimation = Tween<double>(begin: 0.35, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
    _scaleAnimation = Tween<double>(begin: 0.88, end: 1.05).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Opacity(
          opacity: _opacityAnimation.value,
          child: Transform.scale(
            scale: _scaleAnimation.value,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: AppColors.submitButton.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: AppColors.submitButton.withValues(alpha: 0.4),
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: AppColors.submitButton,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Generating...',
                    style: TextStyle(
                      color: AppColors.submitButton,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}