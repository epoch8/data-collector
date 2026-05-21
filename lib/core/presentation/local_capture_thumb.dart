import 'local_capture_thumb_io.dart' if (dart.library.html) 'local_capture_thumb_web.dart' as impl;
import 'package:flutter/material.dart';

Widget localCaptureThumbnail(String path, {required double size, BoxFit fit = BoxFit.cover}) =>
    impl.localCaptureThumbnail(path, size: size, fit: fit);

Widget localCaptureImageBox(
  String path, {
  double? width,
  double? height,
  BoxFit fit = BoxFit.cover,
}) =>
    impl.localCaptureImageBox(path, width: width, height: height, fit: fit);
