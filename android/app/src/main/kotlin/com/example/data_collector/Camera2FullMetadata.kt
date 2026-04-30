package com.example.data_collector

import android.graphics.Point
import android.graphics.PointF
import android.graphics.Rect
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.params.RecommendedStreamConfigurationMap
import android.hardware.camera2.params.StreamConfigurationMap
import android.os.Build
import android.util.Log
import android.util.Rational
import android.util.Size
import android.util.SizeF
import kotlin.math.min

/**
 * Serializes [CameraCharacteristics] into JSON-friendly maps/lists for the package payload.
 * Uses [CameraCharacteristics.getKeys] on API 28+; on older APIs collects a fixed subset.
 */
object Camera2FullMetadata {

    private const val TAG = "Camera2FullMetadata"
    private const val MAX_STREAM_CONFIG_SAMPLES = 64

    fun collectAll(c: CameraCharacteristics): Map<String, Any?> {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            collectViaKeys(c)
        } else {
            collectLegacySubset(c)
        }
    }

    private fun collectViaKeys(c: CameraCharacteristics): Map<String, Any?> {
        val out = linkedMapOf<String, Any?>()
        for (key in c.keys) {
            val name = key.name
            try {
                val v = c.get(key)
                out[name] = serializeValue(v)
            } catch (e: Exception) {
                Log.w(TAG, "get($name): ${e.message}")
                out[name] = mapOf("_read_error" to (e.message ?: e.javaClass.simpleName))
            }
        }
        return out
    }

    @Suppress("DEPRECATION")
    private fun collectLegacySubset(c: CameraCharacteristics): Map<String, Any?> {
        val out = linkedMapOf<String, Any?>()
        fun putRect(key: String, r: Rect?) {
            if (r != null) out[key] = serializeRect(r)
        }
        fun putSize(key: String, s: Size?) {
            if (s != null) out[key] = serializeSize(s)
        }
        fun putFloatArr(key: String, a: FloatArray?) {
            if (a != null) out[key] = a.map { it.toDouble() }
        }
        try {
            c.get(CameraCharacteristics.LENS_FACING)?.let {
                out["android.lens.facing"] = it
            }
            putFloatArr("android.lens.info.availableFocalLengths", c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS))
            putFloatArr("android.lens.info.availableApertures", c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_APERTURES))
            c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)?.let {
                out["android.lens.info.availableOpticalStabilization"] = it.toList()
            }
            c.get(CameraCharacteristics.LENS_INFO_FOCUS_DISTANCE_CALIBRATION)?.let {
                out["android.lens.info.focusDistanceCalibration"] = it
            }
            c.get(CameraCharacteristics.LENS_INFO_HYPERFOCAL_DISTANCE)?.let {
                out["android.lens.info.hyperfocalDistance"] = it.toDouble()
            }
            c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE)?.let {
                out["android.lens.info.minimumFocusDistance"] = it.toDouble()
            }
            putFloatArr("android.lens.intrinsicCalibration", c.get(CameraCharacteristics.LENS_INTRINSIC_CALIBRATION))
            putFloatArr("android.lens.poseRotation", c.get(CameraCharacteristics.LENS_POSE_ROTATION))
            putFloatArr("android.lens.poseTranslation", c.get(CameraCharacteristics.LENS_POSE_TRANSLATION))
            putSize("android.sensor.info.pixelArraySize", c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE))
            c.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)?.let { sf ->
                out["android.sensor.info.physicalSize"] = mapOf("width" to sf.width.toDouble(), "height" to sf.height.toDouble())
            }
            putRect("android.sensor.info.activeArraySize", c.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE))
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                putRect("android.sensor.info.preCorrectionActiveArraySize", c.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE))
            }
            c.get(CameraCharacteristics.SENSOR_ORIENTATION)?.let {
                out["android.sensor.orientation"] = it
            }
            c.get(CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE)?.let {
                out["android.sensor.info.timestampSource"] = it
            }
            c.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT)?.let {
                out["android.sensor.info.colorFilterArrangement"] = it
            }
            c.get(CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED)?.let {
                out["android.sensor.info.lensShadingApplied"] = it
            }
            c.get(CameraCharacteristics.FLASH_INFO_AVAILABLE)?.let {
                out["android.flash.info.available"] = it
            }
            c.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)?.let {
                out["android.info.supportedHardwareLevel"] = it
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)?.let { caps ->
                    out["android.request.availableCapabilities"] = caps.toList()
                }
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                putFloatArr("android.lens.distortion", c.get(CameraCharacteristics.LENS_DISTORTION))
            }
        } catch (e: Exception) {
            out["_legacy_subset_error"] = e.message ?: e.javaClass.simpleName
        }
        return out
    }

    private fun serializeValue(value: Any?): Any? {
        if (value == null) return null
        return when (value) {
            is String, is Boolean -> value
            is Int, is Long, is Short, is Byte -> value
            is Float -> value.toDouble()
            is Double -> value
            is Size -> serializeSize(value)
            is SizeF -> mapOf("width" to value.width.toDouble(), "height" to value.height.toDouble())
            is Rect -> serializeRect(value)
            is Rational -> mapOf("numerator" to value.numerator, "denominator" to value.denominator)
            is Point -> mapOf("x" to value.x, "y" to value.y)
            is PointF -> mapOf("x" to value.x.toDouble(), "y" to value.y.toDouble())
            is IntArray -> value.toList()
            is LongArray -> value.toList()
            is FloatArray -> value.map { it.toDouble() }
            is DoubleArray -> value.toList()
            is ByteArray -> value.map { it.toInt() and 0xff }
            is BooleanArray -> value.toList()
            is StreamConfigurationMap -> serializeStreamConfigurationMap(value)
            is RecommendedStreamConfigurationMap -> mapOf(
                "_type" to "RecommendedStreamConfigurationMap",
                "toString" to value.toString(),
            )
            is Array<*> -> value.map { serializeValue(it) }
            is List<*> -> value.map { serializeValue(it) }
            else -> mapOf(
                "_unhandled_type" to value.javaClass.name,
                "string_fallback" to value.toString(),
            )
        }
    }

    private fun serializeSize(s: Size) = mapOf("width" to s.width, "height" to s.height)

    private fun serializeRect(r: Rect) = mapOf(
        "left" to r.left,
        "top" to r.top,
        "right" to r.right,
        "bottom" to r.bottom,
        "width" to r.width(),
        "height" to r.height(),
    )

    private fun serializeStreamConfigurationMap(map: StreamConfigurationMap): Map<String, Any?> {
        val formats = try {
            map.outputFormats
        } catch (e: Exception) {
            return mapOf("_error" to (e.message ?: "outputFormats"))
        }
        val perFormat = formats.map { fmt ->
            val sizes = try {
                map.getOutputSizes(fmt) ?: emptyArray()
            } catch (e: Exception) {
                emptyArray()
            }
            val n = sizes.size
            val take = min(n, MAX_STREAM_CONFIG_SAMPLES)
            mapOf(
                "format" to fmt,
                "total_size_variants" to n,
                "sizes_sample" to sizes.take(take).map { serializeSize(it) },
                "sizes_truncated" to (n > take),
            )
        }
        return mapOf(
            "_type" to "StreamConfigurationMap",
            "output_formats" to formats.toList(),
            "by_format" to perFormat,
        )
    }
}
