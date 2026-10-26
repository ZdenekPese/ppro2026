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


class WarehouseNotFoundError(DomainException):
    """Výjimka vyvolaná, pokud sklad nebyl v systému nalezen."""
    def __init__(self, identifier: str):
        super().__init__(f"Sklad s identifikátorem '{identifier}' nebyl nalezen.")


class DuplicateWarehouseCodeError(DomainException):
    """Výjimka vyvolaná při duplicitním kódu skladu."""
    def __init__(self, code: str):
        super().__init__(f"Sklad s kódem '{code}' již existuje.")



class StockNotFoundError(DomainException):
    """Výjimka vyvolaná, pokud skladová zásoba nebyla nalezena."""
    def __init__(self, warehouse_id: str, product_id: str):
        super().__init__(f"Zásoba pro produkt '{product_id}' na skladě '{warehouse_id}' nebyla nalezena.")


class InsufficientStockError(DomainException):
    """Výjimka vyvolaná při pokusu o rezervaci či výdej většího množství, než je disponibilní."""
    def __init__(self, available: int, requested: int):
        super().__init__(
            f"Nedostatečná zásoba: požadováno {requested} ks, k dispozici je pouze {available} ks."
        )


class NegativeStockError(DomainException):
    """Výjimka vyvolaná při pokusu snížit skladovou zásobu do záporných hodnot."""
    def __init__(self, message: str = "Skladová zásoba nesmí klesnout do záporu."):
        super().__init__(message)


class CustomerNotFoundError(DomainException):
    """Výjimka vyvolaná, pokud zákazník nebyl nalezen."""
    def __init__(self, identifier: str):
        super().__init__(f"Zákazník s identifikátorem '{identifier}' nebyl nalezen.")


class CustomerDeletionForbiddenError(DomainException):
    """Výjimka vyvolaná při pokusu smazat zákazníka (zákaz mazání dle zadání B)."""
    def __init__(self, identifier: str, reason: str = "Zákazníky nelze z důvodu historie reklamací fyzicky mazat."):
        super().__init__(f"Smazání zákazníka '{identifier}' je zakázáno: {reason}")


class OrderNotFoundError(DomainException):
    """Výjimka vyvolaná, pokud objednávka nebyla nalezena."""
    def __init__(self, identifier: str):
        super().__init__(f"Objednávka s identifikátorem '{identifier}' nebyla nalezena.")


class DuplicateOrderNumberError(DomainException):
    """Výjimka vyvolaná při pokusu vytvořit objednávku s duplicitním číslem."""
    def __init__(self, order_number: str):
        super().__init__(f"Objednávka s číslem '{order_number}' již existuje.")


class InvalidOrderStatusError(DomainException):
    """Výjimka vyvolaná při neplatném přechodu stavu objednávky."""
    def __init__(self, current_status: str, target_status: str, reason: str = ""):
        super().__init__(
            f"Neplatný přechod stavu objednávky z '{current_status}' do '{target_status}'. {reason}".strip()
        )



