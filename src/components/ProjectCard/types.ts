import type { TestStatus } from '../Tag/types';

export interface ProjectCardProps {
  id: string;
  title: string;
  description: string;
  status: TestStatus;
  createdAt: string;
  onClick?: (projectId: string) => void;
  className?: string;
}

export interface MetricCardProps {
  icon?: React.ReactNode;
  label: string;      
  value: string;     
  className?: string; 
}