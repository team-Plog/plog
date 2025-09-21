import axios from "./axiosInstance";

// 테스트 분석 이력 조회
export const getAnalysisHistory = (
  testHistoryId: number,
  params?: {
    limit?: number; // 기본값: 50
    analysis_type?: string | null;
  }
) =>
  axios.get(`/analysis/history/${testHistoryId}`, {
    params: {
      limit: params?.limit ?? 50,
      analysis_type: params?.analysis_type ?? undefined,
    },
  });

// AI 분석 서비스 상태 확인 (Health Check)
export const getAnalysisHealth = () =>
  axios.get("/analysis/health");