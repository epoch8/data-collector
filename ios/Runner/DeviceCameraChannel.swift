import AVFoundation
import CoreMedia
import Flutter

/// Registers MethodChannel `com.example.data_collector/device_camera`.
enum DeviceCameraChannel {
  static let name = "com.example.data_collector/device_camera"

  static func register(with registry: FlutterPluginRegistry) {
    guard let registrar = registry.registrar(forPlugin: "device_camera_intrinsics") else { return }
    let channel = FlutterMethodChannel(name: name, binaryMessenger: registrar.messenger())
    channel.setMethodCallHandler { call, result in
      switch call.method {
      case "getBackCameraIntrinsics":
        result(backIntrinsics())
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }

  private static func backIntrinsics() -> [String: Any] {
    guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
      return ["error": "no_back_camera"]
    }

    let format = device.activeFormat
    let desc = format.formatDescription
    let dim = CMVideoFormatDescriptionGetDimensions(desc)
    let w = Double(dim.width)
    let h = Double(dim.height)

    var out: [String: Any] = [
      "lens_facing": "back",
      "active_pixel_array_width": dim.width,
      "active_pixel_array_height": dim.height,
      "source": "avfoundation",
    ]

    // Diagonal field of view (degrees) — Apple documents as video field of view for the format.
    let fovDeg = Double(format.videoFieldOfView)
    out["video_field_of_view_deg"] = fovDeg

    if fovDeg > 0, w > 0, h > 0 {
      let fovRad = fovDeg * .pi / 180.0
      let diag = (w * w + h * h).squareRoot()
      let halfDiag = diag / 2.0
      // Assume FOV is diagonal: tan(fov/2) = (diag/2) / f_px  =>  f_px = (diag/2) / tan(fov/2)
      let fFromDiag = halfDiag / tan(fovRad / 2.0)
      out["estimated_f_px_from_diagonal_fov"] = fFromDiag
      out["estimated_fx_px"] = fFromDiag
      out["estimated_fy_px"] = fFromDiag
      out["estimated_cx_px"] = w / 2.0
      out["estimated_cy_px"] = h / 2.0
      out["fov_model_note"] = "diagonal_fov_assumed_square_pixels"
    }

    return out
  }
}
