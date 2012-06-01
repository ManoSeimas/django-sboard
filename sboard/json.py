from django.http import HttpResponse
from django.utils import simplejson


def json_response(data):
    content = simplejson.dumps(data)
    return HttpResponse(content, mimetype='application/json')
