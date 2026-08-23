import 'package:ai_answer_engine/theme/colors.dart';
import 'package:flutter/material.dart';

class SideBar extends StatefulWidget {
  const SideBar({super.key});

  @override
  State<SideBar> createState() => _SideBarState();
}

class _SideBarState extends State<SideBar> {
  bool isCollapsed = true;
  @override
  Widget build(BuildContext context) {
    return Container(
      width: isCollapsed ? 64 : 128, // here the logic of width is controlled.
      color: AppColors.sideNav,
      child: Column(
        children: [
          SizedBox(height: 16),
          Icon(
            Icons.auto_awesome_mosaic,
            color: AppColors.whiteColor,
            size: 30,
          ),
          Container(
            margin: EdgeInsets.symmetric(vertical: 14),
            child: Icon(Icons.add, color: AppColors.iconGrey, size: 22),
          ),
          Container(
            margin: EdgeInsets.symmetric(vertical: 14),
            child: Icon(Icons.search, color: AppColors.iconGrey, size: 22),
          ),
          Container(
            margin: EdgeInsets.symmetric(vertical: 14),
            child: Icon(Icons.language, color: AppColors.iconGrey, size: 22),
          ),
          Container(
            margin: EdgeInsets.symmetric(vertical: 14),
            child: Icon(
              Icons.cloud_outlined,
              color: AppColors.iconGrey,
              size: 22,
            ),
          ),
          Spacer(),
          GestureDetector(
            onTap: () {
              setState(() {
                isCollapsed = !isCollapsed; // toggles the logic
              });
            },
            child: Container(
              margin: EdgeInsets.symmetric(vertical: 14),
              child: Icon(
                Icons.keyboard_arrow_right,
                color: AppColors.iconGrey,
                size: 22,
              ),
            ),
          ),
          SizedBox(height: 20),
        ],
      ),
    );
  }
}
