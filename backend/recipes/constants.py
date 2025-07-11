"""
Константы, относящиеся к предметной области «рецепты»
и используемые в разных приложениях.
"""

MIN_AMOUNT = 1
MIN_COOKING_TIME = 1


INGREDIENT_NAME_MAX_LENGTH = 128
MEASUREMENT_UNIT_MAX_LENGTH = 64
RECIPE_NAME_MAX_LENGTH = 256

COOKING_TIME_VALIDATOR_MSG = (
    f'Время должно быть не менее {MIN_COOKING_TIME} минуты'
)
INGREDIENT_AMOUNT_VALIDATOR_MSG = (
    f'Требуется хотя бы {MIN_AMOUNT} единица'
)

VERBOSE_INGREDIENT = 'Ингредиент'
VERBOSE_INGREDIENTS = 'Ингредиенты'
