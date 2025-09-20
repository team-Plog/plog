import React, {useState, useEffect} from "react";
import {Server, Database, Link, Settings, Edit3} from "lucide-react";
import {Button} from "../../components/Button/Button";
import Header from "../../components/Header/Header";
import styles from "./Infrastructure.module.css";
import {
  getInfraPods,
  connectInfraWithOpenAPISpec,
  updateInfraResources,
} from "../../api";
import {getOpenAPIList} from "../../api";

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

const Infrastructure: React.FC = () => {
  const [infraItems, setInfraItems] = useState<InfraItem[]>([]);
  const [openAPISpecs, setOpenAPISpecs] = useState<OpenAPISpec[]>([]);
  const [infraGroups, setInfraGroups] = useState<InfraGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [selectedOpenAPI, setSelectedOpenAPI] = useState<number | null>(null);
  const [editingResources, setEditingResources] = useState<string | null>(null);
  const [resourceForm, setResourceForm] = useState({
    cpu_request: "",
    cpu_limit: "",
    memory_request: "",
    memory_limit: "",
  });

  // 인프라 목록 조회
  useEffect(() => {
    getInfraPods()
      .then((res) => {
        console.log("📦 인프라 목록:", res.data);
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
        console.log("📋 OpenAPI 목록:", res.data);
        setOpenAPISpecs(res.data.data);
      })
      .catch((err) => {
        console.error("❌ OpenAPI 목록 조회 실패:", err);
      });
  }, []);

  // 인프라 그룹화
  useEffect(() => {
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

    setInfraGroups(Object.values(groups));
  }, [infraItems]);

  // OpenAPI와 인프라 연결
  const handleConnectOpenAPI = async () => {
    if (!selectedGroup || !selectedOpenAPI) {
      alert("연결할 인프라 그룹과 OpenAPI를 선택해주세요.");
      return;
    }

    try {
      await connectInfraWithOpenAPISpec({
        openapi_spec_id: selectedOpenAPI,
        group_name: selectedGroup,
      });
      alert("연결이 완료되었습니다.");
      setSelectedGroup(null);
      setSelectedOpenAPI(null);
    } catch (err) {
      console.error("❌ 연결 실패:", err);
      alert("연결에 실패했습니다.");
    }
  };

  // 리소스 수정
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

  const handleSaveResources = async () => {
    if (!editingResources) return;

    try {
      const group = infraGroups.find((g) => g.group_name === editingResources);
      if (!group || group.pods.length === 0) {
        alert("수정할 인프라를 찾을 수 없습니다.");
        return;
      }

      // 그룹 내 모든 pod에 대해 리소스 업데이트
      const updatePromises = group.pods.map((pod) => {
        const data: any = {group_name: editingResources};

        // 밀리코어 단위로 변환 (m 제거하고 숫자만)
        if (resourceForm.cpu_request) {
          data.cpu_request_millicores = resourceForm.cpu_request.replace(
            "m",
            ""
          );
        }
        if (resourceForm.cpu_limit) {
          data.cpu_limit_millicores = resourceForm.cpu_limit.replace("m", "");
        }

        // MB 단위로 변환 (Mi, Gi 등 제거하고 숫자만)
        if (resourceForm.memory_request) {
          let memoryRequest = resourceForm.memory_request.replace(
            /[^0-9]/g,
            ""
          );
          if (resourceForm.memory_request.includes("Gi")) {
            memoryRequest = String(parseInt(memoryRequest) * 1024);
          }
          data.memory_request_millicores = memoryRequest;
        }
        if (resourceForm.memory_limit) {
          let memoryLimit = resourceForm.memory_limit.replace(/[^0-9]/g, "");
          if (resourceForm.memory_limit.includes("Gi")) {
            memoryLimit = String(parseInt(memoryLimit) * 1024);
          }
          data.memory_limit_millicores = memoryLimit;
        }

        return updateInfraResources(pod.server_infra_id, data);
      });

      await Promise.all(updatePromises);

      alert("리소스 설정이 저장되었습니다.");
      setEditingResources(null);

      // 데이터 새로고침
      const res = await getInfraPods();
      setInfraItems(res.data.data);
    } catch (err) {
      console.error("❌ 리소스 저장 실패:", err);
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
        {/* Main Content */}
        <main className={styles.main}>
          {/* Connection Section */}
          <div className={styles.connectionSection}>
            <h2 className={`TitleL ${styles.sectionTitle}`}>
              OpenAPI와 인프라 연결
            </h2>
            <div className={styles.connectionControls}>
              <div className={styles.selectGroup}>
                <label>인프라 그룹 선택:</label>
                <select
                  value={selectedGroup || ""}
                  onChange={(e) => setSelectedGroup(e.target.value || null)}
                  className={styles.select}>
                  <option value="">그룹을 선택하세요</option>
                  {infraGroups.map((group) => (
                    <option key={group.group_name} value={group.group_name}>
                      {group.group_name} ({group.service_type})
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.selectGroup}>
                <label>OpenAPI 선택:</label>
                <select
                  value={selectedOpenAPI || ""}
                  onChange={(e) =>
                    setSelectedOpenAPI(
                      e.target.value ? parseInt(e.target.value) : null
                    )
                  }
                  className={styles.select}>
                  <option value="">OpenAPI를 선택하세요</option>
                  {/*openAPISpecs.map((spec) => (
                    <option
                      key={spec.openapi_spec_id}
                      value={spec.openapi_spec_id}>
                      {spec.title} (v{spec.version})
                    </option>
                  ))*/}
                </select>
              </div>
              <Button
                variant="primaryGradient"
                onClick={handleConnectOpenAPI}
                icon={<Link />}
                disabled={!selectedGroup || !selectedOpenAPI}>
                연결하기
              </Button>
            </div>
          </div>

          {/* Infrastructure Groups */}
          <div className={styles.groupsSection}>
            <h2 className={styles.sectionTitle}>배포된 인프라 목록</h2>
            {infraGroups.length > 0 ? (
              <div className={styles.groupsGrid}>
                {infraGroups.map((group) => (
                  <div key={group.group_name} className={styles.groupCard}>
                    <div className={styles.groupHeader}>
                      <div className={styles.groupInfo}>
                        {getServiceIcon(group.service_type)}
                        <div>
                          <h3 className={`TitleS ${styles.groupName}`}>
                            {group.group_name}
                          </h3>
                          <span className={`Body ${styles.serviceType}`}>
                            {group.service_type}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleEditResources(group.group_name)}
                        className={styles.editButton}>
                        <Edit3 className={styles.editIcon} />
                      </button>
                    </div>

                    <div className={styles.podsSection}>
                      <h4 className={`CaptionBold ${styles.podsTitle}`}>
                        Pod 목록 ({group.pods.length}개)
                      </h4>
                      <div className={styles.podsList}>
                        {group.pods.map((pod) => (
                          <div
                            key={pod.server_infra_id}
                            className={styles.podItem}>
                            <div className={`CaptionLight ${styles.podName}`}>
                              {pod.pod_name}
                            </div>
                            <div className={`CaptionLight ${styles.podSpecs}`}>
                              CPU:{" "}
                              {pod.resource_specs.cpu_request_millicores || 0}m
                              - {pod.resource_specs.cpu_limit_millicores || "∞"}
                              m
                              <br />
                              Memory:{" "}
                              {pod.resource_specs.memory_request_mb || 0}MB -{" "}
                              {pod.resource_specs.memory_limit_mb || "∞"}MB
                              <br />
                              Port:{" "}
                              {pod.service_info.port.length > 0
                                ? pod.service_info.port.join(", ")
                                : "-"}
                              <br />
                              NodePort:{" "}
                              {pod.service_info.node_port.length > 0
                                ? pod.service_info.node_port.join(", ")
                                : "-"}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={`HeadingS ${styles.emptyTitle}`}>
                <Settings className={styles.emptyIcon} />
                <h3 className={styles.emptyTitle}>배포된 인프라가 없습니다</h3>
                <p className={`Body ${styles.emptyDescription}`}>
                  K3S 환경에 배포된 애플리케이션이 없습니다.
                </p>
              </div>
            )}
          </div>
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
                  <label>CPU Request (밀리코어):</label>
                  <input
                    type="text"
                    value={resourceForm.cpu_request}
                    onChange={(e) =>
                      setResourceForm({
                        ...resourceForm,
                        cpu_request: e.target.value,
                      })
                    }
                    placeholder="예: 200"
                    className={styles.input}
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>CPU Limit (밀리코어):</label>
                  <input
                    type="text"
                    value={resourceForm.cpu_limit}
                    onChange={(e) =>
                      setResourceForm({
                        ...resourceForm,
                        cpu_limit: e.target.value,
                      })
                    }
                    placeholder="예: 1000"
                    className={styles.input}
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Memory Request (MB):</label>
                  <input
                    type="text"
                    value={resourceForm.memory_request}
                    onChange={(e) =>
                      setResourceForm({
                        ...resourceForm,
                        memory_request: e.target.value,
                      })
                    }
                    placeholder="예: 512 또는 1Gi"
                    className={styles.input}
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Memory Limit (MB):</label>
                  <input
                    type="text"
                    value={resourceForm.memory_limit}
                    onChange={(e) =>
                      setResourceForm({
                        ...resourceForm,
                        memory_limit: e.target.value,
                      })
                    }
                    placeholder="예: 2048 또는 2Gi"
                    className={styles.input}
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
