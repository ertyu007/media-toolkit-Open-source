import 'package:flutter/material.dart';

const kBg = Color(0xFF090D15);
const kSurface = Color(0xFF111827);
const kSurface2 = Color(0xFF0D1520);
const kAccent = Color(0xFF4D9DE0);
const kDanger = Color(0xFFB3261E);
const kSuccess = Color(0xFF2E7D32);

Widget cliporaCard(Widget child) {
  return Container(
    margin: const EdgeInsets.only(top: 12),
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: kSurface,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: Colors.white10),
    ),
    child: child,
  );
}

Widget fieldLabel(String text) {
  return Padding(
    padding: const EdgeInsets.only(top: 14, bottom: 6),
    child: Text(text,
        style: const TextStyle(color: Colors.white54, fontSize: 12)),
  );
}

Widget segButton(String label, bool active, VoidCallback onTap) {
  return GestureDetector(
    onTap: onTap,
    child: AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        color: active ? const Color(0xFF1D2A3A) : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: active ? kAccent : Colors.white12,
        ),
      ),
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontWeight: FontWeight.w600,
          color: active ? Colors.white : Colors.white54,
        ),
      ),
    ),
  );
}

Widget miniButton(String label, bool active, VoidCallback onTap) {
  return GestureDetector(
    onTap: onTap,
    child: AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: active ? const Color(0xFF16202E) : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
            color: active ? kAccent : Colors.white12),
      ),
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: active ? Colors.white : Colors.white54,
        ),
      ),
    ),
  );
}

Widget cliporaDropdown<T>(T value, List<T> items, ValueChanged<T> onChanged) {
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 12),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: Colors.white12),
    ),
    child: DropdownButtonHideUnderline(
      child: DropdownButton<T>(
        value: value,
        isExpanded: true,
        dropdownColor: kSurface,
        items: items
            .map((item) => DropdownMenuItem(value: item, child: Text('$item')))
            .toList(),
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
      ),
    ),
  );
}

Widget checkRow({
  required bool value,
  required String label,
  required ValueChanged<bool?> onChanged,
}) {
  return Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Checkbox(value: value, onChanged: onChanged),
      Expanded(
        child: Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Text(
            label,
            style: const TextStyle(fontSize: 13, color: Colors.white70),
          ),
        ),
      ),
    ],
  );
}

Widget primaryButton({
  required Icon icon,
  required Widget label,
  VoidCallback? onPressed,
}) {
  return FilledButton.icon(
    style: FilledButton.styleFrom(
      padding: const EdgeInsets.symmetric(vertical: 14),
      backgroundColor: kAccent,
    ),
    onPressed: onPressed,
    icon: icon,
    label: label,
  );
}

void showToast(BuildContext context, String message, {bool bad = false}) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(message),
      backgroundColor: bad ? kDanger : null,
    ),
  );
}

String formatBytes(int bytes) {
  if (bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  var value = bytes.toDouble();
  var unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return unit == 0 ? '$bytes B' : '${value.toStringAsFixed(1)} ${units[unit]}';
}

String formatEta(int seconds) {
  if (seconds <= 0) return '';
  final m = (seconds ~/ 60).toString().padLeft(2, '0');
  final s = (seconds % 60).toString().padLeft(2, '0');
  return 'เหลือประมาณ $m:$s';
}