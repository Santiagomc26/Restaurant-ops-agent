from enum import StrEnum


class ProductCategory(StrEnum):
    BURGERS = "hamburguesas"
    HOT_DOGS = "perros"
    SIDES = "acompañamientos"
    COMBOS = "combos"
    DRINKS = "bebidas"


class UnitOfMeasure(StrEnum):
    GRAM = "g"
    MILLILITER = "ml"
    UNIT = "unidad"


class OrderStatus(StrEnum):
    PENDING = "pendiente"
    CONFIRMED = "confirmado"
    PREPARING = "en_preparacion"
    DELIVERED = "entregado"
    CANCELLED = "cancelado"


class OrderChannel(StrEnum):
    WHATSAPP = "whatsapp"
    SIMULATOR = "simulador"
    COUNTER = "mostrador"
