package com.example.data_collector

import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
class MainActivity : FlutterActivity() {
    private val channelName = "com.example.data_collector/device_camera"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName).setMethodCallHandler { call, result ->
            when (call.method) {
                "getBackCameraIntrinsics" -> {
                    try {
                        result.success(backCameraIntrinsics())
                    } catch (e: Exception) {
                        result.error("CAMERA", e.message, null)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }

    private fun backCameraIntrinsics(): Map<String, Any?> {
        val cameraManager = getSystemService(Context.CAMERA_SERVICE) as CameraManager
        var backId: String? = null
        for (id in cameraManager.cameraIdList) {
            val chars = cameraManager.getCameraCharacteristics(id)
            val facing = chars.get(CameraCharacteristics.LENS_FACING)
            if (facing == CameraCharacteristics.LENS_FACING_BACK) {
                backId = id
                break
            }
        }
        if (backId == null) {
            return mapOf("error" to "no_back_camera")
        }

        val c = cameraManager.getCameraCharacteristics(backId)
        val focalLengths = c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)
        val sensorSize = c.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)
        val pixelArray = c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE)

        val focalMm: Float? = when {
            focalLengths != null && focalLengths.isNotEmpty() -> focalLengths.minOrNull()
            else -> null
        }

        val sensorWmm = sensorSize?.width ?: 0f
        val sensorHmm = sensorSize?.height ?: 0f
        val pixelW = pixelArray?.width ?: 0
        val pixelH = pixelArray?.height ?: 0

        var fxPixels: Double? = null
        var fyPixels: Double? = null
        if (focalMm != null && focalMm > 0f && sensorWmm > 0f && sensorHmm > 0f && pixelW > 0 && pixelH > 0) {
            // Pinhole model: focal_px = f_mm / sensor_dimension_mm * pixel_dimension
            fxPixels = (focalMm.toDouble() / sensorWmm.toDouble()) * pixelW
            fyPixels = (focalMm.toDouble() / sensorHmm.toDouble()) * pixelH
        }

        val out = mutableMapOf<String, Any?>(
            "camera_id" to backId,
            "lens_facing" to "back",
            "sensor_physical_width_mm" to sensorWmm.toDouble(),
            "sensor_physical_height_mm" to sensorHmm.toDouble(),
            "sensor_pixel_array_width" to pixelW,
            "sensor_pixel_array_height" to pixelH,
            "estimated_fx_px" to fxPixels,
            "estimated_fy_px" to fyPixels,
            "estimated_cx_px" to if (pixelW > 0) pixelW / 2.0 else null,
            "estimated_cy_px" to if (pixelH > 0) pixelH / 2.0 else null,
            "android_api" to Build.VERSION.SDK_INT,
            "source" to "android_camera2",
        )

        if (focalLengths != null && focalLengths.isNotEmpty()) {
            out["focal_lengths_mm"] = focalLengths.map { it.toDouble() }
            out["primary_focal_length_mm"] = focalMm?.toDouble()
        }

        return out
    }
}
