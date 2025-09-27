import { CircleDashed, CircleCheck, TriangleAlert, RefreshCcw, FileText, type LucideIcon } from 'lucide-react';
import type { HttpMethod, TestStatus } from './types';

export const HTTP_METHOD_STYLES: Record<HttpMethod, { color: string; background: string }> = {
  GET: { color: 'var(--color-http-get)', background: 'var(--color-http-get-bg)' },
  POST: { color: 'var(--color-http-post)', background: 'var(--color-http-post-bg)' },
  PUT: { color: 'var(--color-http-put)', background: 'var(--color-http-put-bg)' },
  DELETE: { color: 'var(--color-http-delete)', background: 'var(--color-http-delete-bg)' },
  PATCH: { color: 'var(--color-http-patch)', background: 'var(--color-http-patch-bg)' },
  HEAD: { color: 'var(--color-http-head)', background: 'var(--color-http-head-bg)' },
  OPTIONS: { color: 'var(--color-http-options)', background: 'var(--color-http-options-bg)' },
  TRACE: { color: 'var(--color-http-trace)', background: 'var(--color-http-trace-bg)' },
  CONNECT: { color: 'var(--color-http-connect)', background: 'var(--color-http-connect-bg)' },
};

export const STATUS_CONFIG: Record<TestStatus, { 
  icon: LucideIcon; 
  color: string; 
  background: string;
  text: string;
}> = {
  before: {
    icon: CircleDashed,
    color: 'var(--color-http-trace)',
    background: 'var(--color-http-trace-bg)',
    text: '실행 전'
  },
  running: {
    icon: RefreshCcw,
    color: 'var(--color-http-get)',
    background: 'var(--color-http-get-bg)',
    text: '실행 중'
  },
  analyzing: {
    icon: FileText,
    color: 'var(--color-http-put)',
    background: 'var(--color-http-put-bg)',
    text: '문서 생성 중'
  },
  completed: {
    icon: CircleCheck,
    color: 'var(--color-http-post)',
    background: 'var(--color-http-post-bg)',
    text: '문서 생성 완료'
  },
  failed: {
    icon: TriangleAlert,
    color: 'var(--color-http-delete)',
    background: 'var(--color-http-delete-bg)',
    text: '테스트 실패'
  }
};