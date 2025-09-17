"""
파일 저장을 위한 범용 유틸리티 클래스
안전한 파일 저장 기능 제공
"""
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileWriter:
    """범용 파일 저장을 위한 유틸리티 클래스"""
    
    @staticmethod
    def write_to_path(content: str, filename: str, base_path: str, subfolder: Optional[str] = None) -> str:
        """
        지정된 경로에 파일을 저장
        
        Args:
            content: 저장할 파일 내용
            filename: 저장할 파일명
            base_path: 기본 저장 경로
            subfolder: 선택적 하위 폴더 경로
            
        Returns:
            str: 저장된 파일의 전체 경로
            
        Raises:
            OSError: 파일 저장 실패시
        """
        # 기본 경로 설정
        target_path = Path(base_path)
        
        # 하위 폴더가 있다면 추가
        if subfolder:
            target_path = target_path / subfolder
        
        # 디렉터리 생성 (존재하지 않으면)
        target_path.mkdir(parents=True, exist_ok=True)
        
        # 파일 경로 생성
        file_path = target_path / filename
        
        try:
            # 파일 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"파일이 성공적으로 저장되었습니다: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"파일 저장 실패 - 경로: {file_path}, 오류: {str(e)}")
            raise OSError(f"파일 저장에 실패했습니다: {str(e)}")
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> bool:
        """
        디렉터리가 존재하는지 확인하고, 없으면 생성
        
        Args:
            directory_path: 확인/생성할 디렉터리 경로
            
        Returns:
            bool: 디렉터리가 존재하거나 성공적으로 생성되었는지 여부
        """
        try:
            Path(directory_path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"디렉터리 생성 실패 - 경로: {directory_path}, 오류: {str(e)}")
            return False
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        파일이 존재하는지 확인
        
        Args:
            file_path: 확인할 파일 경로
            
        Returns:
            bool: 파일 존재 여부
        """
        return Path(file_path).exists()
    
    @staticmethod
    def remove_file(file_path: str) -> bool:
        """
        파일을 제거
        
        Args:
            file_path: 제거할 파일 경로
            
        Returns:
            bool: 제거 성공 여부
        """
        try:
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                file_path_obj.unlink()
                logger.info(f"파일이 성공적으로 제거되었습니다: {file_path}")
                return True
            else:
                logger.warning(f"제거하려는 파일이 존재하지 않습니다: {file_path}")
                return False
        except Exception as e:
            logger.error(f"파일 제거 실패 - 경로: {file_path}, 오류: {str(e)}")
            return False
    
    @staticmethod
    def read_from_path(file_path: str) -> str:
        """
        지정된 경로에서 파일을 읽음
        
        Args:
            file_path: 읽을 파일 경로
            
        Returns:
            str: 파일 내용
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            OSError: 파일 읽기 실패시
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"파일을 성공적으로 읽었습니다: {file_path}")
            return content
            
        except FileNotFoundError:
            logger.error(f"파일을 찾을 수 없습니다: {file_path}")
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        except Exception as e:
            logger.error(f"파일 읽기 실패 - 경로: {file_path}, 오류: {str(e)}")
            raise OSError(f"파일 읽기에 실패했습니다: {str(e)}")