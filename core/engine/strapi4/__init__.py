from typing import Any, Dict


def flatten_strapi_object(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        if "attributes" in value and isinstance(value["attributes"], dict):
            merged = {"id": value.get("id")}
            merged.update(value["attributes"])
            return merged
        return value
    return {}
