from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from market_pipeline.acquisition.models import AcquisitionSuccess
from market_pipeline.extraction.models import (
    CheapSharkDealExtractionFailure,
    CheapSharkExtractionSuccess,
)


class ValidatedCheapSharkGameMetadata(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be blank")
        return value


class ValidatedCheapSharkDeal(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    store_id: str = Field(alias="storeID")
    price: str

    @field_validator("store_id")
    @classmethod
    def validate_store_id(cls, value: str) -> str:
        stripped_value = value.strip()
        if not (stripped_value.isascii() and stripped_value.isdecimal()):
            raise ValueError("store_id must contain only ASCII decimal digits")
        return value

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: str) -> str:
        try:
            decimal_price = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("price must be a numeric string") from exc
        if not decimal_price.is_finite():
            raise ValueError("price must be a finite number")
        if decimal_price < 0:
            raise ValueError("price must be non-negative")
        return value


@dataclass(frozen=True, slots=True)
class CheapSharkDealValidationFailure:
    index: int
    raw: Mapping[str, object]
    diagnostic_message: str

    def __post_init__(self) -> None:
        if not self.diagnostic_message.strip():
            raise ValueError("diagnostic_message must not be empty")
        if type(self.index) is not int:
            raise TypeError("index must have type int")
        if self.index < 0:
            raise ValueError("index must not be negative")


type CheapSharkDealValidationResult = (
    ValidatedCheapSharkDeal
    | CheapSharkDealValidationFailure
    | CheapSharkDealExtractionFailure
)


@dataclass(frozen=True, slots=True)
class CheapSharkValidationSuccess:
    extraction: CheapSharkExtractionSuccess
    validated_game_metadata: ValidatedCheapSharkGameMetadata
    deal_results: tuple[CheapSharkDealValidationResult, ...]


@dataclass(frozen=True, slots=True)
class CheapSharkValidationFailure:
    extraction: CheapSharkExtractionSuccess
    diagnostic_message: str

    def __post_init__(self) -> None:
        if not self.diagnostic_message.strip():
            raise ValueError("diagnostic_message must not be empty")


type CheapSharkValidationResult = (
    CheapSharkValidationSuccess
    | CheapSharkValidationFailure
)


class CheapSharkStore(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    store_id: str = Field(alias="storeID")
    store_name: str = Field(alias="storeName")

    @field_validator("store_id")
    @classmethod
    def validate_store_id(cls, value: str) -> str:
        if not (value.isascii() and value.isdecimal()):
            raise ValueError("store_id must contain only ASCII decimal digits")
        return value

    @field_validator("store_name")
    @classmethod
    def validate_store_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("store_name must not be blank")
        return value


@dataclass(frozen=True, slots=True)
class CheapSharkStoreCatalogSuccess:
    acquisition: AcquisitionSuccess
    stores: tuple[CheapSharkStore, ...]


@dataclass(frozen=True, slots=True)
class CheapSharkStoreCatalogFailure:
    acquisition: AcquisitionSuccess
    diagnostic_message: str

    def __post_init__(self) -> None:
        if not self.diagnostic_message.strip():
            raise ValueError("diagnostic_message must not be empty")


type CheapSharkStoreCatalogResult = (
    CheapSharkStoreCatalogSuccess
    | CheapSharkStoreCatalogFailure
)
