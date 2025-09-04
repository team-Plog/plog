from typing import List

from sqlalchemy.orm import Session

from app.db.sqlite.models import OpenAPISpecVersionModel
from app.db.sqlite.models.project_models import EndpointModel, OpenAPISpecModel
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
    openapi_spec = (db.query(OpenAPISpecModel)
                    .join(OpenAPISpecModel.openapi_spec_versions)
                    .join(OpenAPISpecVersionModel.endpoints)
                    .filter(EndpointModel.id == endpoint.id, OpenAPISpecVersionModel.is_activate == True).first())

    if not openapi_spec or not openapi_spec.base_url:
        raise Exception("Base URL을 찾을 수 없습니다. OpenAPI 스펙에 base_url이 등록되어야 합니다.")

    base_url = openapi_spec.base_url.rstrip("/")

    # K6 options
    script_lines.append("export const options = {")
    script_lines.append(f"  tags: {{")
    script_lines.append(f"    job_name: '{job_name}'")
    script_lines.append(f"  }},")
    script_lines.append("  scenarios: {")

    for scenario in payload.scenarios:
        scenario_name = f"'{job_name}{scenario.endpoint_id}'"
        script_lines.append(f"    {job_name}{scenario.endpoint_id}: {{")
        # executor 별 옵션 출력
        option_lines = generate_k6_scenario_options(scenario, scenario_name)
        for line in option_lines:
            script_lines.append(line)
        script_lines.append("    },")
    script_lines.append("  }")
    script_lines.append("};\n")

    # exec 함수들
    for scenario in payload.scenarios:
        endpoint = get_endpoint_by_id(db, scenario.endpoint_id)
        method = endpoint.method.lower()
        
        # URL 및 파라미터 처리
        url_parts = generate_url_and_params(base_url, endpoint.path, scenario)
        
        script_lines.append(f"export function {job_name}{scenario.endpoint_id}() {{")
        
        # 헤더 처리
        if scenario.headers:
            script_lines.append("  const headers = {")
            for header in scenario.headers:
                script_lines.append(f"    '{header.header_key}': '{header.header_value}',")
            script_lines.append("  };")
        
        # HTTP 요청 생성
        if method in ['post', 'put', 'patch'] and url_parts['body']:
            # Body가 있는 요청
            if scenario.headers:
                script_lines.append(f"  http.{method}('{url_parts['url']}', {url_parts['body']}, {{ headers }});")
            else:
                script_lines.append(f"  http.{method}('{url_parts['url']}', {url_parts['body']});")
        else:
            # Body가 없는 요청 (GET, DELETE 등)
            if scenario.headers:
                script_lines.append(f"  http.{method}('{url_parts['url']}', null, {{ headers }});")
            else:
                script_lines.append(f"  http.{method}('{url_parts['url']}');")
        
        script_lines.append(f"  sleep({scenario.think_time});")
        script_lines.append("}\n")

    return "\n".join(script_lines)


def generate_k6_scenario_options(scenario: ScenarioConfig, scenario_name: str) -> List[str]:
    lines = []
    lines.append(f"      executor: '{scenario.executor}',")
    lines.append(f"      tags: {{ scenario: {scenario_name} }},")

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

    lines.append(f"      exec: {scenario_name},")
    return lines


def generate_url_and_params(base_url: str, endpoint_path: str, scenario: ScenarioConfig) -> dict:
    """
    파라미터 타입별로 URL과 파라미터를 처리하여 k6 스크립트용 데이터 생성
    
    Returns:
        dict: {'url': str, 'body': str or None}
    """
    url = base_url + endpoint_path
    body = None
    query_params = []
    
    if not scenario.parameters:
        return {'url': url, 'body': body}
    
    for param in scenario.parameters:
        if param.param_type == 'path':
            # Path 파라미터: URL 경로에서 {param_name} 형태를 실제 값으로 치환
            url = url.replace(f'{{{param.name}}}', param.value)
            
        elif param.param_type == 'query':
            # Query 파라미터: URL 쿼리 스트링에 추가
            query_params.append(f"{param.name}={param.value}")
            
        elif param.param_type == 'requestBody':
            # Request Body: JSON 문자열로 설정
            body = param.value
    
    # Query 파라미터가 있으면 URL에 추가
    if query_params:
        url += '?' + '&'.join(query_params)
    
    return {'url': url, 'body': body}

