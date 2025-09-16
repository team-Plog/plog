import React, {useState, useRef, useEffect} from "react";
import {ChevronDown, ChevronRight, Folder, Link, Database} from "lucide-react";
import styles from "./ApiTree.module.css";
import ActionMenu from "../ActionMenu/ActionMenu";

interface ApiEndpoint {
  id: string;
  path: string;
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
}

interface ApiGroup {
  id: string;
  name: string;
  endpoints: ApiEndpoint[];
}

interface ApiServer {
  id: string;
  name: string;
  groups: ApiGroup[];
}

interface ApiTreeProps {
  servers: ApiServer[];
  onEndpointClick?: (
    endpoint: ApiEndpoint,
    serverName: string,
    groupName: string
  ) => void;
  onDeleteServer?: (serverId: string) => void;
  onDeleteGroup?: (serverId: string, groupId: string, endpointIds: string[]) => void;
  onDeleteEndpoint?: (endpointId: string) => void;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  type: 'server' | 'group' | 'endpoint';
  id: number;
  name?: string;
  endpointIds?: string[];
}

const ApiTree: React.FC<ApiTreeProps> = ({
  servers, 
  onEndpointClick,
  onDeleteServer,
  onDeleteGroup,
  onDeleteEndpoint
}) => {
  const [expandedServers, setExpandedServers] = useState<Set<string>>(
    new Set()
  );
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    type: 'server',
    id: 0
  });
  
  const contextMenuRef = useRef<HTMLDivElement>(null);

  // 컨텍스트 메뉴 외부 클릭 감지
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
        setContextMenu(prev => ({ ...prev, visible: false }));
      }
    };

    const handleScroll = () => {
      setContextMenu(prev => ({ ...prev, visible: false }));
    };

    if (contextMenu.visible) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("scroll", handleScroll, true);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
        document.removeEventListener("scroll", handleScroll, true);
      };
    }
  }, [contextMenu.visible]);

  const toggleServer = (serverId: string) => {
    const newExpanded = new Set(expandedServers);
    if (newExpanded.has(serverId)) {
      newExpanded.delete(serverId);
      // 서버가 접히면 해당 서버의 모든 그룹도 접기
      servers
        .find((s) => s.id === serverId)
        ?.groups.forEach((group) => {
          newExpanded.delete(`${serverId}-${group.id}`);
        });
      setExpandedGroups((prev) => {
        const newGroups = new Set(prev);
        servers
          .find((s) => s.id === serverId)
          ?.groups.forEach((group) => {
            newGroups.delete(`${serverId}-${group.id}`);
          });
        return newGroups;
      });
    } else {
      newExpanded.add(serverId);
    }
    setExpandedServers(newExpanded);
  };

  const toggleGroup = (serverId: string, groupId: string) => {
    const key = `${serverId}-${groupId}`;
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedGroups(newExpanded);
  };

  const getMethodColor = (method: string) => {
    switch (method) {
      case "GET":
        return styles.methodGet;
      case "POST":
        return styles.methodPost;
      case "PUT":
        return styles.methodPut;
      case "DELETE":
        return styles.methodDelete;
      case "PATCH":
        return styles.methodPatch;
      default:
        return styles.methodDefault;
    }
  };

  const handleEndpointClick = (
    endpoint: ApiEndpoint,
    serverName: string,
    groupName: string
  ) => {
    onEndpointClick?.(endpoint, serverName, groupName);
  };

  // 서버 우클릭 핸들러
  const handleServerContextMenu = (e: React.MouseEvent, serverId: string, serverName: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      type: 'server',
      id: parseInt(serverId),
      name: serverName
    });
  };

  // 그룹 우클릭 핸들러
  const handleGroupContextMenu = (e: React.MouseEvent, serverId: string, groupId: string, groupName: string, endpointIds: string[]) => {
    e.preventDefault();
    e.stopPropagation();
    
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      type: 'group',
      id: parseInt(groupId),
      name: groupName,
      endpointIds
    });
  };

  // 엔드포인트 우클릭 핸들러
  const handleEndpointContextMenu = (e: React.MouseEvent, endpointId: string, endpointPath: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      type: 'endpoint',
      id: parseInt(endpointId),
      name: endpointPath
    });
  };

  // ActionMenu의 편집 핸들러 (빈 함수)
  const handleEdit = () => {
    setContextMenu(prev => ({ ...prev, visible: false }));
  };

  // ActionMenu의 삭제 핸들러
  const handleDelete = () => {
    const { type, id, name, endpointIds } = contextMenu;
    
    let confirmMessage = '';
    let deleteAction: (() => void) | null = null;

    switch (type) {
      case 'server':
        confirmMessage = `"${name}" 서버를 삭제하시겠습니까?\n\n⚠️ 주의사항:\n- 서버 내의 모든 그룹과 엔드포인트가 함께 삭제됩니다\n- 해당 엔드포인트들을 사용하는 테스트 히스토리의 시나리오 정보는 유지됩니다\n- 삭제 후 복구가 불가능하므로 신중하게 사용하세요\n- 엔드포인트를 참조하는 부하테스트 실행 시 오류가 발생할 수 있습니다`;
        deleteAction = () => onDeleteServer?.(id.toString());
        break;
      
      case 'group':
        confirmMessage = `"${name}" 그룹을 삭제하시겠습니까?\n\n⚠️ 주의사항:\n- 그룹 내의 모든 엔드포인트가 함께 삭제됩니다\n- 해당 엔드포인트들을 사용하는 테스트 히스토리의 시나리오 정보는 유지됩니다\n- 삭제 후 복구가 불가능하므로 신중하게 사용하세요\n- 엔드포인트를 참조하는 부하테스트 실행 시 오류가 발생할 수 있습니다`;
        deleteAction = () => endpointIds && onDeleteGroup?.('', id.toString(), endpointIds);
        break;
      
      case 'endpoint':
        confirmMessage = `"${name}" 엔드포인트를 삭제하시겠습니까?\n\n⚠️ 주의사항:\n- 해당 엔드포인트를 사용하는 테스트 히스토리의 시나리오 정보는 유지됩니다\n- 삭제 후 복구가 불가능하므로 신중하게 사용하세요\n- 엔드포인트를 참조하는 부하테스트 실행 시 오류가 발생할 수 있습니다`;
        deleteAction = () => onDeleteEndpoint?.(id.toString());
        break;
    }

    if (confirm(confirmMessage) && deleteAction) {
      deleteAction();
    }

    setContextMenu(prev => ({ ...prev, visible: false }));
  };

  // 메뉴 닫기 핸들러
  const handleMenuClose = () => {
    setContextMenu(prev => ({ ...prev, visible: false }));
  };

  return (
    <div className={styles.apiTree}>
      {servers.map((server) => (
        <div key={server.id} className={styles.serverNode}>
          {/* 서버 헤더 */}
          <div
            className={styles.serverHeader}
            onClick={() => toggleServer(server.id)}
            onContextMenu={(e) => handleServerContextMenu(e, server.id, server.name)}>
            <div className={styles.serverContent}>
              <div className={styles.itemWrapper}>
                <Database className={styles.database} />
                <span className={`CaptionLight ${styles.textContent}`} title={server.name}>
                  {server.name}
                </span>
              </div>

              {expandedServers.has(server.id) ? (
                <ChevronDown className={styles.chevron} />
              ) : (
                <ChevronRight className={styles.chevron} />
              )}
            </div>
          </div>

          {/* 서버가 펼쳐졌을 때 그룹들 표시 */}
          {expandedServers.has(server.id) && (
            <div className={styles.groupsContainer}>
              {server.groups.map((group) => {
                const groupKey = `${server.id}-${group.id}`;
                const endpointIds = group.endpoints.map(endpoint => endpoint.id);
                
                return (
                  <div key={group.id} className={styles.groupNode}>
                    {/* 그룹 헤더 */}
                    <div
                      className={styles.groupHeader}
                      onClick={() => toggleGroup(server.id, group.id)}
                      onContextMenu={(e) => handleGroupContextMenu(e, server.id, group.id, group.name, endpointIds)}>
                      <div className={styles.groupContent}>
                        <div className={styles.itemWrapper}>
                          <Folder className={styles.groupIcon} />
                          <span className={`CaptionLight ${styles.textContent}`} title={group.name}>
                            {group.name}
                          </span>
                        </div>
                        {expandedGroups.has(groupKey) ? (
                          <ChevronDown className={styles.chevron} />
                        ) : (
                          <ChevronRight className={styles.chevron} />
                        )}
                      </div>
                    </div>

                    {/* 그룹이 펼쳐졌을 때 엔드포인트들 표시 */}
                    {expandedGroups.has(groupKey) && (
                      <div className={styles.endpointsContainer}>
                        {group.endpoints.map((endpoint) => (
                          <div
                            key={endpoint.id}
                            className={styles.endpointNode}
                            onClick={() =>
                              handleEndpointClick(
                                endpoint,
                                server.name,
                                group.name
                              )
                            }
                            onContextMenu={(e) => handleEndpointContextMenu(e, endpoint.id, endpoint.path)}>
                            <div className={styles.endpointContent}>
                              <div className={styles.endpointWrapper}>
                                <Link
                                  className={`${
                                    styles.endpointIcon
                                  } ${getMethodColor(endpoint.method)}`}
                                />
                                <span 
                                  className={`CaptionLight ${styles.endpointPath}`}
                                  title={endpoint.path}
                                >
                                  {endpoint.path}
                                </span>
                              </div>

                              <span
                                className={`CaptionLight ${getMethodColor(
                                  endpoint.method
                                )} ${styles.methodText}`}>
                                {endpoint.method}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}

      {/* ActionMenu 컨텍스트 메뉴 */}
      {contextMenu.visible && (
        <ActionMenu
          projectId={contextMenu.id}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onClose={handleMenuClose}
          deleteOnly={true}
          position={{ x: contextMenu.x, y: contextMenu.y }}
        />
      )}
    </div>
  );
};

export default ApiTree;