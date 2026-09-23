import 'package:research_os/models/conversation.dart';
import 'package:research_os/pages/chat_page.dart';
import 'package:research_os/pages/home_page.dart';
import 'package:research_os/services/conversation_service.dart';
import 'package:research_os/theme/colors.dart';
import 'package:research_os/widget/document_management_dialog.dart';
import 'package:research_os/widget/side_bar_buttons.dart';
import 'package:flutter/material.dart';

class SideBar extends StatefulWidget {
  const SideBar({super.key});

  @override
  State<SideBar> createState() => _SideBarState();
}

class _SideBarState extends State<SideBar> {
  bool isCollapsed = true;

  void _navigateToHome() {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const HomePage()),
      (route) => false,
    );
  }

  void _showConversationLibrary() {
    showDialog(
      context: context,
      builder: (ctx) {
        return const _ConversationHistoryDialog();
      },
    );
  }

  void _showDocumentKnowledge() {
    showDialog(
      context: context,
      builder: (ctx) {
        return const DocumentManagementDialog();
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 100),
      width: isCollapsed ? 64 : 150,
      decoration: const BoxDecoration(
        color: AppColors.sideNav,
        border: Border(
          right: BorderSide(
            color: AppColors.sideNavBorder,
            width: 1,
          ),
        ),
      ),
      child: Column(
        children: [
          const SizedBox(height: 20),
          GestureDetector(
            onTap: _navigateToHome,
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.cardColor,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.cardBorder),
              ),
              child: Icon(
                Icons.auto_awesome_mosaic_rounded,
                color: AppColors.submitButton,
                size: isCollapsed ? 22 : 28,
              ),
            ),
          ),

          Expanded(
            child: Column(
              crossAxisAlignment: isCollapsed
                  ? CrossAxisAlignment.center
                  : CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 24),
                SideBarButton(
                  isCollapsed: isCollapsed,
                  icon: Icons.add,
                  text: "Home",
                  onTap: _navigateToHome,
                ),
                SideBarButton(
                  isCollapsed: isCollapsed,
                  icon: Icons.search,
                  text: "Search",
                  onTap: _navigateToHome,
                ),
                SideBarButton(
                  isCollapsed: isCollapsed,
                  icon: Icons.language,
                  text: "Spaces",
                ),
                SideBarButton(
                  isCollapsed: isCollapsed,
                  icon: Icons.auto_awesome,
                  text: "Discover",
                ),
                SideBarButton(
                  isCollapsed: isCollapsed,
                  icon: Icons.cloud_outlined,
                  text: "Library",
                  onTap: _showConversationLibrary,
                ),
                SideBarButton(
                  isCollapsed: isCollapsed,
                  icon: Icons.folder_copy_outlined,
                  text: "Knowledge",
                  onTap: _showDocumentKnowledge,
                ),
                const Spacer(),
              ],
            ),
          ),
          GestureDetector(
            onTap: () {
              setState(() {
                isCollapsed = !isCollapsed;
              });
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 100),
              margin: const EdgeInsets.symmetric(vertical: 14),
              child: Icon(
                isCollapsed
                    ? Icons.keyboard_arrow_right
                    : Icons.keyboard_arrow_left,
                color: AppColors.iconGrey,
                size: 22,
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _ConversationHistoryDialog extends StatefulWidget {
  const _ConversationHistoryDialog();

  @override
  State<_ConversationHistoryDialog> createState() => _ConversationHistoryDialogState();
}

class _ConversationHistoryDialogState extends State<_ConversationHistoryDialog> {
  late Future<List<ConversationSummary>> _futureConversations;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    setState(() {
      _futureConversations = ConversationService().listConversations();
    });
  }

  Future<void> _openConversation(ConversationSummary summary) async {
    final nav = Navigator.of(context);
    final detail = await ConversationService().getConversation(summary.id);
    if (!mounted) return;

    if (detail != null) {
      final turns = detail.toChatTurns();
      nav.pop(); // Close dialog
      nav.push(
        MaterialPageRoute(
          builder: (_) => ChatPage(
            conversationId: detail.id,
            initialTurns: turns,
          ),
        ),
      );
    }
  }

  Future<void> _renameConversation(ConversationSummary summary) async {
    final controller = TextEditingController(text: summary.title);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.cardColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.cardBorder),
        ),
        title: const Text(
          'Rename Conversation',
          style: TextStyle(color: AppColors.whiteColor, fontSize: 16),
        ),
        content: TextField(
          controller: controller,
          autofocus: true,
          style: const TextStyle(color: AppColors.textPrimary),
          decoration: const InputDecoration(
            hintText: 'Enter conversation title...',
            hintStyle: TextStyle(color: AppColors.textGrey),
            enabledBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: AppColors.searchBarBorder),
            ),
            focusedBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: AppColors.submitButton),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel', style: TextStyle(color: AppColors.textGrey)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.submitButton,
              foregroundColor: AppColors.background,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (confirmed == true && controller.text.trim().isNotEmpty) {
      await ConversationService().renameConversation(summary.id, controller.text.trim());
      _refresh();
    }
    controller.dispose();
  }

  Future<void> _deleteConversation(ConversationSummary summary) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.cardColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.cardBorder),
        ),
        title: const Text(
          'Delete Conversation',
          style: TextStyle(color: AppColors.whiteColor, fontSize: 16),
        ),
        content: Text(
          'Are you sure you want to delete "${summary.title}"?',
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel', style: TextStyle(color: AppColors.textGrey)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.redAccent.shade700,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ConversationService().deleteConversation(summary.id);
      _refresh();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.cardColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppColors.cardBorder),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 580, maxHeight: 540),
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.history_rounded,
                    color: AppColors.submitButton,
                    size: 22,
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    'Conversation Library',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: AppColors.whiteColor,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close, color: AppColors.iconGrey, size: 20),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(color: AppColors.cardBorder, height: 1),
              const SizedBox(height: 12),
              Expanded(
                child: FutureBuilder<List<ConversationSummary>>(
                  future: _futureConversations,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(
                        child: CircularProgressIndicator(
                          color: AppColors.submitButton,
                          strokeWidth: 2,
                        ),
                      );
                    }

                    final conversations = snapshot.data ?? [];
                    if (conversations.isEmpty) {
                      return Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(
                              Icons.chat_bubble_outline_rounded,
                              size: 40,
                              color: AppColors.iconGrey,
                            ),
                            SizedBox(height: 12),
                            Text(
                              'No saved conversations yet',
                              style: TextStyle(color: AppColors.textGrey, fontSize: 14),
                            ),
                          ],
                        ),
                      );
                    }

                    return ListView.separated(
                      itemCount: conversations.length,
                      separatorBuilder: (_, _) => const Divider(
                        color: AppColors.searchBarBorder,
                        height: 1,
                      ),
                      itemBuilder: (context, index) {
                        final conv = conversations[index];
                        return ListTile(
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          leading: const Icon(
                            Icons.chat_bubble_outline_rounded,
                            color: AppColors.iconGrey,
                            size: 18,
                          ),
                          title: Text(
                            conv.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          subtitle: Text(
                            '${conv.updatedAt.month}/${conv.updatedAt.day}/${conv.updatedAt.year}',
                            style: const TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 11,
                            ),
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.edit_outlined, size: 16, color: AppColors.iconGrey),
                                tooltip: 'Rename',
                                onPressed: () => _renameConversation(conv),
                              ),
                              IconButton(
                                icon: const Icon(Icons.delete_outline, size: 16, color: AppColors.iconGrey),
                                tooltip: 'Delete',
                                onPressed: () => _deleteConversation(conv),
                              ),
                            ],
                          ),
                          onTap: () => _openConversation(conv),
                        );
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}