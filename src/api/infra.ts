import axios from './axiosInstance';

// 배포된 pod 정보 조회 (테스트 서버)
export const getInfraPods = () =>
  axios.get('/infra');

// openapi_spec과 server_infra 연결
export const connectInfraWithOpenAPISpec = (data: {
  server_infra_id: number;
  openapi_spec: string;
}) =>
  axios.patch('/infra', data);

// 실행 환경 리소스 사용량 수정
export const updateInfraResources = (
  serverInfraId: number,
  data: {
    cpu?: number;
    memory?: number;
    storage?: number;
  }
) =>
  axios.put(`/infra/${serverInfraId}/resources`, data);
