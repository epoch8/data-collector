import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'wizard_state_provider.g.dart';

/// [keepAlive]: сценарий сбора не должен терять ответы при кратковременной перезагрузке
/// каталога проектов (`projectsProvider` → loading снимает весь subtree и autoDispose).
@Riverpod(keepAlive: true)
class WizardState extends _$WizardState {
  @override
  Map<String, dynamic> build(String projectId) {
    return <String, dynamic>{};
  }

  void updateField(String fieldId, dynamic value) {
    state = {...state, fieldId: value};
  }

  /// Полная подстановка состояния (восстановление черновика).
  void replaceAll(Map<String, dynamic> next) {
    state = Map<String, dynamic>.from(next);
  }

  void reset() {
    state = <String, dynamic>{};
  }
}
