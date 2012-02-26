from django.conf import settings
from django.shortcuts import render


def profile(request):
    template = 'sboard/profile.html'
    return render(request, template)


def login(request):
    template = 'sboard/login.html'
    return render(request, template, {'settings': settings})
