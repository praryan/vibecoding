import time
from typing import Dict, List, Optional

import boto3

from .config import settings


class AthenaQueryError(Exception):
    pass


class AthenaQueryClient:
    def __init__(self,
                 region_name: Optional[str] = None,
                 workgroup: Optional[str] = None,
                 output_location: Optional[str] = None) -> None:
        self._region = region_name or settings.aws_region
        self._workgroup = workgroup or settings.athena_workgroup
        self._output_location = output_location or settings.athena_results_s3
        self._client = boto3.client("athena", region_name=self._region)

    def run_query(self, sql: str, timeout_seconds: Optional[int] = None) -> List[Dict[str, str]]:
        timeout = timeout_seconds or settings.athena_query_timeout_seconds
        start_resp = self._client.start_query_execution(
            QueryString=sql,
            WorkGroup=self._workgroup,
            ResultConfiguration=(
                {"OutputLocation": self._output_location}
                if self._output_location
                else {}
            ),
        )
        query_execution_id = start_resp["QueryExecutionId"]

        state = "RUNNING"
        start_time = time.time()
        while state in ("RUNNING", "QUEUED"):
            if time.time() - start_time > timeout:
                raise AthenaQueryError("Athena query timed out")

            resp = self._client.get_query_execution(QueryExecutionId=query_execution_id)
            state = resp["QueryExecution"]["Status"]["State"]
            if state == "FAILED":
                reason = resp["QueryExecution"]["Status"].get("StateChangeReason", "")
                raise AthenaQueryError(f"Athena query failed: {reason}")
            if state == "CANCELLED":
                raise AthenaQueryError("Athena query cancelled")
            if state in ("SUCCEEDED",):
                break
            time.sleep(1)

        # Fetch results and shape into list[dict]
        results: List[Dict[str, str]] = []
        paginator = self._client.get_paginator("get_query_results")
        for page in paginator.paginate(QueryExecutionId=query_execution_id):
            rows = page["ResultSet"]["Rows"]
            if not rows:
                continue
            # First row on first page is header
            if not results:
                headers = [c.get("VarCharValue", "") for c in rows[0]["Data"]]
                data_rows = rows[1:]
            else:
                data_rows = rows

            for r in data_rows:
                values = [c.get("VarCharValue", None) for c in r["Data"]]
                results.append({h: v for h, v in zip(headers, values)})

        return results


athena_client = AthenaQueryClient()
