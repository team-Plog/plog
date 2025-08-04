import axios from './axiosInstance';

export interface Stage {
  duration: string;
  target: number;
}

export interface Scenario {
  name: string;
  endpoint_id: number;
  executor: 'constant-vus' | 'ramping-vus';
  think_time: number;
  stages: Stage[];
  response_time_target?: number;
  error_rate_target?: number;
}

export interface LoadTestingRequest {
  title: string;
  description: string;
  target_tps?: number;
  scenarios: Scenario[];
}

export interface LoadTestingResponse {
  file_name: string;
  job_name: string;
}

export const generateLoadTestScript = (data: LoadTestingRequest) =>
  axios.post<LoadTestingResponse>('/load-testing', data);

// 테스트 상태 조회용 타입
export interface TestStatus {
  id: string;
  status: 'running' | 'completed' | 'failed';
  progress: number;
  duration: string;
}

// 실시간 메트릭 타입
export interface TestMetrics {
  current_tps: number;
  avg_response_time: number;
  error_rate: number;
  active_users: number;
}