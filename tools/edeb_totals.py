"""Aggregate candidates from the observed EDEB schema, never a production reader.

Caller supplies a connection to a private snapshot. No names/locations are read.
"""

REQUIRED = {
    'StarSystem': {'Id', 'IsTripHistory'},
    'Body': {'StarSystemId', 'CartographicValue', 'WasReadFromJournal'},
    'Genus': {'StarSystemId', 'VistaGenomicsValue', 'AnalysisComplete'},
}


def aggregate(connection, table, field, scope, condition='1=1'):
    # Identifiers/conditions are exclusively internal constants, not user input.
    row = connection.execute(f'''
        SELECT COUNT(*), COALESCE(SUM(t."{field}"), 0),
               COUNT(*) - COUNT(t."{field}"),
               COALESCE(SUM(CASE WHEN t."{field}" IS NOT NULL AND
                    (typeof(t."{field}") != 'integer' OR t."{field}" < 0)
                    THEN 1 ELSE 0 END), 0)
        FROM "{table}" t
        WHERE ({condition}) AND EXISTS (
            SELECT 1 FROM StarSystem s
            WHERE s.Id = t.StarSystemId AND ({scope})
        )
    ''').fetchone()
    return dict(zip(('rows', 'sum', 'null_values', 'invalid_values'), row))


def compare_totals(connection, expected=None):
    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {}
    for table, required in REQUIRED.items():
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')} if table in tables else set()
        if required - columns:
            missing[table] = sorted(required - columns)
    if missing:
        return {'status': 'unsupported_schema', 'missing_columns': missing}

    result = {
        'status': 'diagnostic_only',
        'note': 'Candidate sums, not verified EDEB calculation or reset semantics. NULLs contribute zero and are counted explicitly.',
        'trip_flag_counts': [list(row) for row in connection.execute(
            'SELECT IsTripHistory, COUNT(*) FROM StarSystem GROUP BY IsTripHistory')],
        'orphan_rows': {},
        'scopes': {},
    }
    for table in ('Body', 'Genus'):
        result['orphan_rows'][table] = connection.execute(f'''
            SELECT COUNT(*) FROM "{table}" t WHERE NOT EXISTS (
                SELECT 1 FROM StarSystem s WHERE s.Id = t.StarSystemId)
        ''').fetchone()[0]
    for name, scope in [('trip_flag_1', 's.IsTripHistory = 1'),
                        ('all_systems', '1=1'),
                        ('trip_flag_0', 's.IsTripHistory = 0')]:
        cartography = {
            'all_bodies': aggregate(connection, 'Body', 'CartographicValue', scope),
            'journal_bodies': aggregate(connection, 'Body', 'CartographicValue', scope, 't.WasReadFromJournal = 1'),
        }
        biology = {
            'all_genera': aggregate(connection, 'Genus', 'VistaGenomicsValue', scope),
            'completed_genera': aggregate(connection, 'Genus', 'VistaGenomicsValue', scope, 't.AnalysisComplete = 1'),
        }
        candidates = {}
        for cart_name, cart in cartography.items():
            for bio_name, bio in biology.items():
                total = cart['sum'] + bio['sum']
                item = {'value': total, 'invalid_values': cart['invalid_values'] + bio['invalid_values']}
                if expected:
                    item['difference_from_displayed_trip'] = total - expected['trip']
                    item['difference_from_displayed_history'] = total - expected['history']
                candidates[cart_name + '+' + bio_name] = item
        result['scopes'][name] = {'cartography': cartography, 'biology': biology, 'candidates': candidates}
    if expected:
        result['displayed_values'] = expected
        result['matching_pairs'] = []
        for candidate, trip in result['scopes']['trip_flag_1']['candidates'].items():
            history = result['scopes']['all_systems']['candidates'][candidate]
            if (trip['value'] == expected['trip'] and history['value'] == expected['history']
                    and trip['invalid_values'] == history['invalid_values'] == 0):
                result['matching_pairs'].append(candidate)
        result['match_note'] = 'A matching pair is evidence for this snapshot only; it does not activate the sender.'
    return result
