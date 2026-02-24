from typing import Any, Dict, List, Optional


class CMS:
    async def get_collection_records_by_filters(self, *_: Any, **__: Any) -> List[Dict[str, Any]]:
        return []

    async def get_collection_record_by_id(self, *_: Any, **__: Any) -> Optional[Dict[str, Any]]:
        return None

    async def update_collection_record(self, *_: Any, **__: Any) -> Dict[str, Any]:
        return {"status": "ok"}

    async def create_collection_record(self, *_: Any, **__: Any) -> Dict[str, Any]:
        return {"status": "ok"}
