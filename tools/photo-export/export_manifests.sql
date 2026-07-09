-- Выгрузка манифestов в manifests.jsonl (альтернатива export_manifests.py, если есть psql).
--
--   psql "postgresql://USER:PASS@HOST:6432/dc-project-korovas?sslmode=require" ^
--     -f export_manifests.sql -o manifests.jsonl
--
-- Все фазы (не только completed): уберите строку AND phase = 'completed'

SELECT json_build_object(
    'package_id', package_id,
    'phase', phase,
    'manifest', manifest_json::json
)::text
FROM package_session
WHERE manifest_json IS NOT NULL
  AND manifest_json <> ''
ORDER BY created_at;
