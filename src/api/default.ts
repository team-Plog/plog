import axios from "./axiosInstance";

export const getSseK6Data = (jobName: string) => {
  return axios.get(`/sse/k6data/${jobName}`);
};
