import type { TestStatus } from '../Tag/types';

export interface ProjectCardProps {
  id: number;
  title: string;
  summary: string;
  status: TestStatus;
  updatedAt: string | null;
  onClick?: (projectId: number) => void;
  className?: string;
}

export interface MetricCardProps {
  icon?: React.ReactNode;
  label: string;      
  value: string;     
  color?: string;
  className?: string; 
}