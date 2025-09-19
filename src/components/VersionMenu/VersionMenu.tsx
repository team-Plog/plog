import React, { useEffect, useRef, useState } from "react";
import { Clock, Hash } from "lucide-react";
import styles from "./VersionMenu.module.css";
import { getOpenAPIVersions, updateOpenAPIVersion } from "../../api";

interface VersionData {
  openapi_spec_version_id: number;
  created_at: string;
  commit_hash: string | null;
  is_active: boolean;
}

interface VersionMenuProps {
  openApiSpecId: number;
  onClose: () => void;
  position: { x: number; y: number };
  onVersionChanged?: () => void;
}

const VersionMenu: React.FC<VersionMenuProps> = ({
  openApiSpecId,
  onClose,
  position,
  onVersionChanged,
}) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [versions, setVersions] = useState<VersionData[]>([]);
  const [loading, setLoading] = useState(true);
  const [changingVersion, setChangingVersion] = useState<number | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    
    const handleScroll = () => {
      onClose();
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("scroll", handleScroll, true);
    
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("scroll", handleScroll, true);
    };
  }, [onClose]);

  useEffect(() => {
    const fetchVersions = async () => {
      try {
        setLoading(true);
        const response = await getOpenAPIVersions(openApiSpecId);
        if (response.data.success) {
          console.log('🔍 버전 상세 정보:', response.data.data);
          setVersions(response.data.data);
        }
      } catch (error) {
        console.error('Failed to fetch versions:', error);
        alert('버전 정보를 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    };

    fetchVersions();
  }, [openApiSpecId]);

  const handleVersionChange = async (versionId: number) => {
    if (changingVersion) return; // 이미 변경 중인 경우 무시

    try {
      setChangingVersion(versionId);
      await updateOpenAPIVersion(versionId, { version: "active" });
      
      // 성공 시 버전 목록 다시 불러오기
      const response = await getOpenAPIVersions(openApiSpecId);
      if (response.data.success) {
        setVersions(response.data.data);
      }
      
      onVersionChanged?.();
      alert('버전이 성공적으로 변경되었습니다.');
      onClose();
    } catch (error) {
      console.error('Failed to change version:', error);
      alert('버전 변경에 실패했습니다.');
    } finally {
      setChangingVersion(null);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const menuStyle = {
    position: 'fixed' as const,
    left: position.x,
    top: position.y,
    right: 'auto',
  };

  return (
    <div 
      className={styles.versionMenu} 
      ref={menuRef}
      style={menuStyle}
    >
      <div className={styles.header}>
        <span className={styles.title}>버전 선택</span>
      </div>
      
      {loading ? (
        <div className={styles.loading}>
          <span>로딩 중...</span>
        </div>
      ) : versions.length === 0 ? (
        <div className={styles.empty}>
          <span>사용 가능한 버전이 없습니다.</span>
        </div>
      ) : (
        <div className={styles.versionList}>
          {versions.map((version) => (
            <div
              key={version.openapi_spec_version_id}
              className={`${styles.versionItem} ${version.is_active ? styles.active : ''} ${changingVersion === version.openapi_spec_version_id ? styles.changing : ''}`}
              onClick={() => !version.is_active && handleVersionChange(version.openapi_spec_version_id)}
            >
              <div className={styles.versionInfo}>
                <div className={styles.hashInfo}>
                  <Hash className={styles.icon} />
                  <span className={styles.hash}>
                    {version.commit_hash || `v${version.openapi_spec_version_id}`}
                  </span>
                </div>
                
                <div className={styles.dateInfo}>
                  <Clock className={styles.icon} />
                  <span className={styles.date}>
                    {formatDate(version.created_at)}
                  </span>
                </div>
              </div>
              
              <div className={styles.statusContainer}>
                <span className={`${styles.statusTag} ${version.is_active ? styles.activeTag : styles.inactiveTag}`}>
                  {version.is_active ? 'ACTIVE' : 'INACTIVE'}
                </span>
                {changingVersion === version.openapi_spec_version_id && (
                  <span className={styles.changingText}>변경 중...</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default VersionMenu;