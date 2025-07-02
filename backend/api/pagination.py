from rest_framework.pagination import PageNumberPagination

from api.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class RecipePagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = DEFAULT_PAGE_SIZE
    max_page_size = MAX_PAGE_SIZE
