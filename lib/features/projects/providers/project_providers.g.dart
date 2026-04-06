// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'project_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(mockProjects)
final mockProjectsProvider = MockProjectsProvider._();

final class MockProjectsProvider
    extends $FunctionalProvider<List<Project>, List<Project>, List<Project>>
    with $Provider<List<Project>> {
  MockProjectsProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'mockProjectsProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$mockProjectsHash();

  @$internal
  @override
  $ProviderElement<List<Project>> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  List<Project> create(Ref ref) {
    return mockProjects(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(List<Project> value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<List<Project>>(value),
    );
  }
}

String _$mockProjectsHash() => r'c21229fae70e3083344c524ddcb8f8a0e243db8a';
