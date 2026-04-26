import "package:flutter/material.dart";

import "app_state.dart";
import "data/auth_store.dart";
import "data/local_db.dart";
import "data/sync_service.dart";
import "ui/home_page.dart";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final db = await LocalDb.open();
  final state = AppState(auth: AuthStore(), db: db, sync: SyncService(db: db));
  await state.init();
  runApp(App(state: state));
}

class App extends StatelessWidget {
  const App({super.key, required this.state});
  final AppState state;

  @override
  Widget build(BuildContext context) {
    final scheme = ColorScheme.fromSeed(seedColor: const Color(0xFF20D9B4), brightness: Brightness.dark);
    return MaterialApp(
      title: "Todo Sync",
      theme: ThemeData(
        colorScheme: scheme,
        useMaterial3: true,
      ),
      home: HomePage(state: state),
    );
  }
}

