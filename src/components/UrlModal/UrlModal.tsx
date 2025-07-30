import React, {useState} from "react";
import styles from "./UrlModal.module.css";
import {InputField} from "../Input";
import {Button} from "../Button/Button";
import EndPoint from "../../assets/images/endPoint.svg";
import {analyzeOpenAPI} from "../../api";

interface UrlModalProps {
  onClose: () => void;
  projectId: number;
  onSuccess?: () => void; // API 등록 성공 시 호출될 콜백
}

const UrlModal: React.FC<UrlModalProps> = ({onClose, projectId, onSuccess}) => {
  const [apiUrl, setApiUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    if (!apiUrl.trim()) {
      setError("API 문서 URL을 입력해주세요.");
      return;
    }

    // URL 형식 간단 검증
    try {
      new URL(apiUrl);
    } catch {
      setError("올바른 URL 형식을 입력해주세요.");
      return;
    }

    setIsLoading(true);
    setError("");

    console.log("✉️ 전송 projectID: ", projectId, ", url: ", apiUrl);

    try {
      await analyzeOpenAPI({
        project_id: projectId,
        open_api_url: apiUrl,
      });

      console.log("✅ API 명세 분석 및 등록 성공");
      
      // 성공 시 콜백 호출 (부모 컴포넌트에서 데이터 새로고침 등을 위해)
      if (onSuccess) {
        onSuccess();
      }
      
      onClose();
    } catch (err) {
      console.error("❌ API 명세 분석 실패:", err);
      
      // 에러 메시지 설정
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { message?: string } } };
        if (axiosError.response?.data?.message) {
          setError(axiosError.response.data.message);
        } else {
          setError("API 명세 분석 중 오류가 발생했습니다.");
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("API 명세 분석 중 오류가 발생했습니다.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* 이미지 영역 */}
        <div className={styles.imageSection}>
          <div className={styles.imageContainer}>
            <img src={EndPoint} className={styles.image} />
          </div>
        </div>

        {/* 입력 영역 */}
        <div className={styles.contentSection}>
          <div className={styles.inputContainer}>
            <InputField
              title="API 문서 URL"
              placeholder="예: https://example.com/api-docs"
              value={apiUrl}
              onChange={setApiUrl}
            />
            
            {error && (
              <div className={styles.errorMessage}>
                {error}
              </div>
            )}

            <div className={styles.buttonGroup}>
              <Button 
                variant="secondary" 
                onClick={onClose}
                disabled={isLoading}
              >
                취소
              </Button>
              <Button 
                variant="primaryGradient" 
                onClick={handleSave}
                disabled={isLoading}
              >
                {isLoading ? "분석 중..." : "추가하기"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UrlModal;