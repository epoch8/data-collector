import AVFoundation
import CoreMedia
import Flutter

/// Registers MethodChannel `com.example.data_collector/device_camera`.
enum DeviceCameraChannel {
  static let name = "com.example.data_collector/device_camera"

  private static let maxFormatSummaries = 60

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
      "metadata_schema_version": 2,
      "device_unique_id": device.uniqueID,
      "device_model_id": device.modelID,
      "localized_name": device.localizedName,
      "device_type": device.deviceType.rawValue,
      "position_raw": device.position.rawValue,
      "has_flash": device.hasFlash,
      "has_torch": device.hasTorch,
      "lens_aperture": device.lensAperture,
      "exposure_mode_raw": device.exposureMode.rawValue,
      "focus_mode_raw": device.focusMode.rawValue,
      "white_balance_mode_raw": device.whiteBalanceMode.rawValue,
      "torch_mode_raw": device.torchMode.rawValue,
      "low_light_boost_enabled": device.isLowLightBoostEnabled,
      "video_zoom_factor": device.videoZoomFactor,
      "runtime_lens_position": device.lensPosition,
      "runtime_exposure_duration_seconds": CMTimeGetSeconds(device.exposureDuration),
      "runtime_iso": device.iso,
      "active_format_summary": summarizeFormat(format),
      "formats_total_count": device.formats.count,
    ]

    if #available(iOS 13.0, *) {
      out["is_virtual_device"] = device.isVirtualDevice
      if device.isVirtualDevice {
        out["constituent_device_unique_ids"] = device.constituentDevices.map { $0.uniqueID }
      }
    }

    if #available(iOS 15.0, *) {
      out["minimum_focus_distance_mm"] = device.minimumFocusDistance
      out["active_primary_constituent_device_unique_id"] = device.activePrimaryConstituentDevice?.uniqueID as Any
      out["active_primary_constituent_device_switching_behavior_raw"] = device.activePrimaryConstituentDeviceSwitchingBehavior.rawValue
    }

    if #available(iOS 16.0, *) {
      out["active_format_secondary_native_resolution_zoom_factor"] = format.secondaryNativeResolutionZoomFactor
    }

    let formats = device.formats
    let slice = formats.prefix(maxFormatSummaries)
    out["formats_summaries"] = slice.map { summarizeFormat($0) }
    out["formats_summaries_truncated"] = formats.count > maxFormatSummaries

    // Diagonal field of view (degrees) — Apple documents as video field of view for the format.
    let fovDeg = Double(format.videoFieldOfView)
    out["video_field_of_view_deg"] = fovDeg

    if fovDeg > 0, w > 0, h > 0 {
      let fovRad = fovDeg * .pi / 180.0
      let diag = (w * w + h * h).squareRoot()
      let halfDiag = diag / 2.0
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

  private static func summarizeFormat(_ f: AVCaptureDevice.Format) -> [String: Any] {
    let desc = f.formatDescription
    let d = CMVideoFormatDescriptionGetDimensions(desc)
    let subtype = CMFormatDescriptionGetMediaSubType(desc)
    var m: [String: Any] = [
      "width": d.width,
      "height": d.height,
      "media_subtype_four_cc": Int(subtype),
      "video_field_of_view_deg": f.videoFieldOfView,
      "video_max_zoom_factor": f.videoMaxZoomFactor,
      "is_video_hdr_supported": f.isVideoHDRSupported,
      "is_video_binned": f.isVideoBinned,
    ]
    let ranges = f.videoSupportedFrameRateRanges.map { r -> [String: Any] in
      ["min_frame_rate": r.minFrameRate, "max_frame_rate": r.maxFrameRate]
    }
    m["video_frame_rate_ranges"] = ranges
    if #available(iOS 13.0, *) {
      m["is_highest_photo_quality_supported"] = f.isHighestPhotoQualitySupported
    }
    if #available(iOS 16.0, *) {
      m["secondary_native_resolution_zoom_factor"] = f.secondaryNativeResolutionZoomFactor
    }
    return m
  }
}
