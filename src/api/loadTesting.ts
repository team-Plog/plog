import axios from './axiosInstance';

export interface Stage {
  duration: string;
  target: number;
}

export interface Scenario {
  name: string;
  endpoint_id: number;
  executor: string;
  think_time: number;
  stages: Stage[];
}

export interface LoadTestingRequest {
  title: string;
  description: string;
  scenarios: Scenario[];
}

export const generateLoadTestScript = (data: LoadTestingRequest) =>
  axios.post('/load-testing', data);
