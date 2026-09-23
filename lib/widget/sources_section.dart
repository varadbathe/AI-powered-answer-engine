import 'dart:async';
import 'package:research_os/services/chat_web_services.dart';
import 'package:research_os/theme/colors.dart';
import 'package:research_os/utils/app_logger.dart';
import 'package:flutter/material.dart';
import 'package:skeletonizer/skeletonizer.dart';

class SourcesSection extends StatefulWidget {
  final List? sources;
  final bool? isLoading;

  const SourcesSection({
    super.key,
    this.sources,
    this.isLoading,
  });

  @override
  State<SourcesSection> createState() => _SourcesSectionState();
}

class _SourcesSectionState extends State<SourcesSection> {
  bool isLoading = true;
  StreamSubscription? _subscription;
  List searchResults = [
    {
      'title': 'Loading source 1...',
      'url': 'https://example.com/source1',
    },
    {
      'title': 'Loading source 2...',
      'url': 'https://example.com/source2',
    },
    {
      'title': 'Loading source 3...',
      'url': 'https://example.com/source3',
    },
  ];

  @override
  void initState() {
    super.initState();
    if (widget.sources != null) {
      searchResults = widget.sources!;
      isLoading = widget.isLoading ?? false;
      return;
    }

    _subscription = ChatWebService().searchResultStream.listen(
      (data) {
        AppLogger.info(
          'SourcesSection updated with ${(data['data'] as List?)?.length ?? 0} sources',
          tag: 'UI',
        );
        if (mounted) {
          setState(() {
            searchResults = data['data'] ?? [];
            isLoading = false;
          });
        }
      },
      onError: (error) {
        AppLogger.error('SourcesSection stream error: $error', tag: 'UI');
      },
    );
  }

  @override
  void didUpdateWidget(covariant SourcesSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.sources != null) {
      setState(() {
        searchResults = widget.sources!;
        isLoading = widget.isLoading ?? false;
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
    final displayLoading = widget.isLoading ?? isLoading;
    final rawResults = widget.sources ?? searchResults;
    final displayResults = (displayLoading && rawResults.isEmpty)
        ? [
            {'title': 'Finding relevant sources...', 'url': ''},
            {'title': 'Loading document context...', 'url': ''},
            {'title': 'Analyzing passages...', 'url': ''},
          ]
        : rawResults;

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
                Icons.auto_stories_outlined,
                color: AppColors.submitButton,
                size: 16,
              ),
            ),
            const SizedBox(width: 10),
            const Text(
              "Sources",
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: -0.2,
              ),
            ),
            if (!displayLoading && displayResults.isNotEmpty) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.cardHover,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.cardBorder),
                ),
                child: Text(
                  '${displayResults.length}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 14),
        Skeletonizer(
          enabled: displayLoading,
          effect: const PulseEffect(
            from: AppColors.cardColor,
            to: Color(0xFF2E3235),
            duration: Duration(milliseconds: 1400),
          ),
          child: Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              for (int i = 0; i < displayResults.length; i++)
                _SourceCard(
                  result: displayResults[i],
                  index: i + 1,
                  isLoading: displayLoading,
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SourceCard extends StatefulWidget {
  final dynamic result;
  final int index;
  final bool isLoading;

  const _SourceCard({
    required this.result,
    required this.index,
    required this.isLoading,
  });

  @override
  State<_SourceCard> createState() => _SourceCardState();
}

class _SourceCardState extends State<_SourceCard> {
  bool _isHovered = false;

  String _extractDomain(String rawUrl) {
    try {
      final uri = Uri.parse(rawUrl);
      var host = uri.host;
      if (host.startsWith('www.')) host = host.substring(4);
      return host.isNotEmpty ? host : rawUrl;
    } catch (_) {
      return rawUrl;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDoc = widget.result is Map &&
        (widget.result['type'] == 'document' || widget.result['page_number'] != null);
    final title = widget.result['title']?.toString() ?? 'Source';
    final url = widget.result['url']?.toString() ?? '';
    final domain = isDoc ? url : _extractDomain(url);

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      cursor: widget.isLoading ? SystemMouseCursors.basic : SystemMouseCursors.click,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        width: 185,
        height: 92,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: _isHovered ? AppColors.cardHover : AppColors.cardColor,
          borderRadius: BorderRadius.circular(10),
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
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Top row: domain/page and index badge
            Row(
              children: [
                Icon(
                  isDoc ? Icons.description_outlined : Icons.public_rounded,
                  size: 12,
                  color: isDoc ? AppColors.submitButton : AppColors.textSecondary,
                ),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    domain,
                    style: TextStyle(
                      color: isDoc ? AppColors.submitButton : AppColors.textSecondary,
                      fontSize: 11,
                      fontWeight: isDoc ? FontWeight.w600 : FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: AppColors.cardBorder,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${widget.index}',
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.textGrey,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            // Bottom title
            Text(
              title,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 12.5,
                height: 1.3,
                color: _isHovered ? AppColors.whiteColor : AppColors.textPrimary,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}