export interface ProjectData {
  id: number;
  title: string;
  summary: string; // description -> summary로 변경
  description: string; // detailedDescription -> description으로 변경
  status: "completed" | "running" | "failed" | "before";
  createdAt: string;
}

export interface ApiEndpoint {
  id: number;
  path: string; // endpoint -> path로 변경
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  summary: string; // description -> summary로 변경
  description: string;
}

export interface ApiTag {
  id: number;
  name: string; // groupName -> name으로 변경
  description: string;
  endpoints: ApiEndpoint[];
}

export interface OpenApiSpec {
  id: number;
  title: string;
  version: string;
  base_url: string; // baseUrl -> base_url로 변경
  tags: ApiTag[];
}

export interface ApiTestConfig {
  id: string;
  endpoint: string;
}

export const mockProjects: ProjectData[] = [
  {
    id: 1,
    title: "MedEasy Project",
    summary: "고령자 및 만성질환자를 위한 복약관리 자동화 테스트 프로젝트",
    description: "MedEasy는 고령자 및 디지털 소외계층을 위한 복약 관리 플랫폼입니다. 본 프로젝트는 MedEasy 시스템의 주요 API들에 대해 부하 테스트를 수행하고, 로그인, 복약 등록, NFC 기반 체크, 보호자 알림 등 핵심 기능의 안정성과 확장성을 검증하는 것을 목표로 합니다. 또한, OpenAPI를 통해 자동으로 API를 가져오고, 시나리오 기반 테스트 구성이 가능하도록 설계되었습니다.",
    status: "completed",
    createdAt: "2024-01-15T09:30:00Z",
  },
  {
    id: 2,
    title: "결제 시스템 성능 테스트",
    summary: "결제 처리 시스템의 동시 접속자 처리 능력을 확인합니다.",
    description: "전자상거래 플랫폼의 결제 시스템이 대량의 동시 접속자를 처리할 수 있는지 검증하는 프로젝트입니다. 주요 테스트 대상은 결제 요청 처리, 결제 완료 처리, 환불 처리 등의 핵심 결제 API들입니다. 블랙프라이데이나 특가 이벤트 시 발생할 수 있는 트래픽 급증 상황을 시뮬레이션하여 시스템의 안정성을 확보하고자 합니다.",
    status: "running",
    createdAt: "2024-01-20T14:15:00Z",
  },
  {
    id: 3,
    title: "데이터베이스 쿼리 최적화",
    summary: "복잡한 조인 쿼리의 성능을 테스트하고 최적화 방안을 도출합니다.",
    description: "대용량 데이터베이스에서 실행되는 복잡한 조인 쿼리들의 성능을 분석하고 최적화하는 프로젝트입니다. 사용자 정보, 주문 내역, 상품 정보를 결합하는 다중 테이블 조인 쿼리의 실행 계획을 분석하고, 인덱스 최적화 및 쿼리 리팩토링을 통해 응답 시간을 단축시키는 것이 목표입니다. 다양한 데이터 볼륨에서의 성능 테스트를 통해 확장성을 검증합니다.",
    status: "failed",
    createdAt: "2024-01-18T11:45:00Z",
  },
  {
    id: 4,
    title: "신규 기능 API 테스트",
    summary: "새로 개발된 API 엔드포인트들의 부하 테스트를 진행합니다.",
    description: "최근 개발 완료된 새로운 기능들의 API 엔드포인트에 대한 종합적인 부하 테스트 프로젝트입니다. 실시간 알림 시스템, 파일 업로드/다운로드, 검색 기능 등 신규 추가된 기능들이 예상 사용자 수준의 트래픽을 안정적으로 처리할 수 있는지 검증합니다. 기능별 성능 임계점을 파악하고 운영 환경 배포 전 최종 검증을 수행합니다.",
    status: "before",
    createdAt: "2024-01-22T16:20:00Z",
  },
];

// 프로젝트별 OpenAPI 스펙 데이터 (실제 API 응답 구조에 맞춤)
export const mockOpenApiSpecs: { [projectId: string]: OpenApiSpec[] } = {
  "1": [
    {
      id: 1,
      title: "MedEasy API",
      version: "v1",
      base_url: "https://api.medeasy.com",
      tags: [
        {
          id: 1,
          name: "인증 관리",
          description: "사용자 인증 및 토큰 관리 API",
          endpoints: [
            {
              id: 1,
              path: "/auth/login",
              method: "POST",
              summary: "사용자 로그인",
              description: "이메일과 비밀번호로 로그인"
            },
            {
              id: 2,
              path: "/auth/logout",
              method: "POST",
              summary: "사용자 로그아웃",
              description: "현재 세션을 종료"
            },
            {
              id: 3,
              path: "/auth/refresh",
              method: "POST",
              summary: "토큰 갱신",
              description: "만료된 토큰을 새로 발급"
            },
            {
              id: 4,
              path: "/auth/profile",
              method: "GET",
              summary: "사용자 프로필 조회",
              description: "현재 로그인한 사용자 정보 조회"
            }
          ]
        },
        {
          id: 2,
          name: "복약 관리",
          description: "복약 일정 및 체크 관리 API",
          endpoints: [
            {
              id: 5,
              path: "/medication/routine",
              method: "GET",
              summary: "복약 루틴 조회",
              description: "사용자의 복약 일정 조회"
            },
            {
              id: 6,
              path: "/medication/routine",
              method: "POST",
              summary: "복약 루틴 등록",
              description: "새로운 복약 일정 등록"
            },
            {
              id: 7,
              path: "/medication/routine/{id}",
              method: "PUT",
              summary: "복약 루틴 수정",
              description: "기존 복약 일정 수정"
            },
            {
              id: 8,
              path: "/medication/check",
              method: "POST",
              summary: "복약 체크",
              description: "복약 완료 체크"
            }
          ]
        }
      ]
    }
  ],
  "2": [
    {
      id: 1,
      title: "Payment API",
      version: "v2",
      base_url: "https://api.payment.com",
      tags: [
        {
          id: 1,
          name: "결제 처리",
          description: "결제 요청 및 처리 API",
          endpoints: [
            {
              id: 1,
              path: "/pay/request",
              method: "POST",
              summary: "결제 요청",
              description: "새로운 결제 요청 생성"
            },
            {
              id: 2,
              path: "/pay/confirm",
              method: "POST",
              summary: "결제 확인",
              description: "결제 승인 처리"
            },
            {
              id: 3,
              path: "/pay/cancel",
              method: "POST",
              summary: "결제 취소",
              description: "진행 중인 결제 취소"
            },
            {
              id: 4,
              path: "/pay/status/{paymentId}",
              method: "GET",
              summary: "결제 상태 조회",
              description: "결제 ID로 현재 상태 확인"
            }
          ]
        },
        {
          id: 2,
          name: "환불 관리",
          description: "환불 요청 및 처리 API",
          endpoints: [
            {
              id: 5,
              path: "/refund/request",
              method: "POST",
              summary: "환불 요청",
              description: "결제 완료된 건에 대한 환불 요청"
            },
            {
              id: 6,
              path: "/refund/status/{refundId}",
              method: "GET",
              summary: "환불 상태 조회",
              description: "환불 처리 진행 상황 확인"
            },
            {
              id: 7,
              path: "/refund/approve",
              method: "POST",
              summary: "환불 승인",
              description: "관리자 환불 승인 처리"
            },
            {
              id: 8,
              path: "/refund/reject",
              method: "POST",
              summary: "환불 거부",
              description: "환불 요청 거부 처리"
            }
          ]
        },
        {
          id: 3,
          name: "결제 수단",
          description: "결제 수단 관리 API",
          endpoints: [
            {
              id: 9,
              path: "/method/list",
              method: "GET",
              summary: "결제 수단 목록",
              description: "사용 가능한 결제 수단 조회"
            },
            {
              id: 10,
              path: "/method/card/register",
              method: "POST",
              summary: "카드 등록",
              description: "새로운 결제 카드 등록"
            },
            {
              id: 11,
              path: "/method/card/{cardId}",
              method: "DELETE",
              summary: "카드 삭제",
              description: "등록된 카드 정보 삭제"
            },
            {
              id: 12,
              path: "/method/card/{cardId}/validate",
              method: "POST",
              summary: "카드 유효성 검증",
              description: "등록된 카드의 유효성 확인"
            }
          ]
        }
      ]
    }
  ],
  "3": [
    {
      id: 1,
      title: "Database Optimization API",
      version: "v1",
      base_url: "https://api.database.com",
      tags: [
        {
          id: 1,
          name: "사용자 관리",
          description: "사용자 데이터 조회 및 분석 API",
          endpoints: [
            {
              id: 1,
              path: "/user/list",
              method: "GET",
              summary: "사용자 목록 조회",
              description: "복잡한 조인을 포함한 사용자 목록 조회"
            },
            {
              id: 2,
              path: "/user/{id}/orders",
              method: "GET",
              summary: "사용자별 주문 내역",
              description: "다중 테이블 조인으로 주문 내역 조회"
            },
            {
              id: 3,
              path: "/user/analytics",
              method: "GET",
              summary: "사용자 분석 데이터",
              description: "집계 쿼리를 통한 사용자 행동 분석"
            },
            {
              id: 4,
              path: "/user/statistics/monthly",
              method: "GET",
              summary: "월별 사용자 통계",
              description: "월별 신규 가입자 및 활성 사용자 통계"
            }
          ]
        },
        {
          id: 2,
          name: "주문 데이터",
          description: "주문 관련 복합 쿼리 API",
          endpoints: [
            {
              id: 5,
              path: "/order/report",
              method: "GET",
              summary: "주문 리포트",
              description: "복잡한 집계를 통한 주문 현황 리포트"
            },
            {
              id: 6,
              path: "/order/statistics",
              method: "GET",
              summary: "주문 통계",
              description: "다중 조인과 그룹핑을 통한 주문 통계"
            },
            {
              id: 7,
              path: "/order/performance/analysis",
              method: "GET",
              summary: "성능 분석",
              description: "쿼리 실행 계획 및 성능 분석 데이터"
            }
          ]
        },
        {
          id: 3,
          name: "상품 데이터",
          description: "상품 관련 최적화 쿼리 API",
          endpoints: [
            {
              id: 8,
              path: "/product/popular",
              method: "GET",
              summary: "인기 상품 조회",
              description: "복합 인덱스를 활용한 인기 상품 조회"
            },
            {
              id: 9,
              path: "/product/recommendation/{userId}",
              method: "GET",
              summary: "상품 추천",
              description: "사용자 기반 협업 필터링 추천"
            }
          ]
        }
      ]
    }
  ],
  "4": [
    {
      id: 1,
      title: "New Feature API",
      version: "v1",
      base_url: "https://api.newfeature.com",
      tags: [
        {
          id: 1,
          name: "실시간 알림",
          description: "실시간 알림 및 푸시 서비스 API",
          endpoints: [
            {
              id: 1,
              path: "/notification/websocket/connect",
              method: "POST",
              summary: "웹소켓 연결",
              description: "실시간 알림을 위한 웹소켓 연결"
            },
            {
              id: 2,
              path: "/notification/push/send",
              method: "POST",
              summary: "푸시 알림 발송",
              description: "타겟 사용자에게 푸시 알림 전송"
            },
            {
              id: 3,
              path: "/notification/history",
              method: "GET",
              summary: "알림 히스토리",
              description: "사용자별 알림 발송 이력 조회"
            },
            {
              id: 4,
              path: "/notification/subscribe",
              method: "POST",
              summary: "알림 구독",
              description: "특정 토픽에 대한 알림 구독"
            },
            {
              id: 5,
              path: "/notification/unsubscribe",
              method: "DELETE",
              summary: "알림 구독 해제",
              description: "알림 구독 취소"
            }
          ]
        },
        {
          id: 2,
          name: "파일 관리",
          description: "파일 업로드/다운로드 및 관리 API",
          endpoints: [
            {
              id: 6,
              path: "/file/upload",
              method: "POST",
              summary: "파일 업로드",
              description: "멀티파트 파일 업로드"
            },
            {
              id: 7,
              path: "/file/download/{fileId}",
              method: "GET",
              summary: "파일 다운로드",
              description: "파일 ID로 파일 다운로드"
            },
            {
              id: 8,
              path: "/file/{fileId}",
              method: "DELETE",
              summary: "파일 삭제",
              description: "업로드된 파일 삭제"
            },
            {
              id: 9,
              path: "/file/list",
              method: "GET",
              summary: "파일 목록 조회",
              description: "사용자별 업로드 파일 목록"
            },
            {
              id: 10,
              path: "/file/metadata/{fileId}",
              method: "GET",
              summary: "파일 메타데이터",
              description: "파일 정보 및 메타데이터 조회"
            }
          ]
        },
        {
          id: 3,
          name: "검색 기능",
          description: "통합 검색 및 자동완성 API",
          endpoints: [
            {
              id: 11,
              path: "/search/query",
              method: "GET",
              summary: "통합 검색",
              description: "전체 콘텐츠 대상 통합 검색"
            },
            {
              id: 12,
              path: "/search/autocomplete",
              method: "GET",
              summary: "자동완성",
              description: "검색어 자동완성 제안"
            },
            {
              id: 13,
              path: "/search/index",
              method: "POST",
              summary: "검색 인덱스 업데이트",
              description: "검색 인덱스 데이터 갱신"
            },
            {
              id: 14,
              path: "/search/trending",
              method: "GET",
              summary: "인기 검색어",
              description: "실시간 인기 검색어 조회"
            },
            {
              id: 15,
              path: "/search/filter",
              method: "POST",
              summary: "필터 검색",
              description: "조건별 필터링 검색"
            }
          ]
        }
      ]
    }
  ]
};

// 프로젝트 ID로 특정 프로젝트 데이터를 찾는 헬퍼 함수
export const getProjectById = (id: number): ProjectData | undefined => {
  return mockProjects.find(project => project.id === id);
};

// 프로젝트 ID로 해당 프로젝트의 OpenAPI 스펙 데이터를 찾는 헬퍼 함수
export const getOpenApiSpecsByProjectId = (projectId: string): OpenApiSpec[] => {
  return mockOpenApiSpecs[projectId] || [];
};