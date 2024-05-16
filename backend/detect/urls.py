from django.urls import path
from .views import detect

urlpatterns = [
    path('detect/', detect, name='detect'),
]
