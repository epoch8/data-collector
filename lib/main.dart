import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:data_collector/core/presentation/local_capture_thumb.dart';
import 'package:data_collector/core/presentation/local_disk_photo_dialog.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'bootstrap.dart';
import 'firebase_options.dart';
import 'core/api/api_environment.dart';
import 'core/preferences/app_preferences.dart';
import 'features/projects/providers/project_providers.dart';
import 'models/project_config.dart';
import 'features/collection/logic/collection_flow_resolver.dart';
import 'features/collection/presentation/flow/collection_flow_screen.dart';
import 'core/storage/database.dart';
import 'core/storage/database_provider.dart';
import 'core/package/package_paths.dart';
import 'features/collection/logic/package_payload_codec.dart';
import 'features/collection/presentation/flow/package_payload_keys.dart';
import 'features/sync/presentation/server_sync_tab.dart';
import 'features/history/history_local_actions.dart';
import 'features/history/package_delivery_style.dart';
import 'features/history/package_manifest_export.dart';
import 'features/help/presentation/help_screen.dart';
import 'theme/epoch8_theme.dart';
import 'theme/theme_controller.dart';
import 'theme/epoch8_ui.dart';
import 'theme/epoch8_loader.dart';
import 'theme/epoch8_error_screen.dart';
import 'theme/epoch8_app_bar_controls.dart';
import 'l10n/app_localizations.dart';
import 'l10n/locale_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppPreferences.ensureInitialized();
  initAppLocale();
  initAppThemeMode();
  ErrorWidget.builder = (details) => Epoch8ErrorScreen(details: details);
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
    firebaseInitialized = true;
    // Дождаться первого события: сессия Email/Password уже восстановлена с диска (персистентность по умолчанию).
    await FirebaseAuth.instance.authStateChanges().first;
    appRouterInitialLocation = FirebaseAuth.instance.currentUser != null
        ? '/dashboard'
        : '/login';
  } catch (e) {
    debugPrint('Firebase.initializeApp: $e');
  }
  await PackagePaths.init();
  runApp(ProviderScope(child: DataCollectorApp()));
}

class _AuthRefresh extends ChangeNotifier {
  _AuthRefresh() {
    FirebaseAuth.instance.authStateChanges().listen((_) => notifyListeners());
  }
}

GoRouter _buildAppRouter(Listenable? authRefresh) {
  return GoRouter(
    initialLocation: appRouterInitialLocation,
    refreshListenable: authRefresh,
    redirect: (context, state) {
      if (!firebaseInitialized) return null;
      final user = FirebaseAuth.instance.currentUser;
      final onLogin = state.matchedLocation == '/login';
      if (user == null) return onLogin ? null : '/login';
      if (onLogin) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/dashboard',
        builder: (context, state) => const DashboardScreen(),
      ),
      GoRoute(
        path: '/project/:id/wizard',
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          return Consumer(
            builder: (context, ref, _) {
              final async = ref.watch(projectsProvider);
              return async.when(
                skipLoadingOnReload: true,
                data: (projects) {
                  final loc = AppLocalizations.of(context);
                  try {
                    projects.firstWhere((p) => p.id == id);
                  } catch (_) {
                    return Scaffold(
                      appBar: AppBar(title: _epoch8AppBarTitle(loc.project)),
                      body: Center(child: Text(loc.projectNotFound)),
                    );
                  }
                  return CollectionFlowScreen(projectId: id);
                },
                loading: () => Scaffold(body: Epoch8Loader.center()),
                error: (e, _) => Scaffold(
                  body: Center(
                    child: Text(
                      '${AppLocalizations.of(context).errorPrefix}: $e',
                    ),
                  ),
                ),
              );
            },
          );
        },
      ),
      GoRoute(
        path: '/history/project/:projectId/subject/:subjectId',
        builder: (context, state) => SubjectHistoryScreen(
          projectId: state.pathParameters['projectId']!,
          subjectId: state.pathParameters['subjectId']!,
        ),
      ),
      GoRoute(
        path: '/history/package/:packageId',
        builder: (context, state) =>
            PackageHistoryScreen(packageId: state.pathParameters['packageId']!),
      ),
      GoRoute(path: '/help', builder: (context, state) => const HelpScreen()),
    ],
  );
}

Widget _epoch8AppBarTitle(String title) {
  return Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(7),
        child: Image.asset(
          'e8_logo.png',
          width: 26,
          height: 26,
          fit: BoxFit.cover,
        ),
      ),
      const SizedBox(width: 12),
      Flexible(
        child: Text(
          title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontWeight: FontWeight.w600,
            letterSpacing: -0.2,
          ),
        ),
      ),
    ],
  );
}

class DataCollectorApp extends StatefulWidget {
  const DataCollectorApp({super.key});

  @override
  State<DataCollectorApp> createState() => _DataCollectorAppState();
}

class _DataCollectorAppState extends State<DataCollectorApp>
    with WidgetsBindingObserver {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    final refresh = firebaseInitialized ? _AuthRefresh() : null;
    _router = _buildAppRouter(refresh);
    WidgetsBinding.instance.addObserver(this);
    _syncBrightness();
    appThemeModeNotifier.addListener(_syncBrightness);
    appBrightnessNotifier.addListener(_applySystemChrome);
  }

  @override
  void dispose() {
    appThemeModeNotifier.removeListener(_syncBrightness);
    appBrightnessNotifier.removeListener(_applySystemChrome);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangePlatformBrightness() {
    _syncBrightness();
  }

  void _syncBrightness() {
    final mode = appThemeModeNotifier.value;
    final effective = mode == ThemeMode.light
        ? Brightness.light
        : Brightness.dark;
    if (appBrightnessNotifier.value != effective) {
      appBrightnessNotifier.value = effective;
    } else {
      // Даже если значение совпало — на некоторых вендорных прошивках
      // (например, Samsung One UI) системный chrome не подхватывает
      // изменение автоматически. Применяем явно.
      _applySystemChrome();
    }
  }

  void _applySystemChrome() {
    // Явно тянем стиль статус-бара/навигации под текущую тему,
    // чтобы на Samsung/One UI не оставались светлые иконки на светлом фоне
    // и наоборот.
    final isLight = appBrightnessNotifier.value == Brightness.light;
    SystemChrome.setSystemUIOverlayStyle(
      SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: isLight ? Brightness.dark : Brightness.light,
        statusBarBrightness: isLight ? Brightness.light : Brightness.dark,
        systemNavigationBarColor: isLight
            ? const Color(0xFFF7F8FB)
            : const Color(0xFF0E1118),
        systemNavigationBarIconBrightness: isLight
            ? Brightness.dark
            : Brightness.light,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: appThemeModeNotifier,
      builder: (context, themeMode, __) => ValueListenableBuilder<Brightness>(
        valueListenable: appBrightnessNotifier,
        builder: (context, _, __) => ValueListenableBuilder<Locale>(
          valueListenable: appLocaleNotifier,
          builder: (context, locale, _) => MaterialApp.router(
            locale: locale,
            onGenerateTitle: (context) => AppLocalizations.of(context).appTitle,
            theme: Epoch8Theme.light,
            darkTheme: Epoch8Theme.dark,
            themeMode: themeMode,
            themeAnimationDuration: Duration.zero,
            themeAnimationCurve: Curves.linear,
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
            routerConfig: _router,
            debugShowCheckedModeBanner: false,
          ),
        ),
      ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    appBrightnessNotifier.addListener(_onBrightnessChanged);
  }

  @override
  void dispose() {
    appBrightnessNotifier.removeListener(_onBrightnessChanged);
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _onBrightnessChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _signInWithFirebase() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await FirebaseAuth.instance.signInWithEmailAndPassword(
        email: _email.text.trim(),
        password: _password.text,
      );
      if (mounted) context.go('/dashboard');
    } on FirebaseAuthException catch (e) {
      setState(() => _error = e.message ?? e.code);
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final loc = AppLocalizations.of(context);
    return Scaffold(
      body: Epoch8ScreenBody(
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return Stack(
                children: [
                  SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(
                      Epoch8Layout.pagePadding,
                      56,
                      Epoch8Layout.pagePadding,
                      0,
                    ),
                    child: ConstrainedBox(
                      constraints: BoxConstraints(
                        minHeight: constraints.maxHeight,
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const SizedBox(height: 24),
                          Container(
                            width: 190,
                            height: 190,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(32),
                              color: Epoch8Theme.card.withValues(alpha: 0.9),
                              border: Border.all(color: Epoch8Theme.border),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.45),
                                  blurRadius: 32,
                                  offset: const Offset(0, 16),
                                ),
                              ],
                            ),
                            clipBehavior: Clip.antiAlias,
                            padding: const EdgeInsets.all(16),
                            child: Image.asset(
                              'e8_logo.png',
                              fit: BoxFit.contain,
                            ),
                          ),
                          const SizedBox(height: 28),
                          Text(
                            'EPOCH8',
                            style: t.labelLarge?.copyWith(
                              color: Epoch8Theme.accent,
                              letterSpacing: 5,
                              fontWeight: FontWeight.w800,
                              fontSize: 12,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            loc.loginTitle,
                            style: t.headlineSmall,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            loc.loginSubtitle,
                            style: t.bodyMedium?.copyWith(fontSize: 15),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 32),
                          if (firebaseInitialized) ...[
                            Epoch8Card(
                              child: Column(
                                children: [
                                  TextField(
                                    controller: _email,
                                    keyboardType: TextInputType.emailAddress,
                                    autofillHints: const [AutofillHints.email],
                                    decoration: InputDecoration(
                                      labelText: loc.email,
                                      border: const OutlineInputBorder(),
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                  TextField(
                                    controller: _password,
                                    obscureText: true,
                                    autofillHints: const [
                                      AutofillHints.password,
                                    ],
                                    decoration: InputDecoration(
                                      labelText: loc.password,
                                      border: OutlineInputBorder(),
                                    ),
                                    onSubmitted: (_) {
                                      if (!_busy) _signInWithFirebase();
                                    },
                                  ),
                                  if (_error != null) ...[
                                    const SizedBox(height: 12),
                                    Text(
                                      _error!,
                                      style: t.bodySmall?.copyWith(
                                        color: Epoch8Theme.danger,
                                      ),
                                      textAlign: TextAlign.center,
                                    ),
                                  ],
                                  const SizedBox(height: 20),
                                  SizedBox(
                                    width: double.infinity,
                                    child: FilledButton(
                                      onPressed: _busy
                                          ? null
                                          : _signInWithFirebase,
                                      child: _busy
                                          ? const SizedBox(
                                              height: 22,
                                              width: 22,
                                              child: CircularProgressIndicator(
                                                strokeWidth: 2,
                                              ),
                                            )
                                          : Text(loc.signIn),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ] else ...[
                            Text(
                              loc.firebaseNotInitialized,
                              style: t.bodySmall?.copyWith(
                                color: Epoch8Theme.textMuted,
                              ),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 20),
                            SizedBox(
                              width: double.infinity,
                              child: FilledButton(
                                onPressed: () => context.go('/dashboard'),
                                child: Text(loc.goToWorkspace),
                              ),
                            ),
                          ],
                          const SizedBox(height: 32),
                        ],
                      ),
                    ),
                  ),
                  Positioned(
                    top: 0,
                    right: 0,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Epoch8ThemeSwitcher(),
                            const Epoch8LanguageSwitcher(),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Кастомные элементы внутри Dashboard (TabBar surface/border, FAB-цвета)
    // используют глобальные токены Epoch8Theme.* и не подписаны на Theme.of.
    // Триггерим ребилд при смене темы вручную.
    appBrightnessNotifier.addListener(_onBrightnessChanged);
  }

  @override
  void dispose() {
    appBrightnessNotifier.removeListener(_onBrightnessChanged);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void _onBrightnessChanged() {
    if (mounted) setState(() {});
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && ApiEnvironment.isConfigured) {
      ref.invalidate(projectsProvider);
    }
  }

  Future<void> _refreshProjects() async {
    ref.invalidate(projectsProvider);
    await ref.read(projectsProvider.future);
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final projectsAsync = ref.watch(projectsProvider);
    final packagesAsync = ref.watch(packagesStreamProvider);

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          leading: const Epoch8ThemeSwitcher(),
          title: _epoch8AppBarTitle(loc.workspaceTitle),
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(66),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
              child: Container(
                decoration: BoxDecoration(
                  color: Epoch8Theme.tabBarSurface,
                  borderRadius: BorderRadius.circular(Epoch8Layout.radiusMd),
                  border: Border.all(color: Epoch8Theme.tabBarBorder),
                ),
                child: TabBar(
                  padding: const EdgeInsets.all(4),
                  indicator: BoxDecoration(
                    borderRadius: BorderRadius.circular(
                      Epoch8Layout.radiusSm + 2,
                    ),
                    color: Epoch8Theme.accent.withValues(alpha: 0.18),
                    border: Border.all(
                      color: Epoch8Theme.accent.withValues(alpha: 0.35),
                    ),
                  ),
                  indicatorSize: TabBarIndicatorSize.tab,
                  dividerHeight: 0,
                  tabs: [
                    Tab(
                      icon: const Icon(Icons.folder_outlined, size: 20),
                      text: loc.projectsTab,
                    ),
                    Tab(
                      icon: const Icon(Icons.cloud_outlined, size: 20),
                      text: loc.serverTab,
                    ),
                    Tab(
                      icon: const Icon(Icons.history_outlined, size: 20),
                      text: loc.historyTab,
                    ),
                  ],
                ),
              ),
            ),
          ),
          actions: [
            const Epoch8LanguageSwitcher(),
            const SizedBox(width: 2),
            IconButton(
              icon: const Icon(Icons.logout_outlined),
              tooltip: loc.logout,
              onPressed: () async {
                if (firebaseInitialized) {
                  await FirebaseAuth.instance.signOut();
                }
                if (context.mounted) context.go('/login');
              },
            ),
          ],
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () => context.push('/help'),
          tooltip: loc.helpTitle,
          child: const Icon(Icons.help_outline),
        ),
        body: Epoch8ScreenBody(
          child: TabBarView(
            children: [
              projectsAsync.when(
                data: (projects) {
                  final emptySubtitle = ApiEnvironment.isConfigured
                      ? loc.serverEmptySubtitleConfigured
                      : loc.serverEmptySubtitleNotConfigured;
                  final list = ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(
                      Epoch8Layout.pagePadding,
                      12,
                      Epoch8Layout.pagePadding,
                      24,
                    ),
                    itemCount: projects.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      final project = projects[index];
                      return Epoch8Card(
                        accentBorder: resolveCollectionFlow(
                          project,
                        ).shouldGroupHistoryBySubject,
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 4,
                            vertical: 4,
                          ),
                          leading: Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(14),
                              color: Epoch8Theme.accent.withValues(alpha: 0.12),
                              border: Border.all(
                                color: Epoch8Theme.accent.withValues(
                                  alpha: 0.25,
                                ),
                              ),
                            ),
                            child: Icon(
                              Icons.folder_special_outlined,
                              color: Epoch8Theme.accent,
                              size: 26,
                            ),
                          ),
                          title: Text(
                            project.name,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 16,
                            ),
                          ),
                          subtitle: Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: Text(
                              () {
                                final flow = resolveCollectionFlow(project);
                                if (flow.isSingleScrollOnly) {
                                  return '${loc.version} ${project.version} • ${project.config.fields.length}';
                                }
                                final nCam = flow.cameraPoseCount;
                                final hasInstr = flow.steps.any(
                                  (s) =>
                                      s.kind ==
                                      CollectionScreenKind.instruction,
                                );
                                final hasForm = flow.steps.any(
                                  (s) => s.kind == CollectionScreenKind.form,
                                );
                                final bits = <String>[
                                  '${loc.version} ${project.version}',
                                ];
                                if (hasForm) bits.add(loc.formLabel);
                                if (hasInstr) bits.add(loc.guideLabel);
                                if (nCam > 0)
                                  bits.add(loc.cameraPosesCount(nCam));
                                if (flow.reviewStepIndex != null)
                                  bits.add(loc.reviewLabel);
                                return bits.join(' • ');
                              }(),
                              style: Theme.of(
                                context,
                              ).textTheme.bodySmall?.copyWith(height: 1.4),
                            ),
                          ),
                          trailing: Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Epoch8Theme.bgElevated,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Icon(
                              Icons.arrow_forward_ios_rounded,
                              size: 16,
                              color: Epoch8Theme.textMuted,
                            ),
                          ),
                          onTap: () =>
                              context.go('/project/${project.id}/wizard'),
                        ),
                      );
                    },
                  );
                  if (projects.isEmpty) {
                    return RefreshIndicator(
                      onRefresh: _refreshProjects,
                      child: ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: [
                          SizedBox(
                            height: MediaQuery.sizeOf(context).height * 0.5,
                            child: Epoch8EmptyState(
                              icon: Icons.folder_open_outlined,
                              title: loc.noProjectsTitle,
                              subtitle: emptySubtitle,
                            ),
                          ),
                        ],
                      ),
                    );
                  }
                  return RefreshIndicator(
                    onRefresh: _refreshProjects,
                    child: list,
                  );
                },
                loading: () => Epoch8Loader.center(),
                error: (e, _) => Center(child: Text('${loc.configError}: $e')),
              ),
              const ServerSyncTab(),
              _historyTabBody(context, ref, projectsAsync, packagesAsync),
            ],
          ),
        ),
      ),
    );
  }
}

class SubjectHistoryScreen extends ConsumerWidget {
  const SubjectHistoryScreen({
    super.key,
    required this.projectId,
    required this.subjectId,
  });

  final String projectId;
  final String subjectId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loc = AppLocalizations.of(context);
    final packagesAsync = ref.watch(packagesStreamProvider);
    return Scaffold(
      appBar: AppBar(
        title: _epoch8AppBarTitle('${loc.objectLabel} $subjectId'),
      ),
      body: packagesAsync.when(
        data: (packages) {
          final filtered =
              packages
                  .where(
                    (p) =>
                        p.status != 'draft' &&
                        p.projectId == projectId &&
                        _extractSubjectIdFromPackage(p) == subjectId,
                  )
                  .toList()
                ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
          if (filtered.isEmpty) {
            return Epoch8EmptyState(
              icon: Icons.cloud_off_outlined,
              title: loc.packageNotFoundShort,
              subtitle: loc.noPackagesForSubject,
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(
              Epoch8Layout.pagePadding,
              12,
              Epoch8Layout.pagePadding,
              24,
            ),
            itemCount: filtered.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final pkg = filtered[index];
              final photoCount = _extractImagePaths(pkg).length;
              return Epoch8Card(
                highlightBorderColor: historyPackageBorderColor(
                  pkg.serverDeliveryState,
                ),
                child: ListTile(
                  title: Text(
                    '${AppLocalizations.of(context).packageWord} ${pkg.id}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  subtitle: Text(
                    '${pkg.createdAt.toString().split('.').first}\n${AppLocalizations.of(context).photos}: $photoCount • ${pkg.projectId}\n${deliveryStateShort(context, pkg.serverDeliveryState)}',
                  ),
                  isThreeLine: true,
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        tooltip: loc.downloadManifest,
                        icon: Icon(
                          Icons.download_outlined,
                          size: 22,
                          color: Epoch8Theme.accent,
                        ),
                        onPressed: () => sharePackageServerManifestWithSnackBar(
                          context,
                          pkg,
                        ),
                      ),
                      IconButton(
                        tooltip: loc.deleteFromDevice,
                        icon: Icon(
                          Icons.delete_outline,
                          size: 22,
                          color: Epoch8Theme.danger,
                        ),
                        onPressed: () async {
                          await confirmAndDeleteLocalPackage(context, ref, pkg);
                        },
                      ),
                      Icon(
                        Icons.arrow_forward_ios_rounded,
                        size: 16,
                        color: Epoch8Theme.textMuted,
                      ),
                    ],
                  ),
                  onTap: () => context.push('/history/package/${pkg.id}'),
                ),
              );
            },
          );
        },
        loading: () => Epoch8Loader.center(),
        error: (e, st) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              '${loc.errorPrefix}: $e',
              style: TextStyle(color: Epoch8Theme.danger),
            ),
          ),
        ),
      ),
    );
  }
}

class PackageHistoryScreen extends ConsumerWidget {
  const PackageHistoryScreen({super.key, required this.packageId});

  final String packageId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loc = AppLocalizations.of(context);
    final packagesAsync = ref.watch(packagesStreamProvider);
    return packagesAsync.when(
      data: (packages) {
        Package? pkg;
        for (final item in packages) {
          if (item.id == packageId) {
            pkg = item;
            break;
          }
        }
        return Scaffold(
          appBar: AppBar(
            title: _epoch8AppBarTitle('${loc.packageWord} $packageId'),
            actions: [
              const Epoch8LanguageSwitcher(),
              const SizedBox(width: 2),
              if (pkg != null) ...[
                IconButton(
                  tooltip: loc.downloadManifestAsServer,
                  icon: const Icon(Icons.download_outlined),
                  onPressed: () =>
                      sharePackageServerManifestWithSnackBar(context, pkg!),
                ),
                IconButton(
                  tooltip: loc.deleteFromDevice,
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () async {
                    await confirmAndDeleteLocalPackage(context, ref, pkg!);
                    if (!context.mounted) return;
                    if (context.canPop()) {
                      context.pop();
                    } else {
                      context.go('/dashboard');
                    }
                  },
                ),
              ],
            ],
          ),
          body: pkg == null
              ? Epoch8EmptyState(
                  icon: Icons.error_outline,
                  title: loc.packageNotFoundTitle,
                  subtitle: loc.packageNotFoundSubtitle,
                )
              : _packageHistoryDetailBody(context, ref, pkg),
        );
      },
      loading: () => Scaffold(
        appBar: AppBar(
          title: _epoch8AppBarTitle('${loc.packageWord} $packageId'),
        ),
        body: Epoch8Loader.center(),
      ),
      error: (e, st) => Scaffold(
        appBar: AppBar(
          title: _epoch8AppBarTitle('${loc.packageWord} $packageId'),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              '${loc.errorPrefix}: $e',
              style: TextStyle(color: Epoch8Theme.danger),
            ),
          ),
        ),
      ),
    );
  }
}

Widget _packageHistoryDetailBody(
  BuildContext context,
  WidgetRef ref,
  Package pkg,
) {
  final loc = AppLocalizations.of(context);
  final raw = _decodePackageData(pkg);
  final photos = _extractImagePaths(pkg);
  final metadataByPath = _extractPoseMetadataByPath(raw, pkg.id);
  final projectsList = ref
      .watch(projectsProvider)
      .maybeWhen(data: (v) => v, orElse: () => null);
  final projMeta = _projectById(projectsList, pkg.projectId);
  final groupSubject =
      projMeta != null &&
      resolveCollectionFlow(projMeta).shouldGroupHistoryBySubject;
  final subjectLabel = _extractSubjectId(raw);
  return ListView(
    padding: const EdgeInsets.fromLTRB(
      Epoch8Layout.pagePadding,
      12,
      Epoch8Layout.pagePadding,
      24,
    ),
    children: [
      Epoch8Card(
        highlightBorderColor: historyPackageBorderColor(
          pkg.serverDeliveryState,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              projMeta != null
                  ? loc.projectLabel(projMeta.name)
                  : loc.projectLabel(pkg.projectId),
              style: Theme.of(context).textTheme.titleSmall,
            ),
            if (groupSubject && subjectLabel != 'no-id') ...[
              const SizedBox(height: 8),
              Text(
                '${loc.objectLabel}: $subjectLabel',
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ],
            const SizedBox(height: 8),
            Text(
              deliveryStateShort(context, pkg.serverDeliveryState),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: historyPackageBorderColor(pkg.serverDeliveryState),
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '${loc.identifier}: ${pkg.projectId}',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
            ),
            Text(
              '${loc.createdAt}: ${pkg.createdAt.toString().split('.').first}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            Text(
              '${loc.photos}: ${photos.length}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      Epoch8Card(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              loc.formDataTitle,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            ..._packageFormSummaryRows(context, ref, pkg, raw),
          ],
        ),
      ),
      const SizedBox(height: 12),
      if (photos.isEmpty)
        Epoch8EmptyState(
          icon: Icons.photo_library_outlined,
          title: loc.packageNoPhotosTitle,
          subtitle: loc.packageNoPhotosSubtitle,
        )
      else
        ...photos.map((path) {
          final meta = metadataByPath[path];
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Epoch8Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: InkWell(
                      onTap: () => showLocalDiskPhotoDialog(context, path),
                      child: Stack(
                        children: [
                          localCaptureImageBox(
                            path,
                            height: 180,
                            width: double.infinity,
                          ),
                          Positioned(
                            right: 8,
                            bottom: 8,
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.black.withValues(alpha: 0.55),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                loc.openPhoto,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    path.split(RegExp(r'[\\/]')).last,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${loc.pathLabel}: $path',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Epoch8Theme.textMuted,
                    ),
                  ),
                  if (meta != null) ...[
                    const SizedBox(height: 8),
                    Theme(
                      data: Theme.of(
                        context,
                      ).copyWith(dividerColor: Colors.transparent),
                      child: ExpansionTile(
                        tilePadding: EdgeInsets.zero,
                        childrenPadding: EdgeInsets.zero,
                        iconColor: Epoch8Theme.textMuted,
                        collapsedIconColor: Epoch8Theme.textMuted,
                        title: Text(
                          loc.frameCameraParams,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(fontWeight: FontWeight.w600),
                        ),
                        children: [
                          SelectableText(
                            const JsonEncoder.withIndent('  ').convert(meta),
                            style: Theme.of(
                              context,
                            ).textTheme.bodySmall?.copyWith(height: 1.35),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          );
        }),
      const SizedBox(height: 8),
      SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: () => sharePackageServerManifestWithSnackBar(context, pkg),
          icon: const Icon(Icons.download_outlined),
          label: Text(loc.downloadManifestAsServer),
        ),
      ),
    ],
  );
}

Widget _historyTabBody(
  BuildContext context,
  WidgetRef ref,
  AsyncValue<List<Project>> projectsAsync,
  AsyncValue<List<Package>> packagesAsync,
) {
  return projectsAsync.when(
    data: (projects) {
      return packagesAsync.when(
        data: (packages) {
          final visible = packages.where((p) => p.status != 'draft').toList();
          if (visible.isEmpty) {
            return Epoch8EmptyState(
              icon: Icons.cloud_outlined,
              title: AppLocalizations.of(context).historyEmptyTitle,
              subtitle: AppLocalizations.of(context).historyEmptySubtitle,
            );
          }
          final byProject = <String, List<Package>>{};
          for (final p in visible) {
            byProject.putIfAbsent(p.projectId, () => []).add(p);
          }
          final knownIds = projects.map((p) => p.id).toSet();
          final sections = <Widget>[];
          for (final proj in projects) {
            final pkgs = byProject[proj.id];
            if (pkgs == null || pkgs.isEmpty) continue;
            sections.add(_historyProjectSection(context, ref, proj, pkgs));
          }
          for (final entry in byProject.entries) {
            if (knownIds.contains(entry.key)) continue;
            sections.add(
              _historyOrphanProjectSection(
                context,
                ref,
                entry.key,
                entry.value,
              ),
            );
          }
          final completedCount = visible
              .where((p) => p.serverDeliveryState == 'completed')
              .length;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (completedCount > 0)
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    Epoch8Layout.pagePadding,
                    4,
                    Epoch8Layout.pagePadding,
                    0,
                  ),
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: () =>
                          confirmAndClearUploadedPackagesCache(context, ref),
                      icon: const Icon(
                        Icons.cleaning_services_outlined,
                        size: 18,
                      ),
                      label: Text(
                        AppLocalizations.of(
                          context,
                        ).clearUploadedCacheWithCount(completedCount),
                      ),
                    ),
                  ),
                ),
              Expanded(
                child: ListView(
                  padding: EdgeInsets.fromLTRB(
                    Epoch8Layout.pagePadding,
                    completedCount > 0 ? 4 : 12,
                    Epoch8Layout.pagePadding,
                    24,
                  ),
                  children: sections,
                ),
              ),
            ],
          );
        },
        loading: () => Epoch8Loader.center(),
        error: (e, _) => Center(
          child: Text('${AppLocalizations.of(context).errorPrefix}: $e'),
        ),
      );
    },
    loading: () => Epoch8Loader.center(),
    error: (e, _) =>
        Center(child: Text('${AppLocalizations.of(context).configError}: $e')),
  );
}

Widget _historyProjectSection(
  BuildContext context,
  WidgetRef ref,
  Project proj,
  List<Package> packages,
) {
  final flow = resolveCollectionFlow(proj);
  final bySubject = flow.shouldGroupHistoryBySubject;
  return Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Row(
          children: [
            Icon(
              bySubject ? Icons.pets_outlined : Icons.folder_outlined,
              size: 20,
              color: Epoch8Theme.accent,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                proj.name,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: Epoch8Theme.accent,
                ),
              ),
            ),
            Text(
              AppLocalizations.of(context).packageCountShort(packages.length),
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(color: Epoch8Theme.textMuted),
            ),
          ],
        ),
      ),
      if (bySubject) ...[
        for (final g in _groupPackagesBySubject(packages)) ...[
          Epoch8Card(
            highlightBorderColor: historyGroupBorderColor(g.packages),
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 4,
                vertical: 4,
              ),
              leading: Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: Epoch8Theme.accent.withValues(alpha: 0.12),
                  border: Border.all(
                    color: Epoch8Theme.accent.withValues(alpha: 0.25),
                  ),
                ),
                child: Icon(
                  Icons.badge_outlined,
                  color: Epoch8Theme.accent,
                  size: 24,
                ),
              ),
              title: Text(
                '${AppLocalizations.of(context).objectLabel} ${g.subjectId}',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  _historySubjectGroupSubtitle(context, g.packages),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              isThreeLine: true,
              trailing: Icon(
                Icons.arrow_forward_ios_rounded,
                size: 16,
                color: Epoch8Theme.textMuted,
              ),
              onTap: () => context.push(
                '/history/project/${proj.id}/subject/${Uri.encodeComponent(g.subjectId)}',
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
      ] else ...[
        for (final pkg
            in (packages.toList()
              ..sort((a, b) => b.createdAt.compareTo(a.createdAt)))) ...[
          Epoch8Card(
            highlightBorderColor: historyPackageBorderColor(
              pkg.serverDeliveryState,
            ),
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 4,
                vertical: 4,
              ),
              leading: Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: Epoch8Theme.card,
                  border: Border.all(
                    color: historyPackageBorderColor(
                      pkg.serverDeliveryState,
                    ).withValues(alpha: 0.35),
                  ),
                ),
                child: Icon(
                  Icons.photo_library_outlined,
                  color: historyPackageBorderColor(pkg.serverDeliveryState),
                  size: 24,
                ),
              ),
              title: Text(
                pkg.id,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  '${pkg.createdAt.toString().split('.').first} • ${AppLocalizations.of(context).photosLower}: ${_extractImagePaths(pkg).length}\n${_historyPackageSubtitle(context, pkg)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              isThreeLine: true,
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    tooltip: AppLocalizations.of(context).downloadManifest,
                    icon: Icon(
                      Icons.download_outlined,
                      size: 22,
                      color: Epoch8Theme.accent,
                    ),
                    onPressed: () =>
                        sharePackageServerManifestWithSnackBar(context, pkg),
                  ),
                  IconButton(
                    tooltip: AppLocalizations.of(context).deleteFromDevice,
                    icon: Icon(
                      Icons.delete_outline,
                      size: 22,
                      color: Epoch8Theme.danger,
                    ),
                    onPressed: () async {
                      await confirmAndDeleteLocalPackage(context, ref, pkg);
                    },
                  ),
                  Icon(
                    Icons.arrow_forward_ios_rounded,
                    size: 16,
                    color: Epoch8Theme.textMuted,
                  ),
                ],
              ),
              onTap: () => context.push('/history/package/${pkg.id}'),
            ),
          ),
          const SizedBox(height: 12),
        ],
      ],
      const SizedBox(height: 8),
    ],
  );
}

String _historySubjectGroupSubtitle(
  BuildContext context,
  List<Package> packages,
) {
  final loc = AppLocalizations.of(context);
  final n = packages.length;
  final photos = packages.fold<int>(
    0,
    (a, p) => a + _extractImagePaths(p).length,
  );
  final pending = packages
      .where((p) => p.serverDeliveryState != 'completed')
      .length;
  final failed = packages
      .where((p) => p.serverDeliveryState == 'failed')
      .length;
  final buf = StringBuffer('${loc.packageWord}: $n • ${loc.photos}: $photos');
  if (failed > 0) {
    buf.write('\n${loc.uploadFailed}: $failed');
  } else if (pending > 0) {
    buf.write('\n${loc.notOnServer}: $pending / $n');
  } else {
    buf.write('\n${loc.allPackagesOnServer}');
  }
  return buf.toString();
}

String _historyPackageSubtitle(BuildContext context, Package pkg) {
  final raw = unpackPackageFormData(pkg.dataJson);
  final n = raw['session_note']?.toString().trim() ?? '';
  final note = n.isEmpty ? '' : (n.length > 80 ? '${n.substring(0, 80)}…' : n);
  final delivery = deliveryStateShort(context, pkg.serverDeliveryState);
  if (note.isEmpty) return delivery;
  return '$note\n$delivery';
}

Widget _historyOrphanProjectSection(
  BuildContext context,
  WidgetRef ref,
  String projectId,
  List<Package> packages,
) {
  final sorted = packages.toList()
    ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
  return Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Text(
          '${AppLocalizations.of(context).project} $projectId (${AppLocalizations.of(context).projectMissingInConfig})',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            color: Epoch8Theme.textMuted,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      for (final pkg in sorted) ...[
        Epoch8Card(
          highlightBorderColor: historyPackageBorderColor(
            pkg.serverDeliveryState,
          ),
          child: ListTile(
            title: Text(
              pkg.id,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text(
              '${pkg.createdAt.toString().split('.').first}\n${deliveryStateShort(context, pkg.serverDeliveryState)}',
            ),
            isThreeLine: true,
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  tooltip: AppLocalizations.of(context).downloadManifest,
                  icon: Icon(
                    Icons.download_outlined,
                    size: 22,
                    color: Epoch8Theme.accent,
                  ),
                  onPressed: () =>
                      sharePackageServerManifestWithSnackBar(context, pkg),
                ),
                IconButton(
                  tooltip: AppLocalizations.of(context).deleteFromDevice,
                  icon: Icon(
                    Icons.delete_outline,
                    size: 22,
                    color: Epoch8Theme.danger,
                  ),
                  onPressed: () async {
                    await confirmAndDeleteLocalPackage(context, ref, pkg);
                  },
                ),
                Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 16,
                  color: Epoch8Theme.textMuted,
                ),
              ],
            ),
            onTap: () => context.push('/history/package/${pkg.id}'),
          ),
        ),
        const SizedBox(height: 12),
      ],
    ],
  );
}

Project? _projectById(List<Project>? projects, String id) {
  if (projects == null) return null;
  for (final p in projects) {
    if (p.id == id) return p;
  }
  return null;
}

List<Widget> _packageFormSummaryRows(
  BuildContext context,
  WidgetRef ref,
  Package pkg,
  Map<String, dynamic> raw,
) {
  final projects = ref
      .watch(projectsProvider)
      .maybeWhen(data: (v) => v, orElse: () => null);
  final proj = _projectById(projects, pkg.projectId);
  if (proj == null) return _genericPayloadFieldRows(context, raw);
  final rows = <Widget>[];
  for (final f in proj.config.fields) {
    if (f.type == 'instruction') continue;
    if (f.type == 'camera_photo') {
      final v = raw[f.fieldId];
      final int n;
      if (v is Map) {
        n = v.keys.where((k) => k.toString().trim().isNotEmpty).length;
      } else if (v is List) {
        n = v.where((e) => e != null && e.toString().isNotEmpty).length;
      } else {
        n = (v != null && v.toString().trim().isNotEmpty ? 1 : 0);
      }
      rows.add(
        _packageHistoryFieldRow(
          context,
          f.title,
          n == 0 ? null : '$n ${AppLocalizations.of(context).fileWord}',
        ),
      );
      continue;
    }
    final val = raw[f.fieldId];
    final display = f.type == 'datetime'
        ? _formatPackageScanTime(val)
        : val?.toString();
    rows.add(_packageHistoryFieldRow(context, f.title, display));
  }
  return rows;
}

List<Widget> _genericPayloadFieldRows(
  BuildContext context,
  Map<String, dynamic> raw,
) {
  const skip = {
    'camera_capture_context',
    'korovas_camera_context',
    PackagePayloadKeys.cameraSession,
    PackagePayloadKeys.cameraDebug,
  };
  final out = <Widget>[];
  final keys = raw.keys.where((k) => !skip.contains(k)).toList()..sort();
  for (final k in keys) {
    final v = raw[k];
    String display;
    if (v == null) {
      display = '—';
    } else if (v is List) {
      if (v.isEmpty) {
        display = '—';
      } else if (v.every(
        (x) =>
            x is String &&
            (x.contains('/') || x.contains('\\') || x.startsWith('blobs/')),
      )) {
        display = '${v.length} ${AppLocalizations.of(context).fileWord}';
      } else {
        display = v.map((x) => x.toString()).join(', ');
      }
    } else if (v is Map) {
      display = '{…}';
    } else {
      display = v.toString();
    }
    out.add(_packageHistoryFieldRow(context, k, display));
  }
  return out;
}

class _SubjectGroup {
  const _SubjectGroup({
    required this.subjectId,
    required this.packages,
    required this.totalPhotos,
  });

  final String subjectId;
  final List<Package> packages;
  final int totalPhotos;
}

List<_SubjectGroup> _groupPackagesBySubject(List<Package> packages) {
  final bySubject = <String, List<Package>>{};
  for (final pkg in packages) {
    final subjectId = _extractSubjectIdFromPackage(pkg);
    bySubject.putIfAbsent(subjectId, () => <Package>[]).add(pkg);
  }

  final groups =
      bySubject.entries
          .map(
            (entry) => _SubjectGroup(
              subjectId: entry.key,
              packages: entry.value
                ..sort((a, b) => b.createdAt.compareTo(a.createdAt)),
              totalPhotos: entry.value.fold<int>(
                0,
                (sum, pkg) => sum + _extractImagePaths(pkg).length,
              ),
            ),
          )
          .toList()
        ..sort((a, b) {
          final aDate = a.packages.isNotEmpty
              ? a.packages.first.createdAt
              : DateTime.fromMillisecondsSinceEpoch(0);
          final bDate = b.packages.isNotEmpty
              ? b.packages.first.createdAt
              : DateTime.fromMillisecondsSinceEpoch(0);
          return bDate.compareTo(aDate);
        });
  return groups;
}

String _formatPackageScanTime(dynamic v) {
  if (v == null) return '—';
  final s = v.toString().trim();
  if (s.isEmpty) return '—';
  final d = DateTime.tryParse(s)?.toLocal();
  if (d == null) return s;
  String two(int n) => n.toString().padLeft(2, '0');
  return '${d.year}-${two(d.month)}-${two(d.day)} ${two(d.hour)}:${two(d.minute)}';
}

Widget _packageHistoryFieldRow(
  BuildContext context,
  String label,
  String? value,
) {
  final v = (value == null || value.trim().isEmpty) ? '—' : value.trim();
  return Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 120,
          child: Text(
            label,
            style: TextStyle(color: Epoch8Theme.textMuted, fontSize: 13),
          ),
        ),
        Expanded(child: Text(v, style: Theme.of(context).textTheme.bodyMedium)),
      ],
    ),
  );
}

String _extractSubjectIdFromPackage(Package pkg) =>
    _extractSubjectId(_decodePackageData(pkg));

Map<String, dynamic> _decodePackageData(Package pkg) =>
    unpackPackageFormData(pkg.dataJson);

String _extractSubjectId(Map<String, dynamic> data) {
  const keys = [
    'cow_identifier',
    'cow_id',
    'cowId',
    'animal_id',
    'animalId',
    'cow_tag',
    'tag_id',
  ];
  for (final k in keys) {
    final value = data[k]?.toString().trim();
    if (value != null && value.isNotEmpty) return value;
  }
  return 'no-id';
}

List<String> _extractImagePaths(Package pkg) {
  final data = _decodePackageData(pkg);
  final out = <String>{};
  for (final entry in data.entries) {
    final key = entry.key.toLowerCase();
    final value = entry.value;
    if (value is String &&
        value.isNotEmpty &&
        (key.contains('photo') ||
            key.contains('image') ||
            key.contains('pose_'))) {
      out.add(PackagePaths.resolveMediaReference(value, pkg.id));
    }
    if (value is List) {
      for (final item in value) {
        final path = item?.toString() ?? '';
        if (path.isNotEmpty) {
          out.add(PackagePaths.resolveMediaReference(path, pkg.id));
        }
      }
    }
    if (value is Map &&
        (key.contains('photo') ||
            key.contains('image') ||
            key.contains('pose_'))) {
      for (final k in value.keys) {
        final path = k.toString();
        if (path.isEmpty) continue;
        out.add(PackagePaths.resolveMediaReference(path, pkg.id));
      }
    }
  }
  return out.toList();
}

Map<String, Map<String, dynamic>> _extractPoseMetadataByPath(
  Map<String, dynamic> data,
  String packageId,
) {
  final out = <String, Map<String, dynamic>>{};
  final ctx = data['camera_capture_context'] ?? data['korovas_camera_context'];
  if (ctx is Map) {
    final poses = ctx['poses'];
    if (poses is Map) {
      for (final poseEntry in poses.entries) {
        final poseValue = poseEntry.value;
        if (poseValue is! Map) continue;
        final shots = poseValue['shots'];
        if (shots is! List) continue;
        for (final shot in shots) {
          if (shot is! Map) continue;
          final imagePath = shot['image_path']?.toString();
          if (imagePath == null || imagePath.isEmpty) continue;
          final resolved = PackagePaths.resolveMediaReference(
            imagePath,
            packageId,
          );
          final payload = <String, dynamic>{'pose': poseEntry.key.toString()};
          for (final key in [
            'collected_at',
            'exif',
            'derived',
            PackagePayloadKeys.frameCamera,
            PackagePayloadKeys.cameraSupplement,
          ]) {
            payload[key] = shot[key];
          }
          out[resolved] = payload;
        }
      }
    }
  }

  const skipRoot = {
    'camera_capture_context',
    'korovas_camera_context',
    PackagePayloadKeys.cameraSession,
    PackagePayloadKeys.cameraDebug,
  };
  for (final fieldEntry in data.entries) {
    if (skipRoot.contains(fieldEntry.key)) continue;
    final vid = fieldEntry.value;
    if (vid is! Map) continue;
    for (final pe in vid.entries) {
      final imagePath = pe.key.toString();
      if (imagePath.isEmpty) continue;
      if (!imagePath.contains('/') &&
          !imagePath.contains(r'\') &&
          !imagePath.startsWith('blobs/')) {
        continue;
      }
      final shotBody = pe.value;
      if (shotBody is! Map) continue;
      final resolved = PackagePaths.resolveMediaReference(imagePath, packageId);
      if (out.containsKey(resolved)) continue;
      final payload = <String, dynamic>{'pose': fieldEntry.key.toString()};
      for (final key in [
        'collected_at',
        'exif',
        'derived',
        PackagePayloadKeys.frameCamera,
        PackagePayloadKeys.cameraSupplement,
      ]) {
        payload[key] = shotBody[key];
      }
      out[resolved] = payload;
    }
  }
  return out;
}
