import 'package:research_os/pages/chat_page.dart';
import 'package:research_os/services/chat_web_services.dart';
import 'package:research_os/theme/colors.dart';
import 'package:research_os/utils/app_logger.dart';
import 'package:research_os/widget/document_management_dialog.dart';
import 'package:research_os/widget/search_bar_button.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class SearchSection extends StatefulWidget {
  const SearchSection({super.key});

  @override
  State<SearchSection> createState() => _SearchSectionState();
}

class _SearchSectionState extends State<SearchSection> {
  final queryController = TextEditingController();
  Set<String> _selectedDocumentIds = {};

  @override
  void dispose() {
    queryController.dispose();
    super.dispose();
  }

  void _openDocumentPicker() async {
    final result = await showDialog<Set<String>>(
      context: context,
      builder: (ctx) => DocumentManagementDialog(
        initialSelectedIds: _selectedDocumentIds,
        onSelectionChanged: (updated) {
          setState(() {
            _selectedDocumentIds = updated;
          });
        },
      ),
    );
    if (result != null) {
      setState(() {
        _selectedDocumentIds = result;
      });
    }
  }

  void _submitSearch() {
    final query = queryController.text.trim();
    if (query.isEmpty) {
      AppLogger.warn('Attempted to search with empty query', tag: 'UI');
      return;
    }
    final isRag = _selectedDocumentIds.isNotEmpty;
    final mode = isRag ? 'rag' : 'search';
    final docList = isRag ? _selectedDocumentIds.toList() : null;

    AppLogger.info('User submitted search: "$query" (mode: $mode, docs: ${docList?.length ?? 0})', tag: 'UI');
    ChatWebService().chat(query, mode: mode, documentIds: docList);
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => ChatPage(
          question: query,
          mode: mode,
          documentIds: docList,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          'Where knowledge begins',
          style: GoogleFonts.ibmPlexMono(
            fontSize: 40,
            fontWeight: FontWeight.w400,
            height: 1.2,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 32),
        Container(
          width: 700,
          decoration: BoxDecoration(
            color: AppColors.searchBar,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: AppColors.searchBarBorder,
              width: 1.5,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (_selectedDocumentIds.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(left: 16.0, right: 16.0, top: 12.0),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.submitButton.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppColors.submitButton.withValues(alpha: 0.3)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.description_outlined, size: 14, color: AppColors.submitButton),
                            const SizedBox(width: 6),
                            Text(
                              '${_selectedDocumentIds.length} doc${_selectedDocumentIds.length > 1 ? "s" : ""} attached (RAG Mode)',
                              style: const TextStyle(fontSize: 12, color: AppColors.submitButton, fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(width: 6),
                            GestureDetector(
                              onTap: () => setState(() => _selectedDocumentIds.clear()),
                              child: const Icon(Icons.close, size: 14, color: AppColors.textGrey),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: TextField(
                  controller: queryController,
                  onSubmitted: (_) => _submitSearch(),
                  decoration: const InputDecoration(
                    hintText: 'Search anything...',
                    hintStyle: TextStyle(
                      color: AppColors.textGrey,
                      fontSize: 16,
                    ),
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(10.0),
                child: Row(
                  children: [
                    const SearchBarButton(
                      icon: Icons.auto_awesome_outlined,
                      text: 'Focus',
                    ),
                    const SizedBox(width: 12),
                    SearchBarButton(
                      icon: Icons.add_circle_outline_outlined,
                      text: _selectedDocumentIds.isNotEmpty
                          ? 'Attach (${_selectedDocumentIds.length})'
                          : 'Attach',
                      onTap: _openDocumentPicker,
                    ),
                    const Spacer(),
                    GestureDetector(
                      onTap: _submitSearch,
                      child: Container(
                        padding: const EdgeInsets.all(9),
                        decoration: BoxDecoration(
                          color: AppColors.submitButton,
                          borderRadius: BorderRadius.circular(40),
                        ),
                        child: const Icon(
                          Icons.arrow_forward,
                          color: AppColors.background,
                          size: 16,
                        ),
                      ),
                    )
                  ],
                ),
              )
            ],
          ),
        )
      ],
    );
  }
}