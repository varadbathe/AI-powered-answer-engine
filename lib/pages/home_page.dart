import 'package:ai_answer_engine/widget/side_bar.dart';
import 'package:flutter/material.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          SideBar(),
          Column(
            children: [
              //search section
              //footer
            ],
          ),
        ],
      ),
    );
  }
}
