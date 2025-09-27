import json
from typing import List
import logging

from sqlalchemy.orm import Session

from app.models.sqlite.models import OpenAPISpecVersionModel
from app.models.sqlite.models.project_models import EndpointModel, OpenAPISpecModel
from app.schemas.load_test.load_test_request import LoadTestRequest, ScenarioConfig
from fastapi import HTTPException

logger = logging.getLogger(__name__)

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
    logger.info("first scenario: %s", first_scenario)

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
            # Body가 있는 요청 - JSON.stringify() 사용
            headers_str = "headers" if scenario.headers else "{}"
            if not scenario.headers:
                # Content-Type 헤더만 추가
                script_lines.append(f"  const requestHeaders = {{'Content-Type': 'application/json'}};")
                headers_str = "requestHeaders"
            else:
                # 기존 헤더에 Content-Type 추가
                script_lines.append(f"  const requestHeaders = {{...headers, 'Content-Type': 'application/json'}};")
                headers_str = "requestHeaders"
            
            script_lines.append(f"  const payload = JSON.stringify({url_parts['body']});")
            script_lines.append(f"  http.{method}('{url_parts['url']}', payload, {{ headers: {headers_str} }});")
        else:
            # Body가 없는 요청 (GET, DELETE 등)
            # Query parameter는 이미 URL에 포함되어 있음
            if scenario.headers:
                script_lines.append(f"  http.{method}('{url_parts['url']}', {{ headers }});")
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
            # Request Body: JavaScript 객체 형태로 설정 (JSON.stringify에서 사용할 수 있도록)
            try:
                # param.value가 JSON 문자열인 경우 파싱 후 다시 JavaScript 객체 문법으로 변환
                if isinstance(param.value, str):
                    parsed_json = json.loads(param.value)
                    body = json.dumps(parsed_json, ensure_ascii=False)
                else:
                    body = json.dumps(param.value, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                # JSON이 아닌 경우 문자열 그대로 사용
                body = f'"{param.value}"'
    
    # Query 파라미터가 있으면 URL에 추가
    if query_params:
        url += '?' + '&'.join(query_params)
    
    return {'url': url, 'body': body}

