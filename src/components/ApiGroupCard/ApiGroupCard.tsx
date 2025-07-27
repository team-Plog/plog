import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Plus } from 'lucide-react';
import HttpMethodTag from '../Tag/HttpMethodTag';
import styles from './ApiGroupCard.module.css';

interface ApiEndpoint {
  id: number;
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  summary: string;
  description: string;
}

interface ApiGroupCardProps {
  groupName: string;
  baseUrl: string;
  endpoints: ApiEndpoint[];
  onAddEndpoint?: (endpoint: string) => void;
}

const ApiGroupCard: React.FC<ApiGroupCardProps> = ({ 
  groupName, 
  baseUrl, 
  endpoints,
  onAddEndpoint
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  const handleAddEndpoint = (endpoint: string) => {
    if (onAddEndpoint) {
      onAddEndpoint(endpoint);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header} onClick={toggleExpanded}>
        <div className={styles.headerContent}>
          <div className={styles.textContent}>
            <div className={`${styles.groupName} TitleL`}>{groupName}</div>
            <div className={`${styles.baseUrl} CaptionLight`}>{baseUrl}</div>
          </div>
          <button className={styles.toggleButton} type="button">
            {isExpanded ? <ChevronDown /> : <ChevronRight />}
          </button>
        </div>
      </div>
      
      {isExpanded && (
        <div className={styles.endpointsContainer}>
          {endpoints.map((endpoint) => (
            <div key={endpoint.id} className={styles.endpointItem}>
              <div className={styles.endpointInfo}>
                <HttpMethodTag method={endpoint.method} />
                <span className={`${styles.endpoint} CaptionBold`}>{endpoint.path}</span>
                <span className={`${styles.description} CaptionLight`}>{endpoint.summary}</span>
              </div>
              <button 
                className={styles.addButton} 
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleAddEndpoint(endpoint.path);
                }}
              >
                <Plus />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ApiGroupCard;