import sqlite3, json
conn = sqlite3.connect(r'C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db')
cur = conn.cursor()
cols = [r[1] for r in cur.execute('PRAGMA table_info(backtest_results)')]
need = ['strategy_family','parent_id','mutation_type','stage','validation_target','family_generation','killed','regime_scores','regime_concentration','primary_regime','portability_score','refinement_status','refinement_round','weakness_profile']
missing = [c for c in need if c not in cols]
exists = [c for c in need if c in cols]
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print(json.dumps({'backtest_results_exists': 'backtest_results' in tables, 'existing': exists, 'missing': missing, 'research_funnel_queue': 'research_funnel_queue' in tables, 'mechanism_priors': 'mechanism_priors' in tables}, indent=2))
conn.close()
