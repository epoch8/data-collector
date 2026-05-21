import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Native back-camera characteristics (Android Camera2 / iOS AVFoundation).
class DeviceCameraChannel {
  DeviceCameraChannel._();

  static const MethodChannel _channel = MethodChannel('com.example.data_collector/device_camera');

  /// Returns serializable map; empty on web / unsupported / error.
  static Future<Map<String, dynamic>> getBackCameraIntrinsics() async {
    if (kIsWeb) {
      return {};
    }
    if (defaultTargetPlatform != TargetPlatform.android && defaultTargetPlatform != TargetPlatform.iOS) {
      return {};
    }
    try {
      final raw = await _channel.invokeMethod<dynamic>('getBackCameraIntrinsics');
      if (raw is Map) {
        return raw.map((k, v) => MapEntry(k.toString(), _normalize(v)));
      }
      return {};
    } on PlatformException catch (_) {
      return {};
    }
  }

  static dynamic _normalize(dynamic v) {
    if (v is Map) {
      return v.map((k, val) => MapEntry(k.toString(), _normalize(val)));
    }
    if (v is List) {
      return v.map(_normalize).toList();
    }
    return v;
  }
}
