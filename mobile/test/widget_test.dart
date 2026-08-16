import 'package:flutter_test/flutter_test.dart';

import 'package:clipora_mobile/main.dart';

void main() {
  testWidgets('Clipora app builds without exceptions', (WidgetTester tester) async {
    await tester.pumpWidget(const CliporaApp());
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}