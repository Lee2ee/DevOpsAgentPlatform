from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        """프롬프트를 보내고 텍스트 응답을 반환한다."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """AI 서비스 연결 가능 여부를 반환한다."""
        ...
