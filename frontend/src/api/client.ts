import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8002',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadRepo = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getGraph = async (analysisId: string) => {
  const response = await api.post('/graph', { analysis_id: analysisId });
  return response.data;
};

export const analyzeImpact = async (analysisId: string, nodeId: string) => {
  const response = await api.post('/impact', { analysis_id: analysisId, node_id: nodeId });
  return response.data;
};

export const queryNL = async (analysisId: string, question: string) => {
  const response = await api.post('/query', { analysis_id: analysisId, question });
  return response.data;
};

export const suggestFix = async (analysisId: string, nodeId: string, change: string) => {
  const response = await api.post('/suggest-fix', { analysis_id: analysisId, node_id: nodeId, change });
  return response.data;
};

export default api;
