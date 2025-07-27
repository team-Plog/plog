export interface ProjectData {
  id: number;
  title: string;
  description: string; // 요약
  detailedDescription: string; // 상세 내용
  status: "completed" | "running" | "failed" | "before";
  createdAt: string;
}

export interface ApiEndpoint {
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  endpoint: string;
  description: string;
}

export interface ApiGroup {
  groupName: string;
  baseUrl: string;
  endpoints: ApiEndpoint[];
}

export const mockProjects: ProjectData[] = [
  {
    id: 1,
    title: "MedEasy Project",
    description: "고령자 및 만성질환자를 위한 복약관리 자동화 테스트 프로젝트",
    detailedDescription: "MedEasy는 고령자 및 디지털 소외계층을 위한 복약 관리 플랫폼입니다. 본 프로젝트는 MedEasy 시스템의 주요 API들에 대해 부하 테스트를 수행하고, 로그인, 복약 등록, NFC 기반 체크, 보호자 알림 등 핵심 기능의 안정성과 확장성을 검증하는 것을 목표로 합니다. 또한, OpenAPI를 통해 자동으로 API를 가져오고, 시나리오 기반 테스트 구성이 가능하도록 설계되었습니다.",
    status: "completed",
    createdAt: "2024-01-15T09:30:00Z",
  },
  {
    id: 2,
    title: "결제 시스템 성능 테스트",
    description: "결제 처리 시스템의 동시 접속자 처리 능력을 확인합니다.",
    detailedDescription: "전자상거래 플랫폼의 결제 시스템이 대량의 동시 접속자를 처리할 수 있는지 검증하는 프로젝트입니다. 주요 테스트 대상은 결제 요청 처리, 결제 완료 처리, 환불 처리 등의 핵심 결제 API들입니다. 블랙프라이데이나 특가 이벤트 시 발생할 수 있는 트래픽 급증 상황을 시뮬레이션하여 시스템의 안정성을 확보하고자 합니다.",
    status: "running",
    createdAt: "2024-01-20T14:15:00Z",
  },
  {
    id: 3,
    title: "데이터베이스 쿼리 최적화",
    description: "복잡한 조인 쿼리의 성능을 테스트하고 최적화 방안을 도출합니다.",
    detailedDescription: "대용량 데이터베이스에서 실행되는 복잡한 조인 쿼리들의 성능을 분석하고 최적화하는 프로젝트입니다. 사용자 정보, 주문 내역, 상품 정보를 결합하는 다중 테이블 조인 쿼리의 실행 계획을 분석하고, 인덱스 최적화 및 쿼리 리팩토링을 통해 응답 시간을 단축시키는 것이 목표입니다. 다양한 데이터 볼륨에서의 성능 테스트를 통해 확장성을 검증합니다.",
    status: "failed",
    createdAt: "2024-01-18T11:45:00Z",
  },
  {
    id: 4,
    title: "신규 기능 API 테스트",
    description: "새로 개발된 API 엔드포인트들의 부하 테스트를 진행합니다.",
    detailedDescription: "최근 개발 완료된 새로운 기능들의 API 엔드포인트에 대한 종합적인 부하 테스트 프로젝트입니다. 실시간 알림 시스템, 파일 업로드/다운로드, 검색 기능 등 신규 추가된 기능들이 예상 사용자 수준의 트래픽을 안정적으로 처리할 수 있는지 검증합니다. 기능별 성능 임계점을 파악하고 운영 환경 배포 전 최종 검증을 수행합니다.",
    status: "before",
    createdAt: "2024-01-22T16:20:00Z",
  },
];

// 프로젝트별 API 그룹 데이터
export const mockApiGroups: { [projectId: string]: ApiGroup[] } = {
  "1": [
    {
      groupName: "인증 관리",
      baseUrl: "https://api.medeasy.com/auth",
      endpoints: [
        {
          method: "POST",
          endpoint: "/login",
          description: "사용자 로그인"
        },
        {
          method: "POST",
          endpoint: "/logout",
          description: "사용자 로그아웃"
        },
        {
          method: "POST",
          endpoint: "/refresh",
          description: "토큰 갱신"
        },
        {
          method: "GET",
          endpoint: "/profile",
          description: "사용자 프로필 조회"
        }
      ]
    },
    {
      groupName: "복약 관리",
      baseUrl: "https://api.medeasy.com/medication",
      endpoints: [
        {
          method: "GET",
          endpoint: "/routine",
          description: "복약 루틴 조회"
        },
        {
          method: "POST",
          endpoint: "/routine",
          description: "복약 루틴 등록"
        },
        {
          method: "PUT",
          endpoint: "/routine/{id}",
          description: "복약 루틴 수정"
        },
        {
          method: "DELETE",
          endpoint: "/routine/{id}",
          description: "복약 루틴 삭제"
        },
        {
          method: "POST",
          endpoint: "/check",
          description: "복약 체크"
        }
      ]
    },
    {
      groupName: "NFC 관리",
      baseUrl: "https://api.medeasy.com/nfc",
      endpoints: [
        {
          method: "POST",
          endpoint: "/register",
          description: "NFC 태그 등록"
        },
        {
          method: "GET",
          endpoint: "/scan/{tagId}",
          description: "NFC 태그 스캔"
        },
        {
          method: "DELETE",
          endpoint: "/tag/{id}",
          description: "NFC 태그 삭제"
        }
      ]
    },
    {
      groupName: "알림 시스템",
      baseUrl: "https://api.medeasy.com/notification",
      endpoints: [
        {
          method: "GET",
          endpoint: "/list",
          description: "알림 목록 조회"
        },
        {
          method: "POST",
          endpoint: "/send",
          description: "알림 발송"
        },
        {
          method: "PUT",
          endpoint: "/{id}/read",
          description: "알림 읽음 처리"
        }
      ]
    }
  ],
  "2": [
    {
      groupName: "결제 처리",
      baseUrl: "https://api.payment.com/pay",
      endpoints: [
        {
          method: "POST",
          endpoint: "/request",
          description: "결제 요청"
        },
        {
          method: "POST",
          endpoint: "/confirm",
          description: "결제 확인"
        },
        {
          method: "POST",
          endpoint: "/cancel",
          description: "결제 취소"
        },
        {
          method: "GET",
          endpoint: "/status/{paymentId}",
          description: "결제 상태 조회"
        }
      ]
    },
    {
      groupName: "환불 관리",
      baseUrl: "https://api.payment.com/refund",
      endpoints: [
        {
          method: "POST",
          endpoint: "/request",
          description: "환불 요청"
        },
        {
          method: "GET",
          endpoint: "/status/{refundId}",
          description: "환불 상태 조회"
        },
        {
          method: "POST",
          endpoint: "/approve",
          description: "환불 승인"
        }
      ]
    },
    {
      groupName: "결제 수단",
      baseUrl: "https://api.payment.com/method",
      endpoints: [
        {
          method: "GET",
          endpoint: "/list",
          description: "결제 수단 목록"
        },
        {
          method: "POST",
          endpoint: "/card/register",
          description: "카드 등록"
        },
        {
          method: "DELETE",
          endpoint: "/card/{cardId}",
          description: "카드 삭제"
        }
      ]
    }
  ],
  "3": [
    {
      groupName: "사용자 관리",
      baseUrl: "https://api.database.com/user",
      endpoints: [
        {
          method: "GET",
          endpoint: "/list",
          description: "사용자 목록 조회 (복잡한 조인)"
        },
        {
          method: "GET",
          endpoint: "/{id}/orders",
          description: "사용자별 주문 내역 (다중 테이블 조인)"
        },
        {
          method: "GET",
          endpoint: "/analytics",
          description: "사용자 분석 데이터 (집계 쿼리)"
        }
      ]
    },
    {
      groupName: "주문 데이터",
      baseUrl: "https://api.database.com/order",
      endpoints: [
        {
          method: "GET",
          endpoint: "/report",
          description: "주문 리포트 (복잡한 집계)"
        },
        {
          method: "GET",
          endpoint: "/statistics",
          description: "주문 통계 (다중 조인 + 그룹핑)"
        }
      ]
    }
  ],
  "4": [
    {
      groupName: "실시간 알림",
      baseUrl: "https://api.newfeature.com/notification",
      endpoints: [
        {
          method: "POST",
          endpoint: "/websocket/connect",
          description: "웹소켓 연결"
        },
        {
          method: "POST",
          endpoint: "/push/send",
          description: "푸시 알림 발송"
        },
        {
          method: "GET",
          endpoint: "/history",
          description: "알림 히스토리"
        }
      ]
    },
    {
      groupName: "파일 관리",
      baseUrl: "https://api.newfeature.com/file",
      endpoints: [
        {
          method: "POST",
          endpoint: "/upload",
          description: "파일 업로드"
        },
        {
          method: "GET",
          endpoint: "/download/{fileId}",
          description: "파일 다운로드"
        },
        {
          method: "DELETE",
          endpoint: "/{fileId}",
          description: "파일 삭제"
        },
        {
          method: "GET",
          endpoint: "/list",
          description: "파일 목록 조회"
        }
      ]
    },
    {
      groupName: "검색 기능",
      baseUrl: "https://api.newfeature.com/search",
      endpoints: [
        {
          method: "GET",
          endpoint: "/query",
          description: "통합 검색"
        },
        {
          method: "GET",
          endpoint: "/autocomplete",
          description: "자동완성"
        },
        {
          method: "POST",
          endpoint: "/index",
          description: "검색 인덱스 업데이트"
        }
      ]
    }
  ]
};

// 프로젝트 ID로 특정 프로젝트 데이터를 찾는 헬퍼 함수
export const getProjectById = (id: number): ProjectData | undefined => {
  return mockProjects.find(project => project.id === id);
};

// 프로젝트 ID로 해당 프로젝트의 API 그룹 데이터를 찾는 헬퍼 함수
export const getApiGroupsByProjectId = (projectId: string): ApiGroup[] => {
  return mockApiGroups[projectId] || [];
};