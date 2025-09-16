import axios from './axiosInstance';

// 엔드포인트 리스트 조회
export const getEndpointList = () => axios.get('/endpoint');

// 엔드포인트 상세 조회
export const getEndpointDetail = (endpoint_id: number) =>
  axios.get(`/endpoint/${endpoint_id}`);

// 엔드포인트 삭제
export const deleteEndpoint = (endpoint_id: number) =>
  axios.delete(`/endpoint/${endpoint_id}`);