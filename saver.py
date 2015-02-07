from flask import Flask, request, abort, render_template, redirect, current_app, g, Response
from functools import wraps
from goose import Goose
from jinja2 import evalcontextfilter, Markup, escape
from rhine.instances import instantiate
from rhine.functions import *
from rhine.datatypes import *
import csv
import requests
import unicodedata as u
import requests
import time
import datetime
import json
import re
import sqlite3
app = Flask(__name__)
api_key = 'RPDWZAPKKKZVIZGNQFWCZAYBE'

def create_db():
	conn = sqlite3.connect('db.sqlite')
	c = conn.cursor()
	for s in open('schema.sql').read().split(';'): c.execute(s)
	conn.commit()

# --------------------------------------- FLASK STUFF ---------------------------------------

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
@app.template_filter()
@evalcontextfilter
def nl2div(eval_ctx, value):
    result = u'\n\n'.join(u'<div>%s</div>' % p \
        for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result

rhine_url = 'http://api.rhine.io/a/'
swal_response = 'swal("Extracted Entities:", "%s")'
datab = 'database.csv'

def ssl_required(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_app.config.get("SSL"):
            if request.is_secure:
                return fn(*args, **kwargs)
            else:
                return redirect(request.url.replace("http://", "https://"))
        return fn(*args, **kwargs)
    return decorated_view

def get_db():
    '''these two functions are just to let flask connect to the database
    '''
    db = getattr(g, '_database', None)
    if db is None: db = g._database = sqlite3.connect('db.sqlite')
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()

success = lambda x: json.dumps({'Success' : x})
failure = lambda x: json.dumps({'Failure' : x})


# ----------------------------------- AUTHENTICATION  ---------------------------------------

def check_auth(username, password):
	c = get_db().cursor()
	return (c.execute("SELECT * FROM users WHERE email='{0}' AND password='{1}'".format(request.authorization.username, request.authorization.password)).fetchone() != None)

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ----------------------------------- END FLASK STUFF ---------------------------------------

@app.route('/new_user', methods=['POST'])
def new_user():
	c = get_db().cursor()
	data = json.loads(request.form.get('data'))
	c.execute('INSERT INTO users (email, password) VALUES (?, ?)', (data['email'], data['password']))
	get_db().commit()
	return success(True)
	

@app.route('/update_note', methods=['POST'])
@requires_auth
def update_note():
	c = get_db().cursor()
	data = json.loads(request.form.get('data'))
	user_id = c.execute("SELECT id FROM users WHERE email=?", (request.authorization.username,)).fetchone()[0]

	if data['new_note']:
		if data['new_group']:
			c.execute('INSERT INTO groups (color, user_id) VALUES (?, ?)', (data['color'], user_id))
			get_db().commit()
		c.execute('INSERT INTO notes (type, title, content, group_id) VALUES (?, ?, ?, ?)',
			('note', data['title'], data['content'], c.lastrowid))
		get_db().commit()
	else:
		c.execute("UPDATE notes SET title=?, content=?, group_id=? WHERE note_id=?",
			(data['title'], data['content'], data['group_id'], data['id']))
	return success(True)

@app.route('/')
@requires_auth
def index():
	c = get_db().cursor()
	user_id = c.execute("SELECT id FROM users WHERE email=?", (request.authorization.username,)).fetchone()[0]
	# if not user_id: return abort(401)
	results = []
	# print request.form.get('data')
	# data = json.loads(request.form.get('data'))
	client = instantiate(api_key)
	query = request.args.get('search')

	if query:
		'''
		search_entity = client.run(extraction(query))
		r = c.execute('SELECT (entities) from notes WHERE user_id=?', (request.authorization.username,)).fetchall()
		runs = [distance(entity(search_entity), grouped(es)) for es in r]
		client.pipeline(runs)
		'''
		pass
		# USE RHINE HERE
	else:
		for group in c.execute("SELECT id FROM groups WHERE user_id=?", (request.authorization.username,)).fetchall():
			results.append([{
				'id' 		: n[0],
				'title' 	: n[1],
				'content' 	: n[2],
				'type' 		: n[3],
				'url' 		: n[4],
				'image' 	: n[5]}
				for n in c.execute("SELECT (id, title, content, type, url, image) FROM notes where group_id=?", (group_id,))])
	return render_template('index.html', query=query, results=results)

@app.route('/scan')
@ssl_required
@requires_auth
def scan():
	c = get_db().cursor()
	user_id = c.execute("SELECT id FROM users WHERE email=?", (request.authorization.username,)).fetchone()[0]
	
	url = request.args.get('url')
	title = request.args.get('name')
	entities = c.execute("SELECT entities FROM notes WHERE url=?", (url,))
	if entities == None:
		# then find them
		g = Goose()
		html 	= requests.get(n['url']).text
		article = g.extract(raw_html = html)
		content = u.normalize('NFKD', article.cleaned_text).encode('ascii','ignore')
		title 	= article.title if len(article.title) > 0 else n['title']
		image 	= str(article.top_image.src) if len(article.top_image.src) > 0 else ''

		client = instantiate(api_key)
		entities = client.run(extraction(article(url)))
		
		print '\nTITLE: %s' % title
		print 'IMAGE: %s' % image
		print 'TEXT LENGTH: %s' % len(content)
		print 'ENTITIES: %s' % entities

		c.execute("INSERT INTO groups (color, user_id) VALUES (?, ?)", ('item-white', user_id))
		get_db().commit()
		c.execute("INSERT INTO notes (type, title, url, image, content, entities, group_id) \
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
			('article', title, url, image, content, entities, cursor.lastrowid))
		get_db().commit()
	return swal_response % (', '.join((s.replace('_', '') for s in entities)))

if __name__ == "__main__":
    # app.run(debug=True, host="127.0.0.1")
    app.run(debug=True, host="0.0.0.0")
