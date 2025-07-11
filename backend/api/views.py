from datetime import datetime
from io import BytesIO
import hashlib
import base64

from django.db.models import Sum
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS, AllowAny
from rest_framework.response import Response

from recipes.models import (
    Recipe,
    Ingredient,
    RecipeComponent,
    UserFavorite,
    GroceryList
)
from users.models import User, Subscription
from .serializers import (
    UserSerializer,
    SubscriptionSerializer,
    AvatarSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeCreateSerializer,
    RecipeShortSerializer
)
from .permissions import IsAuthorOrReadOnly
from .pagination import RecipePagination
from .filters import IngredientFilter, RecipeFilter


class UserViewSet(DjoserUserViewSet):
    """ViewSet для работы с пользователями."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = RecipePagination

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        """Подписка/отписка на/от автора."""
        author = self.get_object()
        user = request.user

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription, created = Subscription.objects.get_or_create(
                user=user, author=author
            )
            if not created:
                return Response(
                    {'errors': f'Вы уже подписаны на пользователя {author.username}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = SubscriptionSerializer(
                author, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = Subscription.objects.filter(user=user, author=author)
        if subscription.exists():
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {'errors': f'Вы не подписаны на пользователя {author.username}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Список подписок пользователя."""
        user = request.user
        subscriptions = User.objects.filter(
            subscribers__user=user
        ).prefetch_related('recipes', 'subscribers')

        page = self.paginate_queryset(subscriptions)
        serializer = SubscriptionSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=['put', 'delete'],
        detail=False,
        url_path='me/avatar',
        permission_classes=[IsAuthenticated]
    )
    def avatar(self, request):
        """Управление аватаром пользователя."""
        if request.method == 'PUT':
            serializer = AvatarSerializer(
                instance=request.user,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        user = request.user
        if user.avatar:
            user.avatar.delete()
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        """Динамические разрешения в зависимости от действия."""
        if self.action == 'retrieve':
            return [AllowAny()]
        if self.action in ['me', 'subscribe', 'subscriptions', 'avatar']:
            return [IsAuthenticated()]
        return super().get_permissions()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для работы с ингредиентами (только чтение)."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    permission_classes = (AllowAny,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с рецептами."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = RecipePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        """Оптимизированный queryset с prefetch_related."""
        return Recipe.objects.select_related('author').prefetch_related(
            'components__ingredient'
        )

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от типа запроса."""
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        """Сохранение рецепта с указанием автора."""
        serializer.save(author=self.request.user)

    def _handle_favorite_or_shopping_cart(self, request, pk, model_class):
        """Универсальный метод для работы с избранным и списком покупок."""
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        verbose_name = model_class._meta.verbose_name

        if request.method == 'POST':
            obj, created = model_class.objects.get_or_create(
                user=user, recipe=recipe
            )
            if not created:
                return Response(
                    {'errors': f'Рецепт «{recipe.name}» уже в {verbose_name}!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = RecipeShortSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        qs = model_class.objects.filter(user=user, recipe=recipe)
        if qs.exists():
            qs.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {'errors': f'Рецепт не был добавлен в {verbose_name}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в/из избранного."""
        return self._handle_favorite_or_shopping_cart(request, pk, UserFavorite)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в/из списка покупок."""
        return self._handle_favorite_or_shopping_cart(request, pk, GroceryList)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в виде текстового файла."""
        user = request.user

        ingredients = RecipeComponent.objects.filter(
            recipe__in_grocery_lists__user=user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount')).order_by('ingredient__name')

        recipes = Recipe.objects.filter(
            in_grocery_lists__user=user
        ).select_related('author')

        current_date = datetime.now().strftime('%d.%m.%Y')

        shopping_list_content = self._generate_shopping_list_content(
            current_date, ingredients, recipes
        )

        response = FileResponse(
            BytesIO(shopping_list_content.encode('utf-8')),
            content_type='text/plain; charset=utf-8',
            filename='shopping_cart.txt'
        )
        return response

    def _generate_shopping_list_content(self, date, ingredients, recipes):
        """Генерация содержимого списка покупок."""
        content_parts = [
            f'Список покупок от {date}',
            '',
            'Продукты:',
        ]

        for i, item in enumerate(ingredients, 1):
            ingredient_line = (
                f'{i}. {item["ingredient__name"].capitalize()} '
                f'({item["ingredient__measurement_unit"]}) — {item["total_amount"]}'
            )
            content_parts.append(ingredient_line)

        content_parts.extend(['', 'Рецепты:'])

        for recipe in recipes:
            author_name = recipe.author.get_full_name() or recipe.author.username
            recipe_line = f'• {recipe.name} (автор: {author_name})'
            content_parts.append(recipe_line)

        return '\n'.join(content_parts)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        data_to_hash = f"{recipe.id}_{datetime.now().timestamp()}"
        short_code = base64.urlsafe_b64encode(hashlib.sha256(
            data_to_hash.encode()).digest())[:8].decode()

        short_url = f"{request.build_absolute_uri('/').rstrip('/')}/s/{short_code}"
        return Response({'short-link': short_url})
    # Вроде бы добавила работу с короткой ссылкой...
