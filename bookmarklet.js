javascript:(function(){
	var h = 'http://localhost:5000/',
		n = document.location.href,
		r = document.title;

	var s = document.createElement('script');
	s.type = 'text/javascript';
	s.src = h + 'scan?url=' + n + '&name=' + r + '&r=' + Math.random().toString(36).substring(7);

	var a = document.createElement('script');
	a.type = 'text/javascript';
	a.src = h + 'static/js/sweet-alert.min.js';

	var b = document.createElement('link');
	b.type = 'text/css';
	b.rel = 'stylesheet';
	b.href = h + 'static/css/sweet-alert.css';

	o = document.getElementsByTagName('head')[0] || document.documentElement;
	o.appendChild(a);
	o.appendChild(b);
	o.appendChild(s);
})()

// var h = 'http://54.87.238.201:5000/',