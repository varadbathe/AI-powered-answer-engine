import 'package:ai_answer_engine/pages/home_page.dart';
import 'package:ai_answer_engine/theme/colors.dart';
import 'package:ai_answer_engine/utils/app_logger.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:skeletonizer/skeletonizer.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  AppLogger.info('AI Answer Engine frontend starting...', tag: 'App');
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AI Answer Engine',
      theme: ThemeData(
        scaffoldBackgroundColor: AppColors.background,
        textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme),
        extensions: const [
          SkeletonizerConfigData.dark(
            effect: PulseEffect(
              from: AppColors.cardColor,
              to: Color(0xFF2E3235),
              duration: Duration(milliseconds: 1400),
            ),
          ),
        ],
      ),
      home: const HomePage(),
    );
  }
}
