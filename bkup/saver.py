from flask import Flask
from flask import request
from flask import abort
from flask import render_template
import requests
app = Flask(__name__)

@app.route('/llamaz')
def llamaz():
	url = request.args['url']
	loc = request.args['loc']

	response = request.get(url)
	print request

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1")
