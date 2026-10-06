"""Optional online market price resolver for transporter calculator v4.

Uses OpenAI Responses API + built-in web search.  It is deliberately separate
from engineering and costing so that online market evidence can be replaced by
corporate supplier integrations later.
"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Dict, List


def search_prices_for_bom(
    bom: List[Dict[str, Any]],
    api_key: str | None = None,
    model: str | None = None,
    country: str = "RU",
) -> List[Dict[str, Any]]:
    from openai import OpenAI
    model = model or os.environ.get("OPENAI_PRICE_MODEL") or os.environ.get("OPENAI_MODEL")
    if not model:
        raise ValueError("Укажите модель API для поиска цен")

    client = OpenAI(api_key=api_key, timeout=90.0, max_retries=1) if api_key else OpenAI(timeout=90.0, max_retries=1)

    compact_bom = [
        {
            "position": str(x.get("Позиция", "")),
            "quantity": x.get("Кол-во", 0),
            "unit": str(x.get("Ед.", "")),
            "parameter": str(x.get("Параметр", "")),
            "item_key": " | ".join(str(x.get(k, "")).strip() for k in ("Позиция", "Параметр", "Ед.")),
        }
        for x in bom
    ]

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "prices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "category": {"type": "string"},
                        "description": {"type": "string"},
                        "unit": {"type": "string"},
                        "unit_price_rub": {"type": "number"},
                        "source_name": {"type": "string"},
                        "source_url": {"type": "string"},
                        "price_date": {"type": "string"},
                        "note": {"type": "string"},
                        "item_key": {"type": "string"},
                        "vat_included": {"type": "boolean"},
                        "vat_pct": {"type": "number"},
                    },
                    "required": [
                        "category", "description", "unit", "unit_price_rub",
                        "source_name", "source_url", "price_date", "note", "item_key", "vat_included", "vat_pct"
                    ],
                },
            }
        },
        "required": ["prices"],
    }

    prompt = f"""
Ты — закупщик промышленного оборудования в РФ. Найди актуальные публичные цены
для предварительной калькуляции BOM транспортера. Работай только с конкретными
товарами/материалами, соответствующими параметрам. Если точного совпадения нет,
верни нулевую цену, не заменяй типоразмер ближайшим.

Правила:
- валюта результата RUB;
- верни исходную цену, vat_included и ставку vat_pct по источнику. Если налоговый базис неизвестен, цена 0;
- item_key скопируй из соответствующей позиции BOM без изменений;
- price_date — дата проверки источника в формате YYYY-MM-DD;
- выбирай нормальную рыночную цену, не подозрительно низкую рекламную цену;
- для каждой позиции верни одну рекомендуемую цену за ту же единицу измерения,
  что в BOM;
- если публичную цену надежно найти нельзя, unit_price_rub=0;
- source_url должен вести на страницу, где видна цена/товар;
- не оценивай внутреннюю трудоемкость предприятия через интернет.

Категории используй: belt, idler_set, roller, drum, motor, gearbox, gearmotor,
frame_steel, steel_kg, other.

BOM:
{json.dumps(compact_bom, ensure_ascii=False, indent=2)}

Дата оценки: {date.today().isoformat()}.
"""

    response = client.responses.create(
        model=model,
        store=False,
        tools=[{
            "type": "web_search_preview",
            "user_location": {"type": "approximate", "country": country},
            "search_context_size": "medium",
        }],
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "transporter_market_prices",
                "strict": True,
                "schema": schema,
            },
        },
    )
    data = json.loads(response.output_text)
    return data.get("prices", [])
