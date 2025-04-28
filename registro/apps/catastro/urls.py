from django.urls import path
from .views import SaludoCatastroView,PredioListView

urlpatterns = [
    path('saludo_catastro', SaludoCatastroView.as_view(), name='saludo_catastro'),
     path('predios/', PredioListView.as_view(), name='predio-list'),
] 