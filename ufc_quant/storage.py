import sqlite3, json
DB="ufc_predictions.sqlite"
def initialize(path=DB):
    con=sqlite3.connect(path)
    con.execute("""CREATE TABLE IF NOT EXISTS predictions(
      id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      event TEXT, fighter_a TEXT, fighter_b TEXT, payload TEXT)""")
    con.commit(); con.close()
def save(event,a,b,payload,path=DB):
    con=sqlite3.connect(path)
    con.execute("INSERT INTO predictions(event,fighter_a,fighter_b,payload) VALUES(?,?,?,?)",
                (event,a,b,json.dumps(payload)))
    con.commit(); con.close()
