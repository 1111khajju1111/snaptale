import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:snaptale/providers/app_state.dart';
import 'package:snaptale/main.dart';

void main() {
  testWidgets('SnapTale home screen renders and shows camera trigger', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppState(),
        child: const SnapTaleApp(),
      ),
    );

    // Verify Title and Subtitle
    expect(find.text('SNAPTALE'), findsWidgets);
    expect(find.text('No humans. Just everything else.'), findsOneWidget);
    expect(find.byIcon(Icons.camera_alt), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Library'), findsOneWidget);
    expect(find.text('Explore'), findsOneWidget);
  });
}