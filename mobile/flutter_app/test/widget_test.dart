import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:snaptale/providers/app_state.dart';
import 'package:snaptale/main.dart';

void main() {
  testWidgets('Unauthenticated user sees the login screen, not Home',
      (WidgetTester tester) async {
    // No persisted auth_token -> AuthGate must show LoginScreen.
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppState(),
        child: const SnapTaleApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('SNAPTALE'), findsWidgets);
    expect(find.text('Log in to continue'), findsOneWidget);
    expect(find.text('Home'), findsNothing);
    expect(find.byIcon(Icons.camera_alt), findsNothing);
  });

  testWidgets('Authenticated user (persisted token) reaches the home screen',
      (WidgetTester tester) async {
    // A previously-persisted session should skip the login screen entirely.
    SharedPreferences.setMockInitialValues({'auth_token': 'test-token-e2e-user'});

    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppState(),
        child: const SnapTaleApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('SNAPTALE'), findsWidgets);
    expect(find.text('No humans. Just everything else.'), findsOneWidget);
    expect(find.byIcon(Icons.camera_alt), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Library'), findsOneWidget);
    expect(find.text('Explore'), findsOneWidget);
  });
}