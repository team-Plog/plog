from typing import List

from sqlalchemy.orm import Session
from app.db.sqlite.models.project_models import EndpointModel, OpenAPISpecModel, TagModel
from app.dto.load_test.load_test_request import LoadTestRequest, ScenarioConfig
from fastapi import HTTPException

def get_endpoint_by_id(db: Session, endpoint_id: int):
    endpoint = db.query(EndpointModel).filter(EndpointModel.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail=f"Endpoint ID {endpoint_id} not found")
    return endpoint

def generate_k6_script(payload: LoadTestRequest, job_name: str, db: Session) -> str:
    script_lines = []

    # K6 import
    script_lines.append("import http from 'k6/http';")
    script_lines.append("import { sleep } from 'k6';\n")

    # base_url 조회 (첫 시나리오 기준으로 openapi_spec_id 역추적)
    first_scenario = payload.scenarios[0]
    endpoint = get_endpoint_by_id(db, first_scenario.endpoint_id)
    openapi_spec = db.query(OpenAPISpecModel).join(OpenAPISpecModel.tags).join(TagModel.endpoints).filter(
        EndpointModel.id == endpoint.id).first()

    if not openapi_spec or not openapi_spec.base_url:
        raise Exception("Base URL을 찾을 수 없습니다. OpenAPI 스펙에 base_url이 등록되어야 합니다.")

    base_url = openapi_spec.base_url.rstrip("/")

    # K6 options
    script_lines.append("export const options = {")
    script_lines.append("  scenarios: {")

    for scenario in payload.scenarios:
        script_lines.append(f"    {job_name}#{scenario.endpoint_id}: {{")
        # executor 별 옵션 출력
        option_lines = generate_k6_scenario_options(scenario)
        for line in option_lines:
            script_lines.append(line)
        script_lines.append("    },")
    script_lines.append("  }")
    script_lines.append("};\n")

    # exec 함수들
    for scenario in payload.scenarios:
        endpoint = get_endpoint_by_id(db, scenario.endpoint_id)
        method = endpoint.method.lower()
        full_url = f"{base_url}{endpoint.path}"

        script_lines.append(f"export function {scenario.name}() {{")
        script_lines.append(f"  http.{method}('{full_url}');")
        script_lines.append(f"  sleep({scenario.think_time});")
        script_lines.append("}\n")

    return "\n".join(script_lines)


def generate_k6_scenario_options(scenario: ScenarioConfig) -> List[str]:
    lines = []
    lines.append(f"      executor: '{scenario.executor}',")

    if scenario.executor == "constant-vus":
        # constant-vus는 stages 대신 vus와 duration 단일 필드
        if not scenario.stages:
            raise ValueError("constant-vus executor는 최소 1개의 stage를 지정해야 합니다.")
        first_stage = scenario.stages[0]
        lines.append(f"      vus: {first_stage.target},")
        lines.append(f"      duration: '{first_stage.duration}',")

    elif scenario.executor == "ramping-vus":
        # ramping-vus는 stages 배열을 사용
        if not scenario.stages:
            raise ValueError("ramping-vus executor는 stages 배열을 반드시 지정해야 합니다.")
        lines.append("      stages: [")
        for stage in scenario.stages:
            lines.append(f"        {{ duration: '{stage.duration}', target: {stage.target} }},")
        lines.append("      ],")

    lines.append(f"      exec: '{scenario.name}',")
    return lines

