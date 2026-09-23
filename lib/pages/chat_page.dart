import 'dart:async';
import 'package:research_os/services/chat_web_services.dart';
import 'package:research_os/theme/colors.dart';
import 'package:research_os/utils/app_logger.dart';
import 'package:research_os/widget/answer_section.dart';
import 'package:research_os/widget/follow_up_section.dart';
import 'package:research_os/widget/side_bar.dart';
import 'package:research_os/widget/sources_section.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

class ChatTurn {
  final String question;
  List sources;
  String answer;
  bool isLoadingSources;
  bool isLoadingAnswer;
  bool isStreaming;
  List<String> suggestedFollowUps;

  ChatTurn({
    required this.question,
    List? sources,
    this.answer = '',
    this.isLoadingSources = true,
    this.isLoadingAnswer = true,
    this.isStreaming = false,
    List<String>? suggestedFollowUps,
  })  : sources = sources ?? [],
        suggestedFollowUps = suggestedFollowUps ?? [];
}

class ChatPage extends StatefulWidget {
  final String? question;
  final String? conversationId;
  final List<ChatTurn>? initialTurns;
  final String? mode;
  final List<String>? documentIds;

  const ChatPage({
    super.key,
    this.question,
    this.conversationId,
    this.initialTurns,
    this.mode,
    this.documentIds,
  }) : assert(question != null || initialTurns != null, 'Either question or initialTurns must be provided');

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final List<ChatTurn> _turns = [];
  final ScrollController _scrollController = ScrollController();
  String? _conversationId;
  String? _mode;
  List<String>? _documentIds;
  StreamSubscription? _searchSubscription;
  StreamSubscription? _contentSubscription;
  StreamSubscription? _followUpSubscription;
  StreamSubscription? _conversationIdSubscription;
  StreamSubscription? _errorSubscription;

  @override
  void initState() {
    super.initState();
    _conversationId = widget.conversationId;
    _mode = widget.mode;
    _documentIds = widget.documentIds;

    if (widget.initialTurns != null && widget.initialTurns!.isNotEmpty) {
      _turns.addAll(widget.initialTurns!);
      AppLogger.info(
        'Restored ${_turns.length} turns for conversation: $_conversationId',
        tag: 'UI',
      );
    } else if (widget.question != null && widget.question!.isNotEmpty) {
      AppLogger.info('Initializing ChatPage for query: "${widget.question}"', tag: 'UI');
      _turns.add(ChatTurn(question: widget.question!));
    }

    _conversationIdSubscription =
        ChatWebService().conversationIdStream.listen((id) {
      if (mounted && id.isNotEmpty) {
        setState(() {
          _conversationId = id;
        });
      }
    });

    // Populate cached search results if received before subscription
    if (ChatWebService().lastSearchResults != null && _turns.isNotEmpty) {
      final activeTurn = _turns.last;
      activeTurn.sources = ChatWebService().lastSearchResults!['data'] ?? [];
      activeTurn.isLoadingSources = false;
    }

    // Populate cached answer if tokens were received before subscription
    if (ChatWebService().accumulatedAnswer.isNotEmpty && _turns.isNotEmpty) {
      final activeTurn = _turns.last;
      activeTurn.answer = ChatWebService().accumulatedAnswer;
      activeTurn.isLoadingAnswer = false;
      activeTurn.isStreaming = ChatWebService().isStreamingAnswer;
    }

    // Listen to search results stream
    _searchSubscription = ChatWebService().searchResultStream.listen(
      (data) {
        if (!mounted || _turns.isEmpty) return;
        setState(() {
          final activeTurn = _turns.last;
          activeTurn.sources = data['data'] ?? [];
          activeTurn.isLoadingSources = false;
        });
      },
      onError: (error) {
        AppLogger.error('Search results stream error in ChatPage: $error', tag: 'UI');
      },
    );

    // Listen to content stream
    _contentSubscription = ChatWebService().contentStream.listen(
      (data) {
        if (!mounted || _turns.isEmpty) return;
        final type = data['type'];
        setState(() {
          final activeTurn = _turns.last;
          if (type == 'done') {
            activeTurn.isStreaming = false;
          } else {
            if (activeTurn.isLoadingAnswer) {
              activeTurn.answer = '';
              activeTurn.isLoadingAnswer = false;
              activeTurn.isStreaming = true;
            }
            activeTurn.answer += (data['data'] ?? '');
          }
        });
        _scrollToBottom();
      },
      onError: (error) {
        AppLogger.error('Content stream error in ChatPage: $error', tag: 'UI');
      },
    );

    // Listen to suggested follow-ups stream
    _followUpSubscription = ChatWebService().followUpStream.listen(
      (data) {
        if (!mounted || _turns.isEmpty) return;
        final rawList = data['data'] as List?;
        if (rawList != null) {
          setState(() {
            _turns.last.suggestedFollowUps =
                rawList.map((e) => e.toString()).toList();
          });
          _scrollToBottom();
        }
      },
      onError: (error) {
        AppLogger.error('Follow-up stream error in ChatPage: $error', tag: 'UI');
      },
    );

    // Listen to error stream
    _errorSubscription = ChatWebService().errorStream.listen(
      (errorMessage) {
        if (!mounted || _turns.isEmpty) return;
        setState(() {
          final activeTurn = _turns.last;
          activeTurn.isLoadingAnswer = false;
          activeTurn.isLoadingSources = false;
          activeTurn.isStreaming = false;
          if (activeTurn.answer.isEmpty) {
            activeTurn.answer = '⚠️ $errorMessage';
          }
        });
      },
    );
  }

  @override
  void dispose() {
    _searchSubscription?.cancel();
    _contentSubscription?.cancel();
    _followUpSubscription?.cancel();
    _conversationIdSubscription?.cancel();
    _errorSubscription?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _handleFollowUpSubmitted(String question) {
    final query = question.trim();
    if (query.isEmpty) return;

    final activeTurn = _turns.last;
    if (activeTurn.isLoadingAnswer || activeTurn.isStreaming) {
      AppLogger.warn('Cannot ask follow-up while generating response', tag: 'UI');
      return;
    }

    AppLogger.info('User submitted follow-up question: "$query"', tag: 'UI');

    // Compile previous turns as history
    final history = _turns.map((turn) => {
      'query': turn.question,
      'answer': turn.answer,
    }).toList();

    setState(() {
      _turns.add(ChatTurn(question: query));
    });

    ChatWebService().chat(
      query,
      history: history,
      conversationId: _conversationId,
      mode: _mode,
      documentIds: _documentIds,
    );
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    final isGenerating = _turns.isNotEmpty &&
        (_turns.last.isLoadingAnswer || _turns.last.isStreaming);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Row(
        children: [
          kIsWeb ? const SideBar() : const SizedBox(),
          Expanded(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 880),
                child: SingleChildScrollView(
                  controller: _scrollController,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32.0,
                    vertical: 24.0,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Top navigation bar
                      Row(
                        children: [
                          InkWell(
                            onTap: () {
                              AppLogger.info('Navigating back to Home', tag: 'UI');
                              Navigator.of(context).pop();
                            },
                            borderRadius: BorderRadius.circular(8),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: AppColors.cardColor,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: AppColors.cardBorder),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.arrow_back_rounded,
                                    size: 15,
                                    color: AppColors.textSecondary,
                                  ),
                                  SizedBox(width: 6),
                                  Text(
                                    'New Search',
                                    style: TextStyle(
                                      fontSize: 12.5,
                                      color: AppColors.textSecondary,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const Spacer(),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 9,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: AppColors.submitButton.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: AppColors.submitButton.withValues(alpha: 0.25),
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  _mode == 'rag' ? Icons.description_outlined : Icons.auto_awesome,
                                  size: 13,
                                  color: AppColors.submitButton,
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  _mode == 'rag'
                                      ? (_documentIds != null && _documentIds!.isNotEmpty
                                          ? 'Document RAG (${_documentIds!.length} docs)'
                                          : 'Document RAG')
                                      : 'ResearchOS',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.submitButton,
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: 0.2,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),

                      // Render each conversation turn
                      for (int i = 0; i < _turns.length; i++) ...[
                        if (i > 0) ...[
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 36.0),
                            child: Divider(
                              color: AppColors.searchBarBorder,
                              thickness: 1,
                            ),
                          ),
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 7,
                                  vertical: 3,
                                ),
                                decoration: BoxDecoration(
                                  color: AppColors.submitButton.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: const Text(
                                  'Follow-up',
                                  style: TextStyle(
                                    color: AppColors.submitButton,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  _turns[i].question,
                                  style: const TextStyle(
                                    fontSize: 24,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.whiteColor,
                                    letterSpacing: -0.3,
                                    height: 1.3,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ] else ...[
                          Text(
                            _turns[0].question,
                            style: const TextStyle(
                              fontSize: 32,
                              fontWeight: FontWeight.w700,
                              color: AppColors.whiteColor,
                              letterSpacing: -0.5,
                              height: 1.25,
                            ),
                          ),
                        ],
                        const SizedBox(height: 20),
                        SourcesSection(
                          sources: _turns[i].sources,
                          isLoading: _turns[i].isLoadingSources,
                        ),
                        const SizedBox(height: 24),
                        AnswerSection(
                          answer: _turns[i].answer,
                          isLoading: _turns[i].isLoadingAnswer,
                          isStreaming: _turns[i].isStreaming,
                        ),
                      ],

                      const SizedBox(height: 36),

                      // Follow-up section (suggested questions + input bar)
                      FollowUpSection(
                        suggestedQuestions: _turns.isNotEmpty
                            ? _turns.last.suggestedFollowUps
                            : const [],
                        onSubmitted: _handleFollowUpSubmitted,
                        isGenerating: isGenerating,
                      ),

                      const SizedBox(height: 60),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}