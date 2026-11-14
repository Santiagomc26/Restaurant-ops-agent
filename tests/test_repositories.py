from decimal import Decimal

import pytest

from app.domain.enums import OrderChannel, OrderStatus
from app.domain.models import Customer, Order
from app.repositories.seed import INGREDIENTS, PRODUCTS, seed_catalog
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork


def test_seed_is_idempotent(uow: SqlAlchemyUnitOfWork) -> None:
    first = seed_catalog(uow)
    second = seed_catalog(uow)

    assert first == (len(INGREDIENTS), len(PRODUCTS))
    assert second == (0, 0)


def test_product_search_is_case_insensitive(seeded_uow: SqlAlchemyUnitOfWork) -> None:
    with seeded_uow as uow:
        names = {p.name for p in uow.products.search("HAMBURGUESA")}

    assert names == {"Hamburguesa clásica", "Hamburguesa doble", "Hamburguesa con tocineta"}


def test_combo_recipe_merges_shared_ingredients(seeded_uow: SqlAlchemyUnitOfWork) -> None:
    with seeded_uow as uow:
        combo = uow.products.get_by_sku("COM-CLA")
        recipe = {item.ingredient.name: item.quantity for item in combo.recipe}

    # Burger (30 ml) + fries (20 ml) share the house sauce: one recipe line, summed.
    assert recipe["Salsa de la casa"] == Decimal("50")
    assert recipe["Gaseosa 400 ml"] == Decimal("1")


def test_unavailable_products_are_hidden_from_menu(seeded_uow: SqlAlchemyUnitOfWork) -> None:
    with seeded_uow as uow:
        uow.products.get_by_sku("BEB-LIM").is_available = False
        uow.commit()

    with seeded_uow as uow:
        skus = {p.sku for p in uow.products.list_available()}

    assert "BEB-LIM" not in skus
    assert len(skus) == len(PRODUCTS) - 1


def test_ingredients_below_reorder_level(seeded_uow: SqlAlchemyUnitOfWork) -> None:
    with seeded_uow as uow:
        uow.ingredients.get_by_name("Pan de perro").stock_quantity = Decimal("10")
        uow.commit()

    with seeded_uow as uow:
        low = [i.name for i in uow.ingredients.list_below_reorder_level()]

    assert low == ["Pan de perro"]


def test_order_keeps_price_snapshot_and_total(seeded_uow: SqlAlchemyUnitOfWork) -> None:
    with seeded_uow as uow:
        customer = uow.customers.add(Customer(phone="573001234567", name="Santiago"))
        order = Order(customer=customer, channel=OrderChannel.SIMULATOR)
        order.add_item(uow.products.get_by_sku("HAM-CLA"), quantity=2)
        order.add_item(uow.products.get_by_sku("BEB-GAS"), quantity=1, notes="bien fría")
        uow.orders.add(order)
        uow.commit()
        order_id = order.id

    with seeded_uow as uow:
        uow.products.get_by_sku("HAM-CLA").price = 20000
        uow.commit()

    with seeded_uow as uow:
        saved = uow.orders.get(order_id)
        assert saved.status == OrderStatus.PENDING
        assert saved.total == 2 * 18000 + 4500
        assert saved.items[0].unit_price == 18000
        assert uow.orders.list_by_customer(saved.customer_id)[0].id == order_id


def test_uncommitted_work_is_rolled_back(seeded_uow: SqlAlchemyUnitOfWork) -> None:
    with pytest.raises(ValueError), seeded_uow as uow:
        bread = uow.ingredients.get_by_name("Pan de hamburguesa")
        bread.consume(Decimal("5"))
        bread.consume(Decimal("1000"))  # fails: the first consume must not persist either

    with seeded_uow as uow:
        assert uow.ingredients.get_by_name("Pan de hamburguesa").stock_quantity == Decimal("120")


def test_customer_lookup_by_phone(uow: SqlAlchemyUnitOfWork) -> None:
    with uow:
        uow.customers.add(Customer(phone="573009998877"))
        uow.commit()

    with uow:
        assert uow.customers.get_by_phone("573009998877") is not None
        assert uow.customers.get_by_phone("570000000000") is None


def test_order_rejects_non_positive_quantity(seeded_uow: SqlAlchemyUnitOfWork) -> None:
    with seeded_uow as uow, pytest.raises(ValueError):
        Order(channel=OrderChannel.SIMULATOR).add_item(uow.products.get_by_sku("ACO-PAP"), quantity=0)
