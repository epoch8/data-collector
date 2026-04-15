// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'wizard_state_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(WizardState)
final wizardStateProvider = WizardStateFamily._();

final class WizardStateProvider
    extends $NotifierProvider<WizardState, Map<String, dynamic>> {
  WizardStateProvider._({
    required WizardStateFamily super.from,
    required String super.argument,
  }) : super(
         retry: null,
         name: r'wizardStateProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$wizardStateHash();

  @override
  String toString() {
    return r'wizardStateProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  WizardState create() => WizardState();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(Map<String, dynamic> value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<Map<String, dynamic>>(value),
    );
  }

  @override
  bool operator ==(Object other) {
    return other is WizardStateProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$wizardStateHash() => r'ddced8b91e676c1906b9fdcf4bb654ac306c9b82';

final class WizardStateFamily extends $Family
    with
        $ClassFamilyOverride<
          WizardState,
          Map<String, dynamic>,
          Map<String, dynamic>,
          Map<String, dynamic>,
          String
        > {
  WizardStateFamily._()
    : super(
        retry: null,
        name: r'wizardStateProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  WizardStateProvider call(String projectId) =>
      WizardStateProvider._(argument: projectId, from: this);

  @override
  String toString() => r'wizardStateProvider';
}

abstract class _$WizardState extends $Notifier<Map<String, dynamic>> {
  late final _$args = ref.$arg as String;
  String get projectId => _$args;

  Map<String, dynamic> build(String projectId);
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<Map<String, dynamic>, Map<String, dynamic>>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<Map<String, dynamic>, Map<String, dynamic>>,
              Map<String, dynamic>,
              Object?,
              Object?
            >;
    element.handleCreate(ref, () => build(_$args));
  }
}
