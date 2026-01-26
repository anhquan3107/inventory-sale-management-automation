from enum import Enum

class InventoryLogType(str, Enum):
    INIT = "INIT"
    SALE = "SALE"
    RESTOCK = "RESTOCK"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"
