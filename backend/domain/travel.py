from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TravelAdvisory:
    visa_required: str = "Consultar"
    plug_type: str = "Consultar"
    water_safe: str = "Consultar"
    safety_level: str = "yellow"
    best_time: str = "Consultar"
    attractions: list = field(default_factory=lambda: ["Investiga antes de viajar"])
    details: str = "Revisa fuentes oficiales antes de tu viaje."
    signal: str = "🟡"


@dataclass
class ExchangeRate:
    base: str = "USD"
    rates: dict = field(default_factory=dict)
    timestamp: Optional[float] = None


@dataclass
class CostOfLiving:
    country: str
    factor: float = 1.0
    region: str = "Americas"
    costs_usd: dict = field(default_factory=lambda: {
        "comida": 350, "transporte": 120,
        "alojamiento": 800, "entretenimiento": 200, "servicios": 150
    })


@dataclass
class Weather:
    temp: Optional[float] = None
    feels_like: Optional[float] = None
    humidity: Optional[int] = None
    description: str = ""
    icon: str = ""
    wind_speed: Optional[float] = None
    city: str = ""


@dataclass
class NewsArticle:
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    publishedAt: Optional[str] = None
    urlToImage: Optional[str] = None


@dataclass
class NewsResult:
    articles: list = field(default_factory=list)
    totalResults: int = 0
