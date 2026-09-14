from django.conf import settings
from django.shortcuts import render


def index(request):
    return render(request, 'core/index.html', {
        'streamlit_url': settings.STREAMLIT_URL,
    })
