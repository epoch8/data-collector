import 'package:flutter/material.dart';

bool _isNetworkLikePreviewPath(String path) {
  final p = path.trim();
  return p.startsWith('blob:') ||
      p.startsWith('http://') ||
      p.startsWith('https://') ||
      p.startsWith('data:');
}

Widget localCaptureThumbnail(String path, {required double size, BoxFit fit = BoxFit.cover}) {
  if (_isNetworkLikePreviewPath(path)) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: Image.network(
        path,
        width: size,
        height: size,
        fit: fit,
        errorBuilder: (_, __, ___) => SizedBox(
          width: size,
          height: size,
          child: ColoredBox(
            color: Colors.black12,
            child: Icon(Icons.broken_image_outlined, size: size * 0.35),
          ),
        ),
      ),
    );
  }
  return SizedBox(
    width: size,
    height: size,
    child: ColoredBox(
      color: Colors.black12,
      child: Icon(Icons.photo_outlined, size: size * 0.35),
    ),
  );
}

Widget localCaptureImageBox(
  String path, {
  double? width,
  double? height,
  BoxFit fit = BoxFit.cover,
}) {
  final h = height ?? 120;
  if (_isNetworkLikePreviewPath(path)) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Image.network(
        path,
        width: width,
        height: h,
        fit: fit,
        errorBuilder: (_, __, ___) => SizedBox(
          width: width,
          height: h,
          child: Container(
            color: Colors.black12,
            alignment: Alignment.center,
            child: Icon(Icons.broken_image_outlined, size: h * 0.2),
          ),
        ),
      ),
    );
  }
  return SizedBox(
    width: width,
    height: h,
    child: Container(
      color: Colors.black12,
      alignment: Alignment.center,
      child: Icon(Icons.photo_outlined, size: h * 0.2),
    ),
  );
}
