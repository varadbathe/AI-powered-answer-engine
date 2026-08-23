import 'package:ai_answer_engine/pages/home_page.dart';
import 'package:ai_answer_engine/theme/colors.dart';
import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        scaffoldBackgroundColor: AppColors.background, 
            /*
            scaffoldBackgroundColor specifies what scaffold background
             should look like through out the application
            */
      ),
      home: HomePage(),
    );
  }
}
