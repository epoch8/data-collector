import 'dart:io';

import 'package:flutter/material.dart';

Widget localCaptureThumbnail(String path, {required double size, BoxFit fit = BoxFit.cover}) {
  if (!File(path).existsSync()) {
    return SizedBox(
      width: size,
      height: size,
      child: ColoredBox(
        color: Colors.black12,
        child: Icon(Icons.broken_image_outlined, size: size * 0.35),
      ),
    );
  }
  return Image.file(File(path), width: size, height: size, fit: fit);
}

Widget localCaptureImageBox(
  String path, {
  double? width,
  double? height,
  BoxFit fit = BoxFit.cover,
}) {
  if (!File(path).existsSync()) {
    return SizedBox(
      width: width,
      height: height ?? 120,
      child: Container(
        color: Colors.black12,
        alignment: Alignment.center,
        child: Icon(Icons.broken_image_outlined, size: (height ?? 120) * 0.2),
      ),
    );
  }
  return Image.file(File(path), width: width, height: height, fit: fit);
}
