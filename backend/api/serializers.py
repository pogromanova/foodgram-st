from django.db import transaction
from djoser.serializers import UserSerializer as BaseUserSerializer
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers


from api.constants import (
    MIN_AMOUNT,
    MIN_COOKING_TIME,
)
from recipes.models import (
    Recipe,
    Ingredient,
    RecipeComponent,
)
from users.models import User


class UserCreateSerializer(BaseUserCreateSerializer):
    """Сериализатор для создания пользователя."""

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'password')

    def validate(self, attrs):
        required_fields = ['email', 'username',
                           'first_name', 'last_name', 'password']
        for field in required_fields:
            if not attrs.get(field):
                raise serializers.ValidationError(
                    {field: 'Это поле обязательно.'})
        return super().validate(attrs)


class UserSerializer(BaseUserSerializer):
    """Сериализатор для пользователя."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated:
            return obj.subscribers.filter(user=user).exists()
        return False

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        return None


class RecipeShortSerializer(serializers.ModelSerializer):
    """Краткий сериализатор для рецепта."""

    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if representation['image'] and request:
            representation['image'] = request.build_absolute_uri(
                representation['image'])
        return representation


class SubscriptionSerializer(UserSerializer):
    """Сериализатор для подписки."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='authored_recipes.count', read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.authored_recipes.all()
        if limit and limit.isdigit():
            recipes = recipes[:int(limit)]
        return RecipeShortSerializer(recipes, many=True, context=self.context).data


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара пользователя."""

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def to_representation(self, instance):
        request = self.context.get('request')
        if instance.avatar and hasattr(instance.avatar, 'url'):
            return {'avatar': request.build_absolute_uri(instance.avatar.url)}
        return {'avatar': None}


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиента."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeComponentSerializer(serializers.ModelSerializer):
    """Сериализатор для компонента рецепта (чтение)."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeComponent
        fields = ('id', 'name', 'measurement_unit', 'amount')


class ComponentCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания компонента рецепта."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=MIN_AMOUNT)

    class Meta:
        model = RecipeComponent
        fields = ('id', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецепта."""

    author = UserSerializer(read_only=True)
    ingredients = RecipeComponentSerializer(
        source='components', many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and obj.in_favorites.filter(user=request.user).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and obj.in_grocery_lists.filter(user=request.user).exists())

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if representation['image'] and request:
            representation['image'] = request.build_absolute_uri(
                representation['image'])
        return representation


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецепта."""

    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    ingredients = ComponentCreateSerializer(many=True)
    image = Base64ImageField(required=True, allow_null=False)
    cooking_time = serializers.IntegerField(min_value=MIN_COOKING_TIME)

    class Meta:
        model = Recipe
        fields = ('author', 'ingredients', 'name',
                  'image', 'text', 'cooking_time')

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Необходим минимум один ингредиент')

        ingredient_ids = [item['id'].id for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться')

        return value

    def validate(self, data):
        if not data.get('ingredients'):
            raise serializers.ValidationError(
                {'ingredients': 'Это поле обязательно'})

        if not data.get('image'):
            raise serializers.ValidationError(
                {'image': 'Это поле обязательно.'})

        return data

    def create_ingredients(self, recipe, ingredients):
        """Создание ингредиентов для рецепта."""
        components = [
            RecipeComponent(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            ) for item in ingredients
        ]
        RecipeComponent.objects.bulk_create(components)

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')

        instance = super().update(instance, validated_data)

        instance.components.all().delete()
        self.create_ingredients(instance, ingredients_data)

        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data
