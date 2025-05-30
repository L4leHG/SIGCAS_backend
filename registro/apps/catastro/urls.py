from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
     PredioDetalleAPIView, PredioPreView,
    RadicadoView, RadicadoUpdateView, RadicadoListView,
    RadicadoPredioAsignadoCreateView, RadicadoPredioAsignadoUpdateView, UserListView,
 ######******DOMINIOS
    DominiosPredioView, DominiosInteresadoView, DominiosFuenteAdministrativaView, DominiosUnidadConstruccionView,
    UnidadAdministrativaBasicaTipoView, EstadoAsignacionView, MutacionTipoView,
)

urlpatterns = [
    ###############***********ENDPOINTS DE CONSULTA 

    ##Detalle Predio
    path('detalle_predios/', PredioDetalleAPIView.as_view(), name='predio-lista-detalle'),
    ##Previzualición de la información del Predio
    path('preview_predios/', PredioPreView.as_view(), name='predio-preview'),


    ###############***********ENDPOINTS DE RADICADO
    ## Crear Radicado
    path('radicado/', RadicadoView.as_view(), name='radicado'),
    ## Editar Radicado
    path('api/radicado/<int:id>/editar/', RadicadoUpdateView.as_view(), name='editar_radicado'),
    ##Lista Radicados y detalle de un radicado
    path('api/radicado/lista/', RadicadoListView.as_view(), name='listar_radicados'),
    ##Crear asignación de radicado a predio
    path('api/radicado/asignar/', RadicadoPredioAsignadoCreateView.as_view(), name='asignar_radicado'),
    ##Editar asignación de radicado a predio
    path('api/radicado/editar_asignacion/<int:id>/', RadicadoPredioAsignadoUpdateView.as_view(), name='editar_asignacion_radicado'),
    ##Detalle de un radicado
    # path('api/radicado/detalle/<int:id>/', RadicadoDetailView.as_view(), name='detalle_radicado'),

    
    

    ###############***********ENDPOINTS DE USUARIOS
    path('api/usuarios/', UserListView.as_view(), name='listar_usuarios'),


    ###############***********ENDPOINTS DE DOMINIOS 
    path('api/dominios/predio/', DominiosPredioView.as_view(), name='dominios_predio'),
    path('api/dominios/interesado/', DominiosInteresadoView.as_view(), name='dominios_interesado'),
    path('api/dominios/fuente_administrativa-administrativa/', DominiosFuenteAdministrativaView.as_view(), name='dominios_fuente_administrativa'),
    path('api/dominios/unidad_construccion/', DominiosUnidadConstruccionView.as_view(), name='dominios_unidad_construccion'),
    path('api/dominios/unidad_administrativa_basica_tipo/', UnidadAdministrativaBasicaTipoView.as_view(), name='unidad_administrativa_basica_tipo'),
    path('api/dominios/estado-asignacion/', EstadoAsignacionView.as_view(), name='estado_asignacion'),
    path('api/dominios/mutacion_tipo/', MutacionTipoView.as_view(), name='mutacion_tipo'),
] 