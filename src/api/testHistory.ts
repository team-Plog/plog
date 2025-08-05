import axios from './axiosInstance';

// 테스트 기록 목록 조회
export const getTestHistoryList = (skip: number, limit: number) =>
  axios.get('/test-history/', {
    params: {
      skip,
      limit
    }
  });

// 테스트 기록 상세 조회
export const getTestHistoryDetail = (test_history_id: number) =>
  axios.get(`/test-history/${test_history_id}`);