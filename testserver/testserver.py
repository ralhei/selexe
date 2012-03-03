#!/usr/bin/env python
"""
Web application server for testing selexe
"""
from bottle import route, run, request

HTML_SKEL = """<html>
    <body>
    %s
    </body>
</html>
"""


@route('/static/:name')
def static_page(name):
    return open(name+'.html').read()


@route('/post', method='POST')
def post():
    "Accept any kind of POSTing, render all form fields into SPAN elements with 'id' set to the form field name"
    res = [ '<h1>POST results</h1>']
    for field in request.forms:
        res.append('%s: <span id="%s">%s</span><br/>' % (field, field, request.forms[field]))
    return HTML_SKEL % '\n'.join(res)


if __name__ == '__main__':
    run(host='localhost', port=8080)
