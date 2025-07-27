import axios from 'axios';

const instance = axios.create({
  baseURL: 'http://35.216.24.11:30002',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default instance;