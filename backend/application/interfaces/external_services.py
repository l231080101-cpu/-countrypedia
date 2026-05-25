from abc import ABC, abstractmethod
from typing import Optional
from domain.country import Country
from domain.travel import TravelAdvisory, ExchangeRate, CostOfLiving, Weather, NewsResult


class ExternalAPIClient(ABC):
    """Base class for all external API clients."""
    pass


class RestCountriesService(ExternalAPIClient):

    @abstractmethod
    def get_country_by_name(self, name: str) -> Optional[Country]:
        ...

    @abstractmethod
    def get_countries_by_region(self, region: str) -> list:
        ...

    @abstractmethod
    def get_all_countries_lightweight(self) -> list:
        ...

    @abstractmethod
    def get_country_coordinates(self, country_name: str) -> tuple:
        ...


class ExchangeRateService(ExternalAPIClient):

    @abstractmethod
    def get_rates(self) -> Optional[ExchangeRate]:
        ...

    @abstractmethod
    def get_rate_for_currency(self, currency_code: str) -> Optional[float]:
        ...


class WeatherService(ExternalAPIClient):

    @abstractmethod
    def get_weather(self, country_name: str, lat: float, lon: float) -> Optional[Weather]:
        ...


class NewsService(ExternalAPIClient):

    @abstractmethod
    def get_news(self, country_name: str, language: str = 'es') -> Optional[NewsResult]:
        ...


class WorldBankService(ExternalAPIClient):

    @abstractmethod
    def get_gdp_per_capita(self, cca2: str) -> Optional[float]:
        ...


class TravelAdvisoryService(ExternalAPIClient):

    @abstractmethod
    def get_advisory(self, country_name: str, region: Optional[str] = None) -> TravelAdvisory:
        ...


class CostOfLivingService(ExternalAPIClient):

    @abstractmethod
    def estimate(self, country_name: str, region: str, gdp_factor: Optional[float] = None) -> CostOfLiving:
        ...
