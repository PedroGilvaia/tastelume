import 'package:flutter/material.dart';

import 'app.dart';
import 'core/config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final config = ApiConfig();
  await config.load();
  runApp(TastelumeApp(deps: AppDependencies(config)));
}
