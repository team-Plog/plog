import axios from "./axiosInstance";

export interface AnalyzeRequest {
  project_id: number;
  open_api_url: string;
}

// 명세 분석 및 등록 (POST)
export const analyzeOpenAPI = (data: AnalyzeRequest) =>
  axios.post("/openapi/analyze", data);

// 명세 리스트 조회
export const getOpenAPIList = () => axios.get("/openapi");

// 명세 삭제
export const deleteOpenAPI = (openapi_spec_id: number) =>
  axios.delete(`/openapi/${openapi_spec_id}`);

// 애플리케이션 배포 또는 업데이트
export const deployOpenAPI = (data: {
  openapi_spec_id: number;
  values?: object;
}) => axios.post("/openapi/deploy", data);

// 서버 버전 리스트 조회
export const getOpenAPIVersions = (openapi_spec_id: number) =>
  axios.get(`/openapi/${openapi_spec_id}/versions`);

// 서버 버전 변경
export const updateOpenAPIVersion = (openapi_spec_version_id: number) =>
  axios.patch(`/openapi/versions/${openapi_spec_version_id}`);
