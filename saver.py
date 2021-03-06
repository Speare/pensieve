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
import twilio.twiml
app = Flask(__name__)

api_key = open('key').read()
rhine_url = 'http://api.rhine.io/a/'
swal_response = 'swal("Extracted Entities:", "%s")'
imgexts = ('.tif','.tiff','.gif','.jpeg','.jpg','.jif','.png')

# --------------------------------------- FLASK STUFF ---------------------------------------

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
@app.template_filter()
@evalcontextfilter
def nl2div(eval_ctx, value):
    '''Converts newlines into <p> and <br />s.'''
    value = re.sub(r'\r\n|\r|\n', '\n', value)
    paras = re.split('\n{2,}', value)
    paras = [u'<p>%s</p>' % p.replace('\n', '<br />') for p in paras]
    paras = u'\n\n'.join(paras)
    return Markup(paras)
    # result = u'\n\n'.join(u'<div>%s</div>' % p \
    #     for p in _paragraph_re.split(escape(value)))
    # if eval_ctx.autoescape:
    #     result = Markup(result)
    # return result


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

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return Response(
            'Could not verify your access level for that URL.\n'
            'You have to login with proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'})
        elif not check_auth(auth.username, auth.password):
            return redirect('/signup')
        return f(*args, **kwargs)
    return decorated

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/api/newuser', methods=['POST'])
def newuser():
    c = get_db().cursor()
    data = json.loads(request.form.get('data'))
    c.execute('INSERT INTO users (email, password) VALUES (?, ?)', (data['email'], data['password']))
    get_db().commit()
    return success(True)


# ----------------------------------- END FLASK STUFF ---------------------------------------


def search_db(c, query, user_id):
    client = instantiate(api_key)
    print query
    # transform to flat list of requests so we can pipeline
    res = c.execute('SELECT entities, group_id, title FROM notes WHERE user_id=?', (user_id,)).fetchall()
    runs = []
    for re in res: 
        runs.extend([(distance(entity(query), entity(e['entity'])), e['relevance'], re[1], re[2]) \
            for e in json.loads(re[0])])

    # run pipelined
    dists = client.pipeline([run[0] for run in runs])
    print '\n'.join(['{0}\t{1}\t{2}'.format(d, runs[i][1], runs[i][0]) for i, d in enumerate(dists)])
    
    # transform back into groups based on group_id
    gr_dists = [[
        [d * (1 - runs[i][1]) for i, d in enumerate(dists) if runs[i][2] == re[1] and d != None],
        re[1],
        re[2],
        ] for re in res]
    # calculate weighted scores
    gr_dists = [gr + [sum(gr[0]) / float(len(gr[0])) if gr[0] else 100,] for gr in gr_dists]
    gr_dists = sorted(gr_dists, key=lambda gr: gr[3])
    print '\n'.join([str(p) for p in gr_dists])
    print '\n'.join(['{0}\t{1}'.format(sum(gr[0]) / float(len(gr[0])) if gr[0] else 100, gr[2]) for gr in gr_dists])
    
    # also get plaintext matches
    # plainsearch = [g[0] for g in c.execute('SELECT group_id FROM notesearch WHERE content MATCH (?)', (query,)).fetchall()]
    plainsearch = []
    groups = [gr[1] for gr in gr_dists if gr[1] not in plainsearch and gr[3] < 40]

    return plainsearch, groups

def import_link(c, url, user_id):
    '''extract an article and import it'''
    client = instantiate(api_key)

    entities = c.execute("SELECT entities FROM notes WHERE url=?", (url,)).fetchone()
    # brand new
    if not entities:
        c.execute("INSERT INTO groups (user_id) VALUES (?)", (user_id,))
        print c.lastrowid
        if any((url.endswith(ext) for ext in imgexts)):
            # image extraction
            entities = client.run(extraction(image.fromurl(url)))
            print 'IMAGE: {0}'.format(url)
            c.execute("INSERT INTO notes (color, type, title, url, image, content, entities, group_id, user_id) \
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                ('item-white', 'image', '', url, url, '', json.dumps(entities), c.lastrowid, user_id))
        else:
            # text extraction
            g       = Goose()
            html    = requests.get(url).text
            ea      = g.extract(raw_html = html)
            content = u.normalize('NFKD', ea.cleaned_text).encode('ascii','ignore')
            title   = u.normalize('NFKD', ea.title).encode('ascii', 'ignore') if len(ea.title) > 0 else ''
            try: img = str(ea.top_image.src) if len(ea.top_image.src) > 0 else ''
            except: img = ''
            entities = client.run(extraction(text(content)))
            
            print 'TITLE: {0}\nLENGTH: {1}\nENTITIES: {2}'.format(title, len(content), entities)
            c.execute("INSERT INTO notes (color, type, title, url, image, content, entities, group_id, user_id) \
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                ('item-white', 'article', title, url, img, content, json.dumps(entities), c.lastrowid, user_id))
        get_db().commit()
    # if already scanned
    else:
        entities = json.loads(entities[0])
    return entities

# ---------------------------------------- ENDPOINTS --------------------------------------------

@app.route('/scan')
@ssl_required
@requires_auth
def scan():
    c = get_db().cursor()
    user_id = c.execute("SELECT id FROM users WHERE email=?", (request.authorization.username,)).fetchone()[0]
    url = request.args.get('url')
    title = request.args.get('name')
    entities = import_link(c, url, user_id)
    
    return swal_response % (', '.join((s['entity'].replace('_', '') for s in entities)))

@app.route('/tcallback', methods=['GET', 'POST'])
def twillio_callback():
    c = get_db().cursor()
    msg = request.values.get('Body')
    num = request.values.get('From')
    user_id = c.execute('SELECT id FROM users WHERE phone_num=?', ('+6143903969',)).fetchone()[0]
    reply = ''
    
    if user_id:
        if msg.startswith('http'):
            # extract the artice
            entities = import_link(c, msg, user_id)
            print 'msg: {0}\nnum: {1}'.format(msg, num)
            reply = 'Sure, that article is about:\n' + ', '.join([e.get('entity') for e in entities])
        elif msg.lower().strip().startswith('fetch'):
            query = ' '.join(msg.split()[1:]).lower().strip()
            plainsearch, groups = search_db(c, query, user_id)
            searches = plainsearch[0] if plainsearch else [] + groups[0] if groups else []
            if searches:
                reply = c.executemany('SELECT title, url FROM notes WHERE group_id=?', searches)
            else:
                reply = "Sorry, I couldn't find anything about that."
    else:
        reply = "Sorry, couldn't recognize your phone number. Please sign up first."
    resp = twilio.twiml.Response()
    resp.message(reply)
    print 'SMS Reply: {0}'.format(reply)
    return str(resp)


@app.route('/update_note', methods=['POST'])
@requires_auth
def update_note():
    c = get_db().cursor()
    data = json.loads(request.form.get('data'))
    user_id = c.execute("SELECT id FROM users WHERE email=?", (request.authorization.username,)).fetchone()[0]
    
    client = instantiate(api_key)
    entities = client.run(extraction(text(data['content'])))
    print data
    print entities
    if data['new_note']:
        # if data['new_group']:
        c.execute('INSERT INTO groups (user_id) VALUES (?)', (user_id,))
        get_db().commit()
        gid = c.lastrowid
        
        c.execute("INSERT INTO notes (color, type, title, url, image, content, entities, group_id, user_id) \
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            (data['color'], 'note', data['title'], data['url'], data['image'], data['content'], json.dumps(entities), gid, user_id))
        c.execute("INSERT INTO notesearch (id, group_id, title, content) VALUES (?, ?, ?, ?)", (c.lastrowid, gid, data['title'], data['content']))
    else:
        print data['title'], data['color']
        # print data['id']
        c.execute("UPDATE notes SET title=?, content=?, color=?, entities=? WHERE id=?",
            (data['title'], data['content'], data['color'], json.dumps(entities), data['id']))
        c.execute("UPDATE notesearch SET title=?, content=? WHERE id=?", (data['title'], data['content'], c.lastrowid))
    get_db().commit()
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
    query = request.args.get('search')
    plainsearch, groups = [], []
    if query:
        plainsearch, groups = search_db(c, query, user_id)
    else:
        groups = [g[0] for g in c.execute("SELECT id FROM groups WHERE user_id=?", (user_id,)).fetchall()]
    for group in plainsearch + groups:
        print group
        results.append([
            { k : n[i] for i, k in enumerate(('id', 'title', 'content', 'type', 'url', 'image', 'color'))}
            for n in c.execute("SELECT id, title, content, type, url, image, color FROM notes WHERE group_id=?", (group,))])
    return render_template('index.html', query=query, results=results)


if __name__ == "__main__":
    # app.run(debug=True, host="127.0.0.1")
    app.run(debug=True, host="0.0.0.0")
