import axios from './axiosInstance';

export const getProjectList = () => axios.get('/project');

export const createProject = (data: {
  title: string;
  summary: string;
  description: string;
}) => axios.post('/project', data);

export const getProjectDetail = (projectId: number) =>
  axios.get(`/project/${projectId}`);

export const deleteProject = (projectId: number) =>
  axios.delete(`/project/${projectId}`);