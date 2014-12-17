from flask import Flask, request, abort, render_template, redirect, current_app
from goose import Goose
from functools import wraps
import csv
import requests
import unicodedata as u
import requests
import time
import datetime
app = Flask(__name__)

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

def read_note(filename):
	with open('data/%s' % filename) as f:
		text = '\n'.join(f.readlines())
		text = text.split('---\n')[2]
		
		return text.split('\n\n')[0]

@app.route('/')
def index():
	results = []
	query = None
	if 'search' in request.args:
		query = request.args['search']
	# 	results.append(query)
	entities = None

	with open(datab) as db:
		reader = csv.reader(db, delimiter='\\')

		for row in reader:
			text = read_note(row[3])
			results.append({
				'url' 		: row[1],
				'title' 	: row[2],
				'text'		: text,
				'iso_time' 	: row[4], # converting iso to readble
				'str_time' 	: (datetime.datetime
					.strptime(row[4], "%Y-%m-%dT%H:%M:%S")
					.strftime("%b %d, %Y %I:%M %p")),
				'entities' 	: row[5],
				'image' 	: row[6],
			})
	return render_template('index.html', query=query, results=results)



@app.route('/llamaz')
@ssl_required
def llamaz():
	n = {}
	n['type'] = 'article'
	n['url'] = request.args['url']
	n['title'] = request.args['name']

	# analyze the text of url given
	print '%s : %s' % (n['url'], n['title'])
	g = Goose()
	html = requests.get(n['url']).text
	article = g.extract(raw_html = html)
	n['text'] = u.normalize('NFKD', article.cleaned_text).encode('ascii','ignore')
	n['title'] = article.title if len(article.title) > 0 else n['title']
	n['image'] = str(article.top_image.src) if len(article.top_image.src) > 0 else ''

	print '\nTITLE: %s' % n['title']
	print 'IMAGE: %s' % n['image']
	print 'TEXT LENGTH: %s' % len(n['text'])
	

	# save article data to fil
	with open(datab) as f:
		reader = csv.reader(f, delimiter='\\')
		for row in reader:
			if row[1] == n['url']:
				n['entities'] = row[4].split('|')

	if not 'entities' in n:
		n['entities'] = requests.get(rhine_url + 'entity_extraction/%s' % n['text']).json()['entities']
		# print '\t' + '\n\t'.join(r['entities'])
		print 'GETTING ENTITIES...'

		n['time_created'] = datetime.datetime.now().isoformat().split('.')[0]
		print n['time_created'] 
		n['filename'] = str(time.time()).replace('.', '')

		# write note to file
		with open('data/%s' % n['filename'] , 'w') as f:
			f.write('\n'.join([
				'---',
				'type: %s' % 'article',
				'title: %s' % n['title'],
				'source: %s' % n['url'],
				'date: %s' % (datetime.datetime
					.strptime(n['time_created'], "%Y-%m-%dT%H:%M:%S")
					.strftime("%b %d, %Y %I:%M %p")),
				'---\n']))
			
			f.write(n['text'])

		# save new note in database
		with open(datab, 'a') as f:
			writer = csv.writer(f, delimiter='\\')
			writer.writerow((
				n['type'],
				n['url'] ,
				n['title'] ,
				n['filename'],
				n['time_created'],
				('|'.join(n['entities'])),
				n['image']),)

	print 'ENTITIES: %s\n' % len(n['entities'])
	return swal_response % (', '.join((s.replace('_', '') for s in n['entities']))) 
	# return app.send_static_file('topbar.js')


if __name__ == "__main__":
    # app.run(debug=True, host="127.0.0.1")
    app.run(debug=True, host="0.0.0.0")
