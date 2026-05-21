import 'package:data_collector/main.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('app builds', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: DataCollectorApp()));
    await tester.pump();
    expect(find.byType(DataCollectorApp), findsOneWidget);
  });
}
