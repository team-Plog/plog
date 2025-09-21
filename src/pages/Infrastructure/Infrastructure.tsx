import React, {useState, useEffect} from "react";
import {Server, Database} from "lucide-react";
import {Button} from "../../components/Button/Button";
import InputField from "../../components/Input/InputField";
import Header from "../../components/Header/Header";
import styles from "./Infrastructure.module.css";
import {
  getInfraPods,
  connectInfraWithOpenAPISpec,
  updateInfraResources,
} from "../../api";
import {getOpenAPIList} from "../../api";
import Xarrow from "react-xarrows";

interface InfraItem {
  server_infra_id: number;
  pod_name: string;
  resource_type: string;
  service_type: "SERVER" | "DATABASE";
  group_name: string;
  label: Record<string, string>;
  namespace: string;
  resource_specs: {
    cpu_request_millicores: number;
    cpu_limit_millicores: number;
    memory_request_mb: number;
    memory_limit_mb: number;
  };
  service_info: {
    port: number[];
    node_port: number[];
  };
  openapi_spec_id?: number;
}

interface OpenAPISpec {
  id: number;
  title: string;
  version: string;
  base_url: string;
  commit_hash: string | null;
  created_at: string;
}

interface InfraGroup {
  group_name: string;
  service_type: "SERVER" | "DATABASE";
  pods: InfraItem[];
  connectedOpenAPI?: OpenAPISpec;
}

interface Connection {
  apiId: number;
  groupName: string;
  type: "auto" | "manual"; // 🔑 자동 / 수동 구분
}

const Infrastructure: React.FC = () => {
  const [infraItems, setInfraItems] = useState<InfraItem[]>([]);
  const [openAPISpecs, setOpenAPISpecs] = useState<OpenAPISpec[]>([]);
  const [infraGroups, setInfraGroups] = useState<InfraGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<InfraGroup | null>(null);
  const [editingResources, setEditingResources] = useState<string | null>(null);
  const [resourceForm, setResourceForm] = useState({
    cpu_request: "",
    cpu_limit: "",
    memory_request: "",
    memory_limit: "",
  });
  const [connections, setConnections] = useState<Connection[]>([]);

  // 인프라 목록 조회
  useEffect(() => {
    getInfraPods()
      .then((res) => {
        setInfraItems(res.data.data);
      })
      .catch((err) => {
        console.error("❌ 인프라 목록 조회 실패:", err);
      });
  }, []);

  // OpenAPI 목록 조회
  useEffect(() => {
    getOpenAPIList()
      .then((res) => {
        setOpenAPISpecs(res.data.data);
      })
      .catch((err) => {
        console.error("❌ OpenAPI 목록 조회 실패:", err);
      });
  }, []);

  // 인프라 그룹화 + OpenAPI 자동 매칭
  useEffect(() => {
    if (infraItems.length === 0 || openAPISpecs.length === 0) return;

    const groups: {[key: string]: InfraGroup} = {};
    infraItems.forEach((item) => {
      if (!groups[item.group_name]) {
        groups[item.group_name] = {
          group_name: item.group_name,
          service_type: item.service_type,
          pods: [],
        };
      }
      groups[item.group_name].pods.push(item);
    });

    const newGroups: InfraGroup[] = [];
    const newConnections: Connection[] = [];

    Object.values(groups).forEach((group) => {
      const firstPod = group.pods[0];

      if (firstPod?.openapi_spec_id) {
        const matchedApi = openAPISpecs.find(
          (api) => api.id === firstPod.openapi_spec_id
        );
        if (matchedApi) {
          newGroups.push({...group, connectedOpenAPI: matchedApi});

          // 🔑 자동 연결은 blue
          newConnections.push({
            apiId: matchedApi.id,
            groupName: group.group_name,
            type: "auto",
          });
          return;
        }
      }

      newGroups.push(group);
    });

    setInfraGroups(newGroups);
    setConnections(newConnections);
  }, [infraItems, openAPISpecs]);

  // OpenAPI ↔ Infra 수동 연결
  // 수동 연결
  const handleConnectOpenAPI = async (openapiId: number, groupName: string) => {
    const data = {openapi_spec_id: openapiId, group_name: groupName};

    try {
      await connectInfraWithOpenAPISpec(data);

      const matchedApi = openAPISpecs.find((s) => s.id === openapiId);
      setInfraGroups((prev) =>
        prev.map((g) =>
          g.group_name === groupName ? {...g, connectedOpenAPI: matchedApi} : g
        )
      );

      setConnections((prev) => [
        ...prev,
        {apiId: openapiId, groupName, type: "manual"},
      ]);

      setInfraItems((prev) =>
        prev.map((item) =>
          item.group_name === groupName
            ? {...item, openapi_spec_id: openapiId}
            : item
        )
      );
    } catch (err: any) {
      console.error("❌ 연결 실패:", err.response?.data || err.message);
      alert("연결 실패");
    }
  };

  // 리소스 수정 모달 열기
  const handleEditResources = (groupName: string) => {
    setEditingResources(groupName);
    const group = infraGroups.find((g) => g.group_name === groupName);
    if (group && group.pods.length > 0) {
      const specs = group.pods[0].resource_specs;
      setResourceForm({
        cpu_request: specs.cpu_request_millicores
          ? `${specs.cpu_request_millicores}`
          : "",
        cpu_limit: specs.cpu_limit_millicores
          ? `${specs.cpu_limit_millicores}`
          : "",
        memory_request: specs.memory_request_mb
          ? `${specs.memory_request_mb}`
          : "",
        memory_limit: specs.memory_limit_mb ? `${specs.memory_limit_mb}` : "",
      });
    }
  };

  // 리소스 저장
  const handleSaveResources = async () => {
    if (!editingResources) return;

    try {
      const data: any = {group_name: editingResources};

      if (resourceForm.cpu_request) {
        data.cpu_request_millicores = resourceForm.cpu_request.endsWith("m")
          ? resourceForm.cpu_request
          : `${resourceForm.cpu_request}m`;
      }
      if (resourceForm.cpu_limit) {
        data.cpu_limit_millicores = resourceForm.cpu_limit.endsWith("m")
          ? resourceForm.cpu_limit
          : `${resourceForm.cpu_limit}m`;
      }
      if (resourceForm.memory_request) {
        data.memory_request_millicores = /[0-9]+(Mi|Gi)$/.test(
          resourceForm.memory_request
        )
          ? resourceForm.memory_request
          : `${resourceForm.memory_request}Mi`;
      }
      if (resourceForm.memory_limit) {
        data.memory_limit_millicores = /[0-9]+(Mi|Gi)$/.test(
          resourceForm.memory_limit
        )
          ? resourceForm.memory_limit
          : `${resourceForm.memory_limit}Mi`;
      }

      await updateInfraResources(data);
      alert("리소스 설정이 저장되었습니다.");
      setEditingResources(null);

      const res = await getInfraPods();
      setInfraItems(res.data.data);
    } catch (err: any) {
      console.error("❌ 리소스 저장 실패:", err.response?.data || err.message);
      alert("리소스 저장에 실패했습니다.");
    }
  };

  const getServiceIcon = (serviceType: string) => {
    return serviceType === "SERVER" ? (
      <Server className={styles.typeIcon} />
    ) : (
      <Database className={styles.typeIcon} />
    );
  };

  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.content}>
        <main className={styles.main}>
          <div className={styles.groupRow}>
            {/* OpenAPI 그룹 */}
            <div className={styles.groupBox}>
              <h2 className="TitleL">API 그룹</h2>
              {openAPISpecs.map((spec) => (
                <div
                  id={`api-${spec.id}`}
                  key={spec.id}
                  draggable
                  onDragStart={(e) =>
                    e.dataTransfer.setData("openapiId", spec.id.toString())
                  }
                  className={styles.card}>
                  <h3 className="TitleS">{spec.title}</h3>
                  <p className="CaptionLight">버전: {spec.version}</p>
                  <p className="CaptionLight">{spec.base_url}</p>
                </div>
              ))}
            </div>

            {/* Infra 그룹 */}
            <div className={styles.groupBox}>
              <h2 className="TitleL">Infra 그룹</h2>
              {infraGroups.map((group) => (
                <div
                  id={`infra-${group.group_name}`}
                  key={group.group_name}
                  className={`${styles.card} ${
                    selectedGroup?.group_name === group.group_name
                      ? styles.activeCard
                      : ""
                  }`}
                  onClick={() => setSelectedGroup(group)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    const openapiId = parseInt(
                      e.dataTransfer.getData("openapiId")
                    );
                    handleConnectOpenAPI(openapiId, group.group_name);
                  }}>
                  <div className={styles.groupHeader}>
                    {getServiceIcon(group.service_type)}
                    <div>
                      <h3 className="TitleS">{group.group_name}</h3>
                      <span className="CaptionLight">{group.service_type}</span>
                    </div>
                  </div>
                  {group.connectedOpenAPI && (
                    <p className="CaptionLight">
                      연결된 API: {group.connectedOpenAPI.title}
                    </p>
                  )}

                  {group.pods.length > 0 && (
                    <p className="CaptionLight">
                      Port:{" "}
                      {group.pods[0].service_info.port.length > 0
                        ? group.pods[0].service_info.port.join(", ")
                        : "-"}{" "}
                      | NodePort:{" "}
                      {group.pods[0].service_info.node_port.length > 0
                        ? group.pods[0].service_info.node_port.join(", ")
                        : "-"}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* Pod 그룹 */}
            <div className={styles.groupBox}>
              <h2 className="TitleL">Pod 그룹</h2>
              {selectedGroup ? (
                selectedGroup.pods.map((pod) => (
                  <div key={pod.server_infra_id} className={styles.podCard}>
                    <h4 className="TitleS">{pod.pod_name}</h4>
                    <p className="CaptionLight">{pod.service_type}</p>
                    <p className="CaptionLight">
                      CPU: {pod.resource_specs.cpu_request_millicores}m /{" "}
                      {pod.resource_specs.cpu_limit_millicores}m
                    </p>
                    <p className="CaptionLight">
                      Memory: {pod.resource_specs.memory_request_mb}MB /{" "}
                      {pod.resource_specs.memory_limit_mb}MB
                    </p>
                    <Button
                      variant="secondary"
                      onClick={() => handleEditResources(pod.group_name)}>
                      값 수정
                    </Button>
                  </div>
                ))
              ) : (
                <p className="CaptionLight">Infra 그룹을 선택하세요.</p>
              )}
            </div>
          </div>

          {/* 연결선 (react-xarrows) */}
          {connections.map((c, idx) => (
            <Xarrow
              key={idx}
              start={`api-${c.apiId}`}
              end={`infra-${c.groupName}`}
              color={c.type === "auto" ? "blue" : "green"}
              strokeWidth={2}
              headSize={5}
            />
          ))}
        </main>

        {/* Resource Edit Modal */}
        {editingResources && (
          <div className={styles.modal}>
            <div className={styles.modalContent}>
              <h3 className={`HeadingS ${styles.modalTitle}`}>
                리소스 설정 - {editingResources}
              </h3>
              <div className={styles.formGrid}>
                <div className={styles.formGroup}>
                  <label>CPU Request:</label>
                  <InputField
                    value={resourceForm.cpu_request}
                    onChange={(value) =>
                      setResourceForm({
                        ...resourceForm,
                        cpu_request: value,
                      })
                    }
                    placeholder="예: 300 (자동 m 붙음)"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>CPU Limit:</label>
                  <InputField
                    value={resourceForm.cpu_limit}
                    onChange={(value) =>
                      setResourceForm({
                        ...resourceForm,
                        cpu_limit: value,
                      })
                    }
                    placeholder="예: 1000 (자동 m 붙음)"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Memory Request:</label>
                  <InputField
                    value={resourceForm.memory_request}
                    onChange={(value) =>
                      setResourceForm({
                        ...resourceForm,
                        memory_request: value,
                      })
                    }
                    placeholder="예: 512 (Mi 자동), 2Gi"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Memory Limit:</label>
                  <InputField
                    value={resourceForm.memory_limit}
                    onChange={(value) =>
                      setResourceForm({
                        ...resourceForm,
                        memory_limit: value,
                      })
                    }
                    placeholder="예: 2048 (Mi 자동), 2Gi"
                  />
                </div>
              </div>
              <div className={styles.modalActions}>
                <Button
                  variant="secondary"
                  onClick={() => setEditingResources(null)}>
                  취소
                </Button>
                <Button variant="primaryGradient" onClick={handleSaveResources}>
                  저장
                </Button>
              </div>
            </div>
            <div
              className={styles.modalOverlay}
              onClick={() => setEditingResources(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Infrastructure;
