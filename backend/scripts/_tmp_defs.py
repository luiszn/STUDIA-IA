from __future__ import annotations

import json

from app.schemas.dashboard import PerformanceSeries

schema = PerformanceSeries.model_json_schema()
print(json.dumps(schema, indent=2))
