export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS' | 'TRACE' | 'CONNECT';

export type TestStatus = 'before' | 'completed' | 'failed' | 'running';

export interface HttpMethodTagProps {
  method: HttpMethod;
  className?: string;
}

export interface StatusBadgeProps {
  status: TestStatus;
  className?: string;
}