from rest_framework import pagination

class TableAtributosPagination(pagination.PageNumberPagination):
    page_size = 10  # Cantidad de elementos por página
    page_size_query_param = 'page_size'  # Permite al cliente especificar la cantidad de elementos por página
    max_page_size = 100  # Máximo número de elementos por página

class ListPrediosPagination(pagination.PageNumberPagination):
    page_size = 100  # Cantidad de elementos por página
    page_size_query_param = 'page_size'  # Permite al cliente especificar la cantidad de elementos por página
    max_page_size = 100  # Máximo número de elementos por página

class SearchTableAtributosPagination(pagination.PageNumberPagination):
    page_size = 10  # Cantidad de elementos por página
    page_size_query_param = 'page_size'  # Permite al cliente especificar la cantidad de elementos por página
    max_page_size = 100  # Máximo número de elementos por página
