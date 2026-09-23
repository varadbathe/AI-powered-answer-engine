import 'package:research_os/theme/colors.dart';
import 'package:flutter/material.dart';


class SearchBarButton extends StatefulWidget {
  final IconData icon;
  final String text;
  final VoidCallback? onTap;

  const SearchBarButton({
    super.key,
    required this.icon,
    required this.text,
    this.onTap,
  });

  @override
  State<SearchBarButton> createState() => _SearchBarButtonState();
}

class _SearchBarButtonState extends State<SearchBarButton> {
  bool isHovered = false;
  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (event) {
        setState(() {
          isHovered = true;
        });
      },
      onExit: (event) {
        setState(() {
          isHovered = false;
        });
      },
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: 8,
            vertical: 4,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(6),
            color: isHovered ? AppColors.proButton : Colors.transparent,
          ),
          child: Row(
            children: [
              Icon(
                widget.icon,
                color: AppColors.iconGrey,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                widget.text,
                style: const TextStyle(
                  color: AppColors.textGrey,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}