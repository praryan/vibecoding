from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import boto3
from fastapi import FastAPI, HTTPException, Query

from .athena import AthenaQueryError, athena_client
from .config import settings

app = FastAPI(title="AWS Cost Intelligence API", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _parse_date(param: Optional[str], default: Optional[date] = None) -> date:
    if param:
        return datetime.fromisoformat(param).date()
    if default is None:
        raise ValueError("Date parameter missing and no default provided")
    return default


GROUP_BY_FIELD_MAP: Dict[str, str] = {
    "service": "coalesce(product_product_name, line_item_product_code)",
    "account": "line_item_usage_account_id",
    "region": "product_region",
}


@app.get("/cost/summary")
def cost_summary(
    start_date: Optional[str] = Query(None, description="ISO date, defaults to 30 days ago"),
    end_date: Optional[str] = Query(None, description="ISO date, defaults to today"),
    group_by: str = Query("service", pattern="^(service|account|region)$"),
    limit: int = Query(20, ge=1, le=500),
) -> Dict[str, List[Dict[str, float]]]:
    start = _parse_date(start_date, default=date.today() - timedelta(days=30))
    end = _parse_date(end_date, default=date.today())

    group_expr = GROUP_BY_FIELD_MAP[group_by]

    sql = f"""
        SELECT
          {group_expr} AS group_key,
          sum(CAST(line_item_unblended_cost AS DOUBLE)) AS cost
        FROM {settings.athena_database}.{settings.cur_table_name}
        WHERE date(line_item_usage_start_date) >= date('{start.isoformat()}')
          AND date(line_item_usage_start_date) <= date('{end.isoformat()}')
          AND line_item_line_item_type IN ('Usage','DiscountedUsage','SavingsPlanCoveredUsage')
        GROUP BY {group_expr}
        ORDER BY cost DESC
        LIMIT {int(limit)}
    """

    try:
        rows = athena_client.run_query(sql)
    except AthenaQueryError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    results = [
        {
            "group": r.get("group_key") or "(unknown)",
            "cost": float(r.get("cost") or 0.0),
        }
        for r in rows
    ]
    return {"results": results}


@app.get("/cost/forecast")
def cost_forecast(
    horizon_days: int = Query(14, ge=1, le=60),
    history_days: int = Query(60, ge=14, le=365),
) -> Dict[str, List[Dict[str, float]]]:
    end = date.today()
    start = end - timedelta(days=history_days)

    sql = f"""
        SELECT
          date_trunc('day', line_item_usage_start_date) AS usage_day,
          sum(CAST(line_item_unblended_cost AS DOUBLE)) AS cost
        FROM {settings.athena_database}.{settings.cur_table_name}
        WHERE date(line_item_usage_start_date) >= date('{start.isoformat()}')
          AND date(line_item_usage_start_date) <= date('{end.isoformat()}')
          AND line_item_line_item_type IN ('Usage','DiscountedUsage','SavingsPlanCoveredUsage')
        GROUP BY 1
        ORDER BY 1 ASC
    """

    try:
        rows = athena_client.run_query(sql)
    except AthenaQueryError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    history: List[Dict[str, float]] = []
    for r in rows:
        day_str = r.get("usage_day") or ""
        cost_val = float(r.get("cost") or 0.0)
        history.append({"date": day_str[:10], "cost": cost_val})

    # Simple baseline: moving average over last 7 observed days
    last_seven = [p["cost"] for p in history[-7:]] or [0.0]
    avg = sum(last_seven) / max(len(last_seven), 1)

    forecast: List[Dict[str, float]] = []
    for i in range(1, horizon_days + 1):
        d = end + timedelta(days=i)
        forecast.append({"date": d.isoformat(), "cost": avg})

    return {"history": history, "forecast": forecast}


@app.get("/cost/anomalies")
def cost_anomalies() -> Dict[str, List[Dict[str, float]]]:
    # Placeholder for anomaly detection (Phase 2). Returns empty list for now.
    return {"anomalies": []}


@app.post("/alerts/test")
def send_test_alert(message: str = "Test alert from Cost Intelligence API") -> Dict[str, str]:
    if not settings.sns_topic_arn:
        raise HTTPException(status_code=400, detail="SNS_TOPIC_ARN is not configured")

    client = boto3.client("sns", region_name=settings.aws_region)
    client.publish(TopicArn=settings.sns_topic_arn, Message=message, Subject="Cost Alert Test")
    return {"status": "sent"}
