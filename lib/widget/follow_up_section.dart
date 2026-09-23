import 'package:research_os/theme/colors.dart';
import 'package:flutter/material.dart';

class FollowUpSection extends StatefulWidget {
  final List<String> suggestedQuestions;
  final ValueChanged<String> onSubmitted;
  final bool isGenerating;

  const FollowUpSection({
    super.key,
    this.suggestedQuestions = const [],
    required this.onSubmitted,
    this.isGenerating = false,
  });

  @override
  State<FollowUpSection> createState() => _FollowUpSectionState();
}

class _FollowUpSectionState extends State<FollowUpSection> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      final hasText = _controller.text.trim().isNotEmpty;
      if (hasText != _hasText) {
        setState(() {
          _hasText = hasText;
        });
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _handleSubmitted() {
    final text = _controller.text.trim();
    if (text.isEmpty || widget.isGenerating) return;
    _controller.clear();
    widget.onSubmitted(text);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Suggested follow-up questions
        if (widget.suggestedQuestions.isNotEmpty) ...[
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
                'Follow-up questions',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Column(
            children: widget.suggestedQuestions.map((question) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: _SuggestedQuestionCard(
                  question: question,
                  isEnabled: !widget.isGenerating,
                  onTap: () {
                    if (!widget.isGenerating) {
                      widget.onSubmitted(question);
                    }
                  },
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),
        ],

        // Interactive "Ask a follow up" floating pill input bar
        AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          decoration: BoxDecoration(
            color: AppColors.searchBar,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: _focusNode.hasFocus
                  ? AppColors.submitButton.withValues(alpha: 0.8)
                  : AppColors.searchBarBorder,
              width: 1.5,
            ),
            boxShadow: _focusNode.hasFocus
                ? [
                    BoxShadow(
                      color: AppColors.submitButton.withValues(alpha: 0.12),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.25),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
          ),
          child: Row(
            children: [
              const SizedBox(width: 18),
              Icon(
                Icons.chat_bubble_outline_rounded,
                color: _focusNode.hasFocus
                    ? AppColors.submitButton
                    : AppColors.iconGrey,
                size: 18,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  enabled: !widget.isGenerating,
                  onSubmitted: (_) => _handleSubmitted(),
                  style: const TextStyle(
                    color: AppColors.whiteColor,
                    fontSize: 15,
                    fontWeight: FontWeight.w400,
                  ),
                  decoration: InputDecoration(
                    hintText: widget.isGenerating
                        ? 'Generating response...'
                        : 'Ask a follow up...',
                    hintStyle: const TextStyle(
                      color: AppColors.textGrey,
                      fontSize: 15,
                    ),
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(right: 6.0),
                child: GestureDetector(
                  onTap: (_hasText && !widget.isGenerating) ? _handleSubmitted : null,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: (_hasText && !widget.isGenerating)
                          ? AppColors.submitButton
                          : AppColors.proButton,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.arrow_forward,
                      color: (_hasText && !widget.isGenerating)
                          ? AppColors.background
                          : AppColors.iconGrey,
                      size: 16,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SuggestedQuestionCard extends StatefulWidget {
  final String question;
  final VoidCallback onTap;
  final bool isEnabled;

  const _SuggestedQuestionCard({
    required this.question,
    required this.onTap,
    required this.isEnabled,
  });

  @override
  State<_SuggestedQuestionCard> createState() => _SuggestedQuestionCardState();
}

class _SuggestedQuestionCardState extends State<_SuggestedQuestionCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      cursor: widget.isEnabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      child: GestureDetector(
        onTap: widget.isEnabled ? widget.onTap : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 13),
          decoration: BoxDecoration(
            color: _isHovered ? AppColors.cardHover : AppColors.cardColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _isHovered
                  ? AppColors.submitButton.withValues(alpha: 0.55)
                  : AppColors.cardBorder,
              width: 1,
            ),
            boxShadow: _isHovered
                ? [
                    BoxShadow(
                      color: AppColors.submitButton.withValues(alpha: 0.08),
                      blurRadius: 12,
                      offset: const Offset(0, 3),
                    ),
                  ]
                : null,
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  widget.question,
                  style: TextStyle(
                    color: _isHovered ? AppColors.whiteColor : AppColors.textPrimary,
                    fontSize: 14.5,
                    height: 1.35,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                padding: const EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: _isHovered
                      ? AppColors.submitButton.withValues(alpha: 0.15)
                      : AppColors.cardBorder,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.arrow_forward_rounded,
                  color: _isHovered ? AppColors.submitButton : AppColors.iconGrey,
                  size: 14,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

