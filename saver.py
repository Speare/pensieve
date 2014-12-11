from flask import Flask, request, abort, render_template, redirect, current_app
from goose import Goose
from functools import wraps

import requests
import unicodedata as u
import requests
import time
app = Flask(__name__)

rhine_url = 'http://api.rhine.io/a/'
swal_response = 'swal("Extracted Entities:", "%s")'

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

@app.route('/llamaz')
@ssl_required
def llamaz():
	url = request.args['url']
	name = request.args['name']

	print '%s : %s' % (url, name)
	html = requests.get(url).text

	g = Goose()
	article = g.extract(raw_html = html)
	article.cleaned_text = u.normalize('NFKD', article.cleaned_text).encode('ascii','ignore')

	print 'TITLE: %s' % article.title
	print 'IMAGE: %s' % article.top_image.src if article.top_image else "None"
	print 'TEXT LENGTH: %s' % len(article.cleaned_text)
	
	r = requests.get(rhine_url + 'entity_extraction/%s' % article.cleaned_text).json()
	print '\t' + '\n\t'.join(r['entities'])

	with open(str(time.time()).replace('.', '_'), 'w') as f:
		f.write('%s\n\n%s' % (','.join(r['entities']), article.cleaned_text))
	
	return swal_response % (', '.join((s.replace('_', ' ') for s in r['entities']))) 
	# return app.send_static_file('topbar.js')

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1")
