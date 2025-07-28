import React, {useState} from "react";
import {ChevronDown, ChevronRight, Folder, Link, Database} from "lucide-react";
import styles from "./ApiTree.module.css";

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
}

const ApiTree: React.FC<ApiTreeProps> = ({servers, onEndpointClick}) => {
  const [expandedServers, setExpandedServers] = useState<Set<string>>(
    new Set()
  );
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

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

  return (
    <div className={styles.apiTree}>
      {servers.map((server) => (
        <div key={server.id} className={styles.serverNode}>
          {/* 서버 헤더 */}
          <div
            className={styles.serverHeader}
            onClick={() => toggleServer(server.id)}>
            <div className={styles.serverContent}>
              <div className={styles.itemWrapper}>
                <Database className={styles.database} />
                <span className="CaptionLight">{server.name}</span>
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
                return (
                  <div key={group.id} className={styles.groupNode}>
                    {/* 그룹 헤더 */}
                    <div
                      className={styles.groupHeader}
                      onClick={() => toggleGroup(server.id, group.id)}>
                      <div className={styles.groupContent}>
                        <div className={styles.itemWrapper}>
                          <Folder className={styles.groupIcon} />
                          <span className="CaptionLight">{group.name}</span>
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
                            }>
                            <div className={styles.endpointContent}>
                              <div className={styles.itemWrapper}>
                                <Link
                                  className={`${
                                    styles.endpointIcon
                                  } ${getMethodColor(endpoint.method)}`}
                                />
                                <span className="CaptionLight">
                                  {endpoint.path}
                                </span>
                              </div>

                              <span
                                className={`CaptionLight ${getMethodColor(
                                  endpoint.method
                                )}`}>
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
    </div>
  );
};

export default ApiTree;
