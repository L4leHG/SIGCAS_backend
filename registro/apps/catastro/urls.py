from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SaludoCatastroView, PredioListView, PredioDetalleAPIView, PredioPreView,
    RadicadoView
    # EstadoAsignacionViewSet, MutacionTipoViewSet,
    # DocumentoTipoViewSet, InteresadoTipoViewSet,
    # UsuarioViewSet
)


urlpatterns = [
    path('saludo_catastro', SaludoCatastroView.as_view(), name='saludo_catastro'),
    path('predios/', PredioListView.as_view(), name='predio-list'),
    path('detalle_predios/', PredioDetalleAPIView.as_view(), name='predio-lista-detalle'),
    path('radicado/', RadicadoView.as_view(), name='radicado'),
    path('preview_predios/', PredioPreView.as_view(), name='predio-preview'),
] 