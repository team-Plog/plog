export interface ProjectData {
  id: string;
  title: string;
  description: string; // 요약
  detailedDescription: string; // 상세 내용
  status: "completed" | "running" | "failed" | "before";
  createdAt: string;
}

export const mockProjects: ProjectData[] = [
  {
    id: "1",
    title: "MedEasy Project",
    description: "고령자 및 만성질환자를 위한 복약관리 자동화 테스트 프로젝트",
    detailedDescription: "MedEasy는 고령자 및 디지털 소외계층을 위한 복약 관리 플랫폼입니다. 본 프로젝트는 MedEasy 시스템의 주요 API들에 대해 부하 테스트를 수행하고, 로그인, 복약 등록, NFC 기반 체크, 보호자 알림 등 핵심 기능의 안정성과 확장성을 검증하는 것을 목표로 합니다. 또한, OpenAPI를 통해 자동으로 API를 가져오고, 시나리오 기반 테스트 구성이 가능하도록 설계되었습니다.",
    status: "completed",
    createdAt: "2024-01-15T09:30:00Z",
  },
  {
    id: "2",
    title: "결제 시스템 성능 테스트",
    description: "결제 처리 시스템의 동시 접속자 처리 능력을 확인합니다.",
    detailedDescription: "전자상거래 플랫폼의 결제 시스템이 대량의 동시 접속자를 처리할 수 있는지 검증하는 프로젝트입니다. 주요 테스트 대상은 결제 요청 처리, 결제 완료 처리, 환불 처리 등의 핵심 결제 API들입니다. 블랙프라이데이나 특가 이벤트 시 발생할 수 있는 트래픽 급증 상황을 시뮬레이션하여 시스템의 안정성을 확보하고자 합니다.",
    status: "running",
    createdAt: "2024-01-20T14:15:00Z",
  },
  {
    id: "3",
    title: "데이터베이스 쿼리 최적화",
    description: "복잡한 조인 쿼리의 성능을 테스트하고 최적화 방안을 도출합니다.",
    detailedDescription: "대용량 데이터베이스에서 실행되는 복잡한 조인 쿼리들의 성능을 분석하고 최적화하는 프로젝트입니다. 사용자 정보, 주문 내역, 상품 정보를 결합하는 다중 테이블 조인 쿼리의 실행 계획을 분석하고, 인덱스 최적화 및 쿼리 리팩토링을 통해 응답 시간을 단축시키는 것이 목표입니다. 다양한 데이터 볼륨에서의 성능 테스트를 통해 확장성을 검증합니다.",
    status: "failed",
    createdAt: "2024-01-18T11:45:00Z",
  },
  {
    id: "4",
    title: "신규 기능 API 테스트",
    description: "새로 개발된 API 엔드포인트들의 부하 테스트를 진행합니다.",
    detailedDescription: "최근 개발 완료된 새로운 기능들의 API 엔드포인트에 대한 종합적인 부하 테스트 프로젝트입니다. 실시간 알림 시스템, 파일 업로드/다운로드, 검색 기능 등 신규 추가된 기능들이 예상 사용자 수준의 트래픽을 안정적으로 처리할 수 있는지 검증합니다. 기능별 성능 임계점을 파악하고 운영 환경 배포 전 최종 검증을 수행합니다.",
    status: "before",
    createdAt: "2024-01-22T16:20:00Z",
  },
];

// 프로젝트 ID로 특정 프로젝트 데이터를 찾는 헬퍼 함수
export const getProjectById = (id: string): ProjectData | undefined => {
  return mockProjects.find(project => project.id === id);
};