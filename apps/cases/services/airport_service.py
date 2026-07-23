from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

import airportsdata
import pycountry
import requests
from django.conf import settings


AIRPORT_SEARCH_RESULT_LIMIT = 10


class AirportLookupError(Exception):
    pass


class AirportProviderUnavailableError(AirportLookupError):
    pass


@dataclass(slots=True)
class AirportRecord:
    code: str
    name: str
    city: str | None
    country: str | None


@dataclass(slots=True)
class AirportDistanceResult:
    from_airport_code: str
    to_airport_code: str
    kilometers: Decimal


@lru_cache(maxsize=1)
def _load_airport_records() -> tuple[AirportRecord, ...]:
    records = []
    for airport_code, attributes in airportsdata.load("IATA").items():
        normalized_code = (attributes.get("iata") or airport_code or "").upper()
        if len(normalized_code) != 3:
            continue
        records.append(
            AirportRecord(
                code=normalized_code,
                name=attributes.get("name") or normalized_code,
                city=attributes.get("city") or None,
                country=_resolve_country_name(attributes.get("country")),
            )
        )
    return tuple(records)


@lru_cache(maxsize=512)
def _resolve_country_name(country_code: str | None) -> str | None:
    if not country_code:
        return None

    country = pycountry.countries.get(alpha_2=country_code.upper())
    if country is None:
        return country_code.upper()
    return country.name


class AirportService:
    def __init__(self, *, base_url: str | None = None, session: requests.Session | None = None) -> None:
        self.base_url = (base_url or settings.AIRPORTGAP_BASE_URL).rstrip("/")
        self.session = session or requests.Session()
        self.verify = settings.AIRPORTGAP_CA_BUNDLE or settings.AIRPORTGAP_VERIFY_SSL

    def search(self, query: str) -> list[AirportRecord]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        matches = []
        seen_codes = set()
        lowered_query = normalized_query.lower()
        for airport in _load_airport_records():
            if airport.code in seen_codes:
                continue
            if self._matches_query(airport, lowered_query):
                matches.append(airport)
                seen_codes.add(airport.code)
                if len(matches) >= AIRPORT_SEARCH_RESULT_LIMIT:
                    break
        return matches

    def get_airport(self, airport_code: str) -> AirportRecord:
        normalized_code = airport_code.upper()
        payload = self._get_json(f"/api/airports/{normalized_code}", allow_not_found=True)
        airport = self._build_airport_record(payload.get("data"))
        if airport is None:
            raise AirportLookupError(f"Airport code {normalized_code} is invalid")
        return airport

    def ensure_airport_exists(self, airport_code: str) -> AirportRecord:
        return self.get_airport(airport_code)

    def calculate_distance(self, *, from_airport_code: str, to_airport_code: str) -> AirportDistanceResult:
        payload = self._post_json(
            "/api/airports/distance",
            data={
                "from": from_airport_code.upper(),
                "to": to_airport_code.upper(),
            },
        )
        attributes = payload.get("data", {}).get("attributes", {})
        kilometers = Decimal(str(attributes.get("kilometers", "0")))
        return AirportDistanceResult(
            from_airport_code=from_airport_code.upper(),
            to_airport_code=to_airport_code.upper(),
            kilometers=kilometers,
        )

    def _matches_query(self, airport: AirportRecord, lowered_query: str) -> bool:
        haystacks = [airport.code.lower(), airport.name.lower()]
        if airport.city:
            haystacks.append(airport.city.lower())
        if airport.country:
            haystacks.append(airport.country.lower())
        return any(lowered_query in haystack for haystack in haystacks)

    def _get_json(self, path: str, *, allow_not_found: bool = False) -> dict:
        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                timeout=10,
                verify=self.verify,
            )
        except requests.exceptions.SSLError as exc:
            raise AirportProviderUnavailableError(
                "Airport provider SSL verification failed. Configure AIRPORTGAP_CA_BUNDLE "
                "or set AIRPORTGAP_VERIFY_SSL=False for local development if your network "
                "intercepts HTTPS traffic."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise AirportProviderUnavailableError("Airport provider unavailable") from exc

        if allow_not_found and response.status_code == 404:
            return {}
        if response.status_code != 200:
            raise AirportProviderUnavailableError("Airport provider unavailable")
        return response.json()

    def _post_json(self, path: str, *, data: dict) -> dict:
        try:
            response = self.session.post(
                f"{self.base_url}{path}",
                data=data,
                timeout=10,
                verify=self.verify,
            )
        except requests.exceptions.SSLError as exc:
            raise AirportProviderUnavailableError(
                "Airport provider SSL verification failed. Configure AIRPORTGAP_CA_BUNDLE "
                "or set AIRPORTGAP_VERIFY_SSL=False for local development if your network "
                "intercepts HTTPS traffic."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise AirportProviderUnavailableError("Airport provider unavailable") from exc

        if response.status_code != 200:
            raise AirportProviderUnavailableError("Airport provider unavailable")
        return response.json()

    def _build_airport_record(self, item: dict | None) -> AirportRecord | None:
        if not item:
            return None
        attributes = item.get("attributes", {})
        iata_code = (attributes.get("iata") or item.get("id") or "").upper()
        if not iata_code:
            return None
        return AirportRecord(
            code=iata_code,
            name=attributes.get("name") or iata_code,
            city=attributes.get("city"),
            country=attributes.get("country"),
        )
