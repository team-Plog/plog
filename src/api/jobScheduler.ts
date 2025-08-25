import axios from './axiosInstance';

// 스케줄러 상태 조회
export const getSchedulerStatus = () =>
  axios.get('/scheduler/status');

// 스케줄러 재시작 - 디버깅/관리 목적
export const restartScheduler = () =>
  axios.post('/scheduler/restart');

// 특정 Job 일시정지 - 개발용
export const suspendJob = (job_name: string) =>
  axios.post(`/scheduler/suspend/${job_name}`);

// 특정 Job 재개 - 개발용
export const resumeJob = (job_name: string) =>
  axios.post(`/scheduler/resume/${job_name}`);

// 특정 Job 중지
export const stopJob = (job_name: string) =>
  axios.delete(`/scheduler/stop/${job_name}`);