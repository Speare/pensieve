#!/usr/bin/python
import sqlite3
import os
os.remove('db.sqlite')
conn = sqlite3.connect('db.sqlite')
c = conn.cursor()
for s in open('schema.sql').read().split(';'): c.execute(s)
# conn.commit()