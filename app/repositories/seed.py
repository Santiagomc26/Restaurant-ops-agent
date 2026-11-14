import logging
from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import ProductCategory, UnitOfMeasure
from app.domain.models import Ingredient, Product, RecipeItem
from app.repositories.interfaces import UnitOfWork

logger = logging.getLogger(__name__)

G, ML, UN = UnitOfMeasure.GRAM, UnitOfMeasure.MILLILITER, UnitOfMeasure.UNIT


@dataclass(frozen=True)
class IngredientSeed:
    name: str
    unit: UnitOfMeasure
    stock: str
    reorder_level: str
    unit_cost: str


@dataclass(frozen=True)
class ProductSeed:
    sku: str
    name: str
    category: ProductCategory
    price: int
    description: str
    recipe: dict[str, str]


INGREDIENTS: list[IngredientSeed] = [
    IngredientSeed("Pan de hamburguesa", UN, "120", "30", "900"),
    IngredientSeed("Carne de hamburguesa 150 g", UN, "100", "25", "4500"),
    IngredientSeed("Queso tajado", UN, "200", "50", "600"),
    IngredientSeed("Tocineta", G, "3000", "800", "45"),
    IngredientSeed("Lechuga", G, "3000", "800", "8"),
    IngredientSeed("Tomate", G, "4000", "1000", "6"),
    IngredientSeed("Cebolla", G, "3000", "800", "5"),
    IngredientSeed("Salsa de la casa", ML, "5000", "1500", "12"),
    IngredientSeed("Pan de perro", UN, "100", "25", "700"),
    IngredientSeed("Salchicha americana", UN, "120", "30", "1800"),
    IngredientSeed("Papa a la francesa", G, "15000", "4000", "9"),
    IngredientSeed("Papitas ripio", G, "3000", "800", "20"),
    IngredientSeed("Gaseosa 400 ml", UN, "96", "24", "2200"),
    IngredientSeed("Limón", UN, "150", "40", "300"),
    IngredientSeed("Azúcar", G, "5000", "1000", "4"),
]

_CLASSIC_BURGER = {
    "Pan de hamburguesa": "1",
    "Carne de hamburguesa 150 g": "1",
    "Queso tajado": "1",
    "Lechuga": "30",
    "Tomate": "40",
    "Cebolla": "20",
    "Salsa de la casa": "30",
}
_FRIES = {"Papa a la francesa": "200", "Salsa de la casa": "20"}
_SODA = {"Gaseosa 400 ml": "1"}


def _combine(*recipes: dict[str, str]) -> dict[str, str]:
    combined: dict[str, Decimal] = {}
    for recipe in recipes:
        for name, qty in recipe.items():
            combined[name] = combined.get(name, Decimal("0")) + Decimal(qty)
    return {name: str(qty) for name, qty in combined.items()}


PRODUCTS: list[ProductSeed] = [
    ProductSeed(
        "HAM-CLA",
        "Hamburguesa clásica",
        ProductCategory.BURGERS,
        18000,
        "Carne de res, queso, lechuga, tomate, cebolla y salsa de la casa",
        _CLASSIC_BURGER,
    ),
    ProductSeed(
        "HAM-DOB",
        "Hamburguesa doble",
        ProductCategory.BURGERS,
        26000,
        "Doble carne y doble queso",
        _combine(
            _CLASSIC_BURGER,
            {"Carne de hamburguesa 150 g": "1", "Queso tajado": "1", "Salsa de la casa": "10"},
        ),
    ),
    ProductSeed(
        "HAM-TOC",
        "Hamburguesa con tocineta",
        ProductCategory.BURGERS,
        23000,
        "Clásica con tocineta crocante",
        _combine(_CLASSIC_BURGER, {"Tocineta": "40"}),
    ),
    ProductSeed(
        "PER-SEN",
        "Perro sencillo",
        ProductCategory.HOT_DOGS,
        12000,
        "Salchicha americana, cebolla, papitas ripio y salsa",
        {
            "Pan de perro": "1",
            "Salchicha americana": "1",
            "Cebolla": "20",
            "Papitas ripio": "25",
            "Salsa de la casa": "30",
        },
    ),
    ProductSeed(
        "PER-ESP",
        "Perro especial",
        ProductCategory.HOT_DOGS,
        17000,
        "Perro sencillo con queso y tocineta",
        {
            "Pan de perro": "1",
            "Salchicha americana": "1",
            "Cebolla": "20",
            "Papitas ripio": "25",
            "Salsa de la casa": "30",
            "Queso tajado": "1",
            "Tocineta": "30",
        },
    ),
    ProductSeed(
        "SAL-CLA",
        "Salchipapa",
        ProductCategory.SIDES,
        16000,
        "Papa a la francesa con salchicha, queso y salsa",
        {
            "Papa a la francesa": "300",
            "Salchicha americana": "2",
            "Queso tajado": "1",
            "Salsa de la casa": "40",
        },
    ),
    ProductSeed(
        "ACO-PAP", "Papas a la francesa", ProductCategory.SIDES, 7000, "Porción de papas con salsa", _FRIES
    ),
    ProductSeed("BEB-GAS", "Gaseosa 400 ml", ProductCategory.DRINKS, 4500, "Gaseosa personal", _SODA),
    ProductSeed(
        "BEB-LIM",
        "Limonada natural",
        ProductCategory.DRINKS,
        6000,
        "Limonada de limón natural",
        {"Limón": "2", "Azúcar": "30"},
    ),
    ProductSeed(
        "COM-CLA",
        "Combo clásico",
        ProductCategory.COMBOS,
        26000,
        "Hamburguesa clásica + papas + gaseosa",
        _combine(_CLASSIC_BURGER, _FRIES, _SODA),
    ),
]


def seed_catalog(uow: UnitOfWork) -> tuple[int, int]:
    """Loads the demo menu. Idempotent: existing ingredients and SKUs are left untouched."""
    created_ingredients = created_products = 0
    with uow:
        ingredients: dict[str, Ingredient] = {}
        for seed in INGREDIENTS:
            ingredient = uow.ingredients.get_by_name(seed.name)
            if ingredient is None:
                ingredient = uow.ingredients.add(
                    Ingredient(
                        name=seed.name,
                        unit=seed.unit,
                        stock_quantity=Decimal(seed.stock),
                        reorder_level=Decimal(seed.reorder_level),
                        unit_cost=Decimal(seed.unit_cost),
                    )
                )
                created_ingredients += 1
            ingredients[seed.name] = ingredient

        for seed in PRODUCTS:
            if uow.products.get_by_sku(seed.sku) is not None:
                continue
            product = Product(
                sku=seed.sku,
                name=seed.name,
                category=seed.category,
                price=seed.price,
                description=seed.description,
            )
            product.recipe = [
                RecipeItem(ingredient=ingredients[name], quantity=Decimal(qty))
                for name, qty in seed.recipe.items()
            ]
            uow.products.add(product)
            created_products += 1

        uow.commit()
    logger.info("Seed complete: %d ingredients, %d products created", created_ingredients, created_products)
    return created_ingredients, created_products
