import json

from django.http import HttpResponse


def json_response(data):
    content = json.dumps(data)
    return HttpResponse(content, mimetype='application/json')
