import sqlite3, os, json
root=r'C:\Users\Clamps\.openclaw\workspace-oragorn'
db=os.path.join(root,'db','autoquant.db')
conn=sqlite3.connect(db)
cur=conn.cursor()
for tbl in ['backtest_results','research_funnel_queue','lessons']:
    try:
        c=cur.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]
        print(tbl, c)
    except Exception as e:
        print(tbl, 'ERR', e)
conn.close()
