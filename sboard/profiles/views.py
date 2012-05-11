from django.conf import settings
from django.shortcuts import redirect
from django.shortcuts import render


def profile(request):
    profile = request.user.get_profile()
    node = profile.get_node()
    return redirect(node.permalink())


def login(request):
    template = 'sboard/login.html'
    return render(request, template, {'settings': settings})
