from django.conf import settings
from django.shortcuts import redirect
from django.shortcuts import render


def profile(request):
    return redirect(request.user.get_profile().get_node().permalink())


def login(request):
    template = 'sboard/login.html'
    return render(request, template, {'settings': settings})
