from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Country:
    name_common: str
    name_official: str
    cca3: str
    region: str
    subregion: Optional[str] = None
    population: Optional[int] = None
    capital: Optional[str] = None
    flags: dict = field(default_factory=dict)
    currencies: dict = field(default_factory=dict)
    latlng: list = field(default_factory=list)
    timezones: list = field(default_factory=list)
    translations: dict = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)


@dataclass
class CountryCache:
    nombre_comun: str
    cca3: str
    data: str
    ultima_actualizacion: Optional[str] = None


@dataclass
class PopularCountry:
    pais_nombre: str
    conteo: int
    data: Optional[dict] = None
