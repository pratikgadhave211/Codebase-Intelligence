import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const ingestRepo = async (githubUrl) => {
  const response = await axios.post(`${API_BASE_URL}/ingest`, { github_url: githubUrl });
  return response.data;
};

export const getDiagram = async (repoName) => {
  const response = await axios.get(`${API_BASE_URL}/diagram?repo_name=${repoName}`);
  return response.data;
};

export const getGraph = async (repoName) => {
  const response = await axios.get(`${API_BASE_URL}/graph?repo_name=${repoName}`);
  return response.data;
};

export const getBugs = async (repoName) => {
  const response = await axios.get(`${API_BASE_URL}/bugs?repo_name=${repoName}`);
  return response.data;
};

export const askQuestion = async (repoName, question) => {
  const response = await axios.post(`${API_BASE_URL}/ask`, { repo_name: repoName, question });
  return response.data;
};
