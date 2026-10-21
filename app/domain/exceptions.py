from typing import Optional


class DomainException(Exception):
    """Základní bázová třída pro doménové výjimky."""
    pass


class ProductNotFoundError(DomainException):
    """Výjimka vyvolaná, pokud produkt nebyl v databázi nalezen."""
    def __init__(self, identifier: str):
        super().__init__(f"Produkt s identifikátorem '{identifier}' nebyl nalezen.")


class DuplicateProductCodeError(DomainException):
    """Výjimka vyvolaná při pokusu o uložení produktu s již existujícím kódem (SKU)."""
    def __init__(self, code: str):
        super().__init__(f"Produkt s kódem (SKU) '{code}' již v systému existuje.")


class InvalidPriceError(DomainException):
    """Výjimka vyvolaná při neplatné hodnotě nákupní nebo prodejní ceny."""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


class CategoryNotFoundError(DomainException):
    """Výjimka vyvolaná, pokud kategorie nebyla v databázi nalezena."""
    def __init__(self, identifier: str):
        super().__init__(f"Kategorie s identifikátorem '{identifier}' nebyla nalezena.")


class DuplicateCategoryNameError(DomainException):
    """Výjimka vyvolaná při pokusu o uložení kategorie s již existujícím názvem."""
    def __init__(self, name: str):
        super().__init__(f"Kategorie s názvem '{name}' již existuje.")

