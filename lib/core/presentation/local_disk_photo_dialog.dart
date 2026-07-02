import 'local_disk_photo_dialog_io.dart'
    if (dart.library.html) 'local_disk_photo_dialog_web.dart'
    as impl;
import 'package:flutter/material.dart';

Future<void> showLocalDiskPhotoDialog(BuildContext context, String path) =>
    impl.showLocalDiskPhotoDialog(context, path);
