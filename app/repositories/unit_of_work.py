from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from app.repositories.sqlalchemy_repositories import (
    SqlAlchemyCustomerRepository,
    SqlAlchemyIngredientRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyProductRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        # All repositories share one session, hence one database transaction.
        self.products = SqlAlchemyProductRepository(self._session)
        self.ingredients = SqlAlchemyIngredientRepository(self._session)
        self.customers = SqlAlchemyCustomerRepository(self._session)
        self.orders = SqlAlchemyOrderRepository(self._session)
        return self

    def __exit__(self, *args: object) -> None:
        # Anything not explicitly committed is discarded: forgetting commit()
        # fails safe instead of persisting half a business operation.
        self.rollback()
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
