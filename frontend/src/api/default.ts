import axios from "./axiosInstance";

// SSE URL 생성 함수 (실시간 스트림용)
export const getSseK6DataUrl = (jobName: string): string => {
  const baseURL = axios.defaults.baseURL || '';
  return `${baseURL}/sse/k6data/${jobName}`;
};