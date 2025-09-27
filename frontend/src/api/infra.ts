import axios from "./axiosInstance";

// 배포된 pod 정보 조회 (테스트 서버)
export const getInfraPods = () => axios.get("/infra");

// openapi_spec과 server_infra 연결 (PATCH /infra)
export const connectInfraWithOpenAPISpec = (data: {
  openapi_spec_id: number;
  group_name: string;
}) => axios.patch("/infra", data);

// 실행 환경 리소스 사용량 수정 (PUT /infra/{server_infra_id}/resources)
export const updateInfraResources = (data: {
  group_name: string;
  cpu_request_millicores?: string;
  cpu_limit_millicores?: string;
  memory_request_millicores?: string;
  memory_limit_millicores?: string;
}) => {
  return axios.put("/infra/resources", data);
};
