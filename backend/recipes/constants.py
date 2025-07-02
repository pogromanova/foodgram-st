"""
Единая точка, где хранятся все «магические» числа/строки,
использующиеся в моделях и сериализаторах.
"""

# ───── CharField lengths ────────────────────────────────────────────────────
INGREDIENT_NAME_MAX_LENGTH = 128
MEASUREMENT_UNIT_MAX_LENGTH = 64
RECIPE_NAME_MAX_LENGTH = 256

# ───── Min/Max значения для числовых полей ‒ и их сообщения ────────────────
MIN_COOKING_TIME_MINUTES = 1
COOKING_TIME_VALIDATOR_MSG = (
    f"Время должно быть не менее {MIN_COOKING_TIME_MINUTES} минуты"
)

MIN_INGREDIENT_AMOUNT = 1
INGREDIENT_AMOUNT_VALIDATOR_MSG = (
    f"Требуется хотя бы {MIN_INGREDIENT_AMOUNT} единица"
)

# ───── Строки для verbose_name и пр. (по желанию) ───────────────────────────
# Например:
VERBOSE_INGREDIENT = "Ингредиент"
VERBOSE_INGREDIENTS = "Ингредиенты"
