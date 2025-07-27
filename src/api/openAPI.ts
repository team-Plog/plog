import axios from './axiosInstance';

export interface AnalyzeRequest {
  project_id: number;
  open_api_url: string;
}

// 명세 분석 및 등록 (POST)
export const analyzeOpenAPI = (data: AnalyzeRequest) =>
  axios.post('/openapi/analyze', data);

// 명세 리스트 조회
export const getOpenAPIList = () => axios.get('/openapi');
