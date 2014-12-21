from flask import Flask, request, abort, render_template, redirect, current_app
from goose import Goose
from functools import wraps
import csv
import requests
import unicodedata as u
import requests
import time
import datetime
import json
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

@app.route('/update_note')
def update_note():
	print request.args
	n = {}
	# n['text'] 	= u.normalize('NFKD', request.args['text']).encode('ascii','ignore')
	# n['title'] 	= u.normalize('NFKD', request.args['title']).encode('ascii','ignore')
	# n['color'] 	= u.normalize('NFKD', request.args['color']).encode('ascii','ignore')
	n['text'] 	= request.args['text']
	n['title'] 	= request.args['title']
	n['color'] 	= request.args['color']

	if request.args['isnew'] == 'true':
		n['time_created'] 	= datetime.datetime.now().isoformat().split('.')[0]
		n['filename'] 		= str(time.time()).replace('.', '')
		n['type'] = 'note'
		# save into main database
		with open(datab, 'a') as db:
			writer = csv.writer(db, delimiter='\\')
			writer.writerow((
				n['type'],
				'',
				n['title'] ,
				n['filename'],
				n['time_created'],
				'', # get entities for this handwritten note later
				'', # no image right?
				n['color'])) 
	else:
		n['filename'] = request.args['id']
		with open(datab) as db:
			reader = csv.reader(db, delimiter='\\')
			for row in reader:
				if row[3] == n['filename']:
					n['time_created'] = row[4]

		
	print n
	# write note to file
	with open('data/%s' % n['filename'] , 'w') as f:
		f.write('\n'.join([
			'---',
			'type: %s' % 'note',
			'title: %s' % n['title'],
			'date: %s' % (datetime.datetime
				.strptime(n['time_created'], "%Y-%m-%dT%H:%M:%S")
				.strftime("%b %d, %Y %I:%M %p")),
			'---\n']))
		f.write(n['text'])

	return json.dumps(n), 200


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
			print text
			results.append({
				'type' 		: row[0],
				'url' 		: row[1],
				'title' 	: row[2],
				'text'		: text,
				'filename' 	: row[3],
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
	n['color'] = 'item-white'
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
				n['entities'] = row[5].split('|')

	if not 'entities' in n:
		try:
			n['entities'] = requests.get(rhine_url + 'entity_extraction/%s' % n['text']).json()['entities']

			# print '\t' + '\n\t'.join(r['entities'])
			print 'GETTING ENTITIES...'

			n['time_created'] = datetime.datetime.now().isoformat().split('.')[0]
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
					n['image']),
					n['color'])
		except JSONDecodeError:
			pass
	
	if 'entities' in n:
		print 'ENTITIES: %s\n' % len(n['entities'])
		return swal_response % (', '.join((s.replace('_', '') for s in n['entities']))) 
	else:
		return 'oops', 200


if __name__ == "__main__":
    # app.run(debug=True, host="127.0.0.1")
    app.run(debug=True, host="0.0.0.0")
