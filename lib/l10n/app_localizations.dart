import 'package:flutter/material.dart';

class AppLocalizations {
  AppLocalizations(this.locale);

  final Locale locale;

  static const supportedLocales = <Locale>[
    Locale('ru'),
    Locale('en'),
  ];

  static AppLocalizations of(BuildContext context) {
    final loc = Localizations.of<AppLocalizations>(context, AppLocalizations);
    assert(loc != null, 'AppLocalizations not found in context');
    return loc!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate = _Delegate();

  bool get _isRu => locale.languageCode.toLowerCase().startsWith('ru');

  String get appTitle => _isRu ? 'EPOCH8 Сборщик данных' : 'EPOCH8 Data Collector';
  String get languageCodeLabel => _isRu ? 'RU' : 'EN';
  String get languageToggleTooltip => _isRu ? 'Switch to English' : 'Переключить на русский';
  String get loginTitle => 'Data Collector';
  String get loginSubtitle => _isRu
      ? 'Сбор полевых данных и фото с офлайн-историей на устройстве'
      : 'Collect field data and photos with offline history on device';
  String get email => 'Email';
  String get password => _isRu ? 'Пароль' : 'Password';
  String get signIn => _isRu ? 'Войти' : 'Sign in';
  String get workspaceTitle => _isRu ? 'Рабочее пространство' : 'Workspace';
  String get projectsTab => _isRu ? 'Проекты' : 'Projects';
  String get serverTab => _isRu ? 'Сервер' : 'Server';
  String get historyTab => _isRu ? 'История' : 'History';
  String get logout => _isRu ? 'Выйти' : 'Sign out';
  String get projectNotFound => _isRu
      ? 'Проект не найден в конфигурации.'
      : 'Project not found in configuration.';
  String get project => _isRu ? 'Проект' : 'Project';
  String get errorPrefix => _isRu ? 'Ошибка' : 'Error';
  String get packageNotFoundTitle => _isRu ? 'Пакет не найден' : 'Package not found';
  String get packageNotFoundSubtitle => _isRu
      ? 'Возможно, он был удалён или база обновилась.'
      : 'It may have been deleted or the database has been updated.';
  String get packageNoPhotosTitle => _isRu ? 'В пакете нет фото' : 'No photos in package';
  String get packageNoPhotosSubtitle => _isRu
      ? 'Сохранены только поля формы.'
      : 'Only form fields were saved.';
  String get formDataTitle => _isRu ? 'Данные анкеты' : 'Form data';
  String get openPhoto => _isRu ? 'Открыть' : 'Open';
  String get fileNotFoundOnDevice => _isRu ? 'Файл не найден на устройстве' : 'File not found on device';
  String get frameCameraParams => _isRu ? 'Параметры кадра и камеры' : 'Frame and camera parameters';
  String get downloadManifestAsServer => _isRu
      ? 'Скачать JSON манифеста (как на сервер)'
      : 'Download manifest JSON (server format)';
  String get packageNotFoundShort => _isRu ? 'Пакеты не найдены' : 'Packages not found';
  String get noPackagesForCow => _isRu
      ? 'Для этой коровы пока нет сохранённых пакетов.'
      : 'There are no saved packages for this cow yet.';
  String get historyEmptyTitle => _isRu ? 'История пуста' : 'History is empty';
  String get historyEmptySubtitle => _isRu
      ? 'Отправленные пакеты появятся здесь.'
      : 'Sent packages will appear here.';
  String get noProjectsTitle => _isRu ? 'Пока нет проектов' : 'No projects yet';
  String get clearUploadedCache => _isRu ? 'Очистить кэш загруженных' : 'Clear uploaded cache';
  String clearUploadedCacheWithCount(int n) => _isRu
      ? 'Очистить кэш загруженных ($n)'
      : 'Clear uploaded cache ($n)';
  String get packageWordShort => _isRu ? 'пак.' : 'pkg.';
  String packageCountShort(int n) => '$n ${packageWordShort}';
  String get allPackagesOnServer => _isRu ? 'Все пакеты на сервере' : 'All packages are on server';
  String get uploadFailed => _isRu ? 'Ошибка отправки' : 'Upload failed';
  String get notOnServer => _isRu ? 'Не на сервере' : 'Not on server';
  String get photos => _isRu ? 'Фото' : 'Photos';
  String get version => _isRu ? 'Версия' : 'Version';
  String get formLabel => _isRu ? 'анкета' : 'form';
  String get guideLabel => _isRu ? 'справка' : 'guide';
  String cameraPosesCount(int n) => _isRu ? '$n ракурса' : '$n poses';
  String get reviewLabel => _isRu ? 'проверка' : 'review';
  String get createdAt => _isRu ? 'Создан' : 'Created';
  String get identifier => _isRu ? 'Идентификатор' : 'Identifier';
  String get objectLabel => _isRu ? 'Объект' : 'Object';
  String get packageWord => _isRu ? 'Пакет' : 'Package';
  String get fileWord => _isRu ? 'файл(ов)' : 'file(s)';
  String get close => _isRu ? 'Закрыть' : 'Close';
  String get fileNotFound => _isRu ? 'Файл не найден' : 'File not found';
  String get pathLabel => _isRu ? 'Путь' : 'Path';
  String projectLabel(String value) => _isRu ? 'Проект: $value' : 'Project: $value';
  String get firebaseNotInitialized => _isRu
      ? 'Firebase не инициализирован: проверьте lib/firebase_options.dart и google-services.json (Android). Для разработки без входа:'
      : 'Firebase is not initialized: check lib/firebase_options.dart and google-services.json (Android). For development without sign-in:';
  String get goToWorkspace => _isRu ? 'Перейти в рабочее пространство' : 'Go to workspace';
  String get configError => _isRu ? 'Ошибка конфига' : 'Config error';
  String get serverEmptySubtitleConfigured => _isRu
      ? 'С сервера пока нечего показать: нет доступных проектов или нет сети (показан кэш/bundled). Потяните вниз для обновления.'
      : 'Nothing to show from server yet: no available projects or no network (cached/bundled data shown). Pull to refresh.';
  String get serverEmptySubtitleNotConfigured => _isRu
      ? 'Задайте API_BASE_URL при запуске, чтобы подтянуть проекты с Django, или добавьте проекты в assets/config/projects.json.'
      : 'Set API_BASE_URL at startup to fetch projects from Django, or add projects to assets/config/projects.json.';
  String get downloadManifest => _isRu ? 'Скачать JSON манифеста' : 'Download manifest JSON';
  String get deleteFromDevice => _isRu ? 'Удалить с устройства' : 'Delete from device';
  String get photosLower => _isRu ? 'фото' : 'photos';
  String get noId => _isRu ? 'без-id' : 'no-id';
  String get projectMissingInConfig => _isRu ? 'нет в конфиге' : 'missing in config';
  String get addProjectToAssets => _isRu
      ? 'Добавьте проект в assets/config/projects.json'
      : 'Add project to assets/config/projects.json';
  String get loadingConfigError => _isRu ? 'Ошибка загрузки конфига' : 'Config loading error';
  String get projectNotFoundShort => _isRu ? 'Проект не найден' : 'Project not found';
  String get projectNotFoundShortDot => _isRu ? 'Проект не найден.' : 'Project not found.';
  String get unsupportedFieldType => _isRu
      ? 'Тип поля не поддерживается на этом экране.'
      : 'Field type is not supported on this screen.';
  String get supportedFieldTypes => _isRu
      ? 'Допустимо: text_input, camera_photo.'
      : 'Supported: text_input, camera_photo.';
  String get submitPackage => _isRu ? 'Отправить пакет' : 'Submit package';
  String get capturePhoto => _isRu ? 'Сделать фото' : 'Capture photo';
  String get takeAnotherPhoto => _isRu ? 'Сделать еще фото' : 'Take another photo';
  String get photosCaptured => _isRu ? 'снимков' : 'photos captured';
  String get photoSaved => _isRu ? 'Фото сохранено' : 'Photo saved';
  String get finishFocus => _isRu ? 'Завершить' : 'Finish';
  String get saveAndNext => _isRu ? 'Сохранить и дальше' : 'Save & next';
  String get projectsUpdated => _isRu ? 'Проекты обновлены с сервера' : 'Projects synced from server';
  String get syncError => _isRu ? 'Ошибка синхронизации' : 'Sync error';
  String packageSent(String id) => _isRu ? 'Пакет $id отправлен' : 'Package $id sent';
  String get serverSetupHint => _isRu
      ? 'Чтобы ходить на Django с эмулятора, запустите приложение с:\n\nflutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000\n\n(порт как у runserver). Войдите в приложении через Firebase.\nЕсли на сервере не включён Firebase Auth, можно добавить:\n--dart-define=API_BEARER_TOKEN=...'
      : 'To access Django from an emulator, run the app with:\n\nflutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000\n\n(use your runserver port). Sign in via Firebase.\nIf Firebase Auth is not enabled on server, you can also add:\n--dart-define=API_BEARER_TOKEN=...';
  String baseUrlLabel(String url) => _isRu ? 'База: $url' : 'Base: $url';
  String get syncingConfigs => _isRu ? 'Качаем конфиги…' : 'Syncing configs...';
  String get syncProjects => _isRu ? 'Синхронизировать проекты' : 'Sync projects';
  String get serverQueue => _isRu ? 'Очередь на сервер' : 'Server queue';
  String get noQueuePackages => _isRu ? 'Нет пакетов в очереди' : 'No packages in queue';
  String get noQueuePackagesSubtitle => _isRu
      ? 'Все сохранённые пакеты уже на сервере или нет локальных данных.'
      : 'All saved packages are already on server, or there is no local data.';
  String serverStateLabel(String state) => _isRu ? 'Сервер: $state' : 'Server: $state';
  String get send => _isRu ? 'Отправить' : 'Send';
  String get dbError => _isRu ? 'Ошибка БД' : 'DB error';
  String get confirmDeletePackageTitle => _isRu ? 'Удалить пакет?' : 'Delete package?';
  String confirmDeletePackageBody(String id) => _isRu
      ? 'Пакет $id будет удалён с устройства (данные и фото в локальном кэше). На сервере копия не удаляется.'
      : 'Package $id will be deleted from this device (local data and photos). Server copy will not be deleted.';
  String get cancel => _isRu ? 'Отмена' : 'Cancel';
  String get delete => _isRu ? 'Удалить' : 'Delete';
  String deletedFromDevice(String id) => _isRu ? 'Пакет $id удалён с устройства' : 'Package $id deleted from device';
  String get clearUploadedCacheConfirmTitle => _isRu ? 'Очистить кэш загруженных?' : 'Clear uploaded cache?';
  String get clearUploadedCacheConfirmBody => _isRu
      ? 'Будут удалены только пакеты со статусом «загружен на сервер»: записи в истории и локальные файлы. Пакеты, которые ещё не отправлены, останутся.'
      : 'Only packages with state "uploaded to server" will be removed: history records and local files. Not-yet-sent packages will stay.';
  String get clear => _isRu ? 'Очистить' : 'Clear';
  String clearedPackagesCount(int n) => _isRu ? 'Удалено пакетов с устройства: $n' : 'Packages removed from device: $n';
  String get nothingToDelete => _isRu ? 'Нечего удалять' : 'Nothing to delete';
  String get webExportNotSupported => _isRu ? 'Экспорт JSON на веб пока не поддерживается.' : 'JSON export on web is not supported yet.';
  String manifestSubject(String id) => _isRu ? 'Манифест $id' : 'Manifest $id';
  String get manifestShareText => _isRu ? 'JSON манифеста пакета (как на сервер)' : 'Package manifest JSON (server format)';
  String exportJsonFailed(String e) => _isRu ? 'Не удалось экспортировать JSON: $e' : 'Failed to export JSON: $e';
  String get packageSavedLocal => _isRu ? 'Пакет сохранен локально' : 'Package saved locally';
  String get cannotUploadDraft => _isRu
      ? 'Нельзя отправить незавершённый черновик — завершите сбор на устройстве.'
      : 'Cannot upload unfinished draft — complete collection on device first.';
  String get noProjectAccess => _isRu
      ? 'Нет доступа к этому проекту у текущего пользователя (проверьте каталог на сервере).'
      : 'No access to this project for current user (check server catalog).';

  // --- Collection flow: app-controlled chrome (not from project JSON) ---
  String get flowDraftDialogTitle => _isRu ? 'Незавершённый сбор' : 'Unfinished collection';
  String get flowDraftDialogBody => _isRu
      ? 'Найден сохранённый прогресс по этому проекту. Продолжить с того же места или начать новый пакет?'
      : 'Saved progress was found for this project. Continue from the same place or start a new package?';
  String get flowDraftStartFresh => _isRu ? 'Начать заново' : 'Start over';
  String get flowDraftContinue => _isRu ? 'Продолжить' : 'Continue';
  String get flowNext => _isRu ? 'Далее' : 'Next';
  String get flowToReview => _isRu ? 'К проверке' : 'To review';
  String get flowRibbonReview => _isRu ? 'Проверка и отправка' : 'Review and submit';
  String get flowRibbonScrollForm => _isRu ? 'Шаг сбора' : 'Collection step';
  String flowScrollCounter(int cur, int total) =>
      _isRu ? '$cur из $total' : '$cur of $total';
  String flowReviewScrollBlockTitle(int n, String formTitle) =>
      _isRu ? 'Шаг $n: $formTitle' : 'Step $n: $formTitle';
  String flowReviewScrollBlockStepOnly(int n) => _isRu ? 'Шаг $n' : 'Step $n';
  String get flowReviewEdit => _isRu ? 'Изменить' : 'Edit';
  String get flowReviewInstructionOnlyHint => _isRu
      ? 'На этом шаге только инструкция (Markdown) — нечего проверять в полях.'
      : 'This step contains instructions only (Markdown) — no fields to review.';
  String get flowReviewNoFrames => _isRu ? 'Нет кадров' : 'No frames';
  String get flowReviewHeaderOverline => _isRu ? 'Завершение' : 'Finish';
  String get flowReviewHeaderTitle => _isRu ? 'Проверка и отправка' : 'Review and submit';
  String get flowReviewHeaderSubtitle => _isRu
      ? 'Проверьте данные. Можно вернуться к любому шагу — введённые значения и фото сохраняются.'
      : 'Check the data. You can go back to any step — entered values and photos are preserved.';
  String get flowReviewSubmit => _isRu ? 'Отправить данные' : 'Submit data';
  String get flowReviewEmptyValue => '—';
  String flowCameraMetaFxEstimate(String value) => 'fₓ≈$value px';
  String get flowCameraMetaTapToExpand => _isRu ? 'Нажмите, чтобы развернуть' : 'Tap to expand';
  String get flowCameraMetaEmptyNotice => _isRu
      ? 'Метаданные камеры появятся после съёмки ракурсов.'
      : 'Camera metadata will appear after capture poses are taken.';
  String get flowCameraMetaTileTitle => _isRu ? 'Метаданные камеры' : 'Camera metadata';
  String get flowCameraMetaSectionDevice => _isRu ? 'Устройство' : 'Device';
  String get flowCameraMetaSectionNative => _isRu ? 'Нативная камера (задняя)' : 'Native camera (rear)';
  String get flowCameraMetaJsonSection => _isRu ? 'Полный JSON (копировать)' : 'Full JSON (copy)';
  String get flowCameraMetaNativeEmpty => _isRu ? 'Нет данных нативного API' : 'No data from native API';
  String flowCameraMetaPoseShotTitle(int idx, int shot) => _isRu
      ? 'Ракурс $idx — кадр $shot'
      : 'Pose $idx — frame $shot';
  String flowCameraMetaPoseDerivedTitle(int idx) =>
      _isRu ? 'Ракурс $idx — оценки' : 'Pose $idx — estimates';
  String get flowCameraMetaFrameCameraHeading => _isRu ? 'Кадр (основной)' : 'Frame (primary)';
  String get flowCameraMetaDerivedHeading =>
      _isRu ? 'Доп. оценки фокусного (дополнение)' : 'Additional focal estimates (supplement)';
  String get flowCameraMetaLabelFxExif => _isRu ? 'fx_px (EXIF × сенсор)' : 'fx_px (EXIF focal × sensor)';
  String get flowCameraMetaLabelFx35mm => _isRu ? 'fx_px (экв. 35 мм)' : 'fx_px (35mm equiv)';
  String get flowCameraMetaLabelFxNative => _isRu ? 'fx_px (нативно)' : 'fx_px (native)';
  String get flowCameraMetaExifHeading => _isRu ? 'Фрагмент EXIF' : 'EXIF fragment';
  String flowCameraMetaExifMore(int n) =>
      _isRu ? '… ещё $n полей' : '… $n more fields';
  String flowCameraMetaNativeMapSummary(int keyCount) => _isRu
      ? '{$keyCount ключей} — см. полный JSON ниже'
      : '{$keyCount keys} — see full JSON below';

  String get flowFormCowHintExact => _isRu ? 'ID есть в локальной истории' : 'ID found in local history';
  String get flowFormCowHintSimilar => _isRu ? 'В истории есть похожие ID' : 'There are similar IDs in history';
  String get flowFormCowHintNew => _isRu ? 'Новый ID (нет в истории)' : 'New ID (not found in history)';
  String get flowFormPrefillButton =>
      _isRu ? 'Подставить поля из последней записи' : 'Prefill fields from latest record';
  String get flowFormDatetimeChange => _isRu ? 'Изменить' : 'Change';
  String get flowFormInstructionEmpty =>
      _isRu ? 'Нет текста инструкции для этого блока.' : 'No instruction text for this block.';
  String get flowCameraPoseExampleAssetMissing =>
      _isRu ? 'Не удалось загрузить пример' : 'Could not load example image';
  String get flowCameraPoseQualityTitle => _isRu ? 'Проверка качества кадра' : 'Frame quality check';
  String get flowCameraPoseUseAnyway => _isRu ? 'Всё равно использовать' : 'Use anyway';
  String get flowCameraPoseRetake => _isRu ? 'Переснять' : 'Retake';
  String flowCameraPoseYourShots(int count) =>
      _isRu ? 'Ваши кадры ($count)' : 'Your frames ($count)';
  String get flowCameraPoseEmptyHint =>
      _isRu ? 'Добавьте кадры с камеры или из галереи' : 'Add frames from camera or gallery';
  String get flowCameraPoseCamera => _isRu ? 'Камера' : 'Camera';
  String get flowCameraPoseGallery => _isRu ? 'Галерея' : 'Gallery';
  String get flowCameraPoseClearAll =>
      _isRu ? 'Удалить все кадры этого ракурса' : 'Delete all frames for this pose';

  String get shootingGuideSectionOverline => _isRu ? 'Справка' : 'Guide';
  String get shootingGuideSectionTitle => _isRu ? 'Съёмка' : 'Shooting';
  String get shootingGuideGeneralTipsHeading => _isRu ? 'Общие советы' : 'General tips';
  String get shootingGuideAssetMissing =>
      _isRu ? 'Изображение недоступно' : 'Image unavailable';
  String get shootingGuideStartButton => _isRu ? 'Понятно' : 'OK';

  String deliveryStateLabel(String serverDeliveryState) {
    switch (serverDeliveryState) {
      case 'completed':
        return _isRu ? 'Сервер: загружен' : 'Server: uploaded';
      case 'failed':
        return _isRu ? 'Сервер: ошибка отправки' : 'Server: upload failed';
      case 'uploading':
        return _isRu ? 'Сервер: отправка…' : 'Server: uploading...';
      case 'pending':
      default:
        return _isRu ? 'Сервер: не загружен' : 'Server: pending';
    }
  }
}

class _Delegate extends LocalizationsDelegate<AppLocalizations> {
  const _Delegate();

  @override
  bool isSupported(Locale locale) =>
      AppLocalizations.supportedLocales.any((l) => l.languageCode == locale.languageCode);

  @override
  Future<AppLocalizations> load(Locale locale) async => AppLocalizations(locale);

  @override
  bool shouldReload(covariant LocalizationsDelegate<AppLocalizations> old) => false;
}
