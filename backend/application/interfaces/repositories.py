from abc import ABC, abstractmethod
from typing import Optional
from domain.user import User
from domain.country import Country, PopularCountry


class UserRepository(ABC):

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        ...

    @abstractmethod
    def get_by_username_with_hash(self, username: str) -> Optional[dict]:
        ...

    @abstractmethod
    def create(self, username: str, email: str, password_hash: str) -> User:
        ...

    @abstractmethod
    def create_refresh_token(self, user_id: int, token: str, expires_at) -> None:
        ...

    @abstractmethod
    def get_refresh_token(self, token: str) -> Optional[dict]:
        ...

    @abstractmethod
    def revoke_refresh_token(self, token: str, user_id: int) -> None:
        ...

    @abstractmethod
    def add_to_blacklist(self, jti: str, expires_at) -> None:
        ...

    @abstractmethod
    def is_jti_blacklisted(self, jti: str) -> bool:
        ...

    @abstractmethod
    def cleanup_expired_tokens(self) -> None:
        ...


class CountryRepository(ABC):

    @abstractmethod
    def get_cache_by_name(self, name: str) -> Optional[str]:
        ...

    @abstractmethod
    def upsert_cache(self, name_lower: str, cca3: str, data_json: str) -> None:
        ...

    @abstractmethod
    def get_cache_by_cca3(self, cca3: str) -> Optional[str]:
        ...

    @abstractmethod
    def get_cache_count(self) -> int:
        ...

    @abstractmethod
    def insert_many_countries(self, countries: list) -> None:
        ...

    @abstractmethod
    def get_all_names(self) -> list:
        ...

    @abstractmethod
    def increment_consulta(self, pais_nombre: str) -> None:
        ...

    @abstractmethod
    def get_populares(self, limit: int = 10) -> list:
        ...


class FavoriteRepository(ABC):

    @abstractmethod
    def get_user_favorites(self, user_id: int) -> list:
        ...

    @abstractmethod
    def add_favorite(self, user_id: int, cca3: str) -> None:
        ...

    @abstractmethod
    def remove_favorite(self, user_id: int, cca3: str) -> None:
        ...
