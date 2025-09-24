import axios from "./axiosInstance";

// 테스트 기록 목록 조회
export const getTestHistoryList = (page: number, size: number) =>
  axios.get("/test-history/simple", {
    params: {
      page,
      size,
    },
  });

// 프로젝트별 테스트 기록 조회
export const getTestHistoryByProject = (projectId: number) =>
  axios.get(`/test-history/projects/${projectId}`);

// 테스트 기록 상세 조회
export const getTestHistoryDetail = (testHistoryId: number) =>
  axios.get(`/test-history/${testHistoryId}/details`);

// 테스트 기록 시계열 데이터 조회
export const getTestHistoryTimeseries = (testHistoryId: number) =>
  axios.get(`/test-history/${testHistoryId}/timeseries`);

// 테스트 리소스 시계열 데이터 조회
export const getTestHistoryResources = (testHistoryId: number) =>
  axios.get(`/test-history/${testHistoryId}/resources`);

// 테스트 기록 삭제
export const deleteTestHistory = (testHistoryId: number) => {
  axios.delete(`/test-history/${testHistoryId}`);
};

// 테스트 리소스 요약 조회 (테스트 보고서용)
export const getTestHistoryResourceSummary = (testHistoryId: number) =>
  axios.get(`/test-history/${testHistoryId}/resource/summary`);
