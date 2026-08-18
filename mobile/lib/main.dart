import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'widgets/ui.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const CliporaApp());
}

class CliporaApp extends StatelessWidget {
  const CliporaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Clipora',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: kBg,
        colorScheme: ColorScheme.fromSeed(
          seedColor: kAccent,
          brightness: Brightness.dark,
          surface: kSurface,
        ),
        appBarTheme: const AppBarTheme(backgroundColor: kBg),
      ),
      home: const HomeScreen(),
    );
  }
}