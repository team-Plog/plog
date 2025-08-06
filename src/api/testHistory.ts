import axios from './axiosInstance';

// 테스트 기록 목록 조회
export const getTestHistoryList = (page: number, size: number) =>
  axios.get('/test-history/simple', {
    params: {
      page,
      size
    }
  });