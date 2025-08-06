import axios from './axiosInstance';

// 스케줄러 상태 조회
export const getSchedulerStatus = () =>
  axios.get('/scheduler/status');

// 스케줄러 재시작 - 디버깅/관리 목적
export const restartScheduler = () =>
  axios.post('/scheduler/restart');

// 특정 job 강제 처리 - 디버깅 목적
export const forceProcessJob = (job_name: string) =>
  axios.post(`/scheduler/force-process/${job_name}`);