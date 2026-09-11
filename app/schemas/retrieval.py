from pydantic import BaseModel


class RetrievalFilters(BaseModel):
    manufacturer: str | None = None
    material: str | None = None
    category: str | None = None

    def active(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for name, value in self.model_dump().items():
            if isinstance(value, str) and value.strip():
                values[name] = value.strip()
        return values

    def is_empty(self) -> bool:
        return not self.active()
