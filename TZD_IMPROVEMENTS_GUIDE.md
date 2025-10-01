# 🛠️ TZDReader: Практические Улучшения для Стабильности

**Сопутствующий документ к:** TZD_ARCHITECTURE_REVIEW.md  
**Фокус:** Готовые к использованию решения и код

---

## 🎯 Краткое Руководство по Внедрению

Этот документ содержит конкретные решения для улучшения стабильности TZDReader агента. Каждое улучшение включает:
- ✅ Готовый код
- 📝 Инструкции по интеграции
- 🧪 Примеры тестов
- 📊 Метрики для мониторинга

---

## 1️⃣ Улучшенная Обработка Ошибок

### Создание файла `agents/tzd_reader/exceptions.py`

```python
"""
Специализированные исключения для TZDReader
Обеспечивают точную диагностику и обработку ошибок
"""
from typing import Dict, Any, Optional


class TZDReaderError(Exception):
    """Базовое исключение для всех ошибок TZDReader"""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False
    ):
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация для API ответов"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'recoverable': self.recoverable
        }


class ValidationError(TZDReaderError):
    """Ошибки валидации входных данных"""
    def __init__(self, message: str, field: str = None, **kwargs):
        details = {'field': field} if field else {}
        super().__init__(message, details=details, recoverable=True, **kwargs)


class EmptyFileListError(ValidationError):
    """Пустой список файлов"""
    def __init__(self):
        super().__init__("File list cannot be empty", field="files")


class TooManyFilesError(ValidationError):
    """Слишком много файлов"""
    def __init__(self, count: int, max_count: int = 20):
        super().__init__(
            f"Too many files: {count} (max: {max_count})",
            field="files",
            details={'count': count, 'max_count': max_count}
        )


class ParsingError(TZDReaderError):
    """Ошибки парсинга документов"""
    def __init__(self, message: str, file_path: str = None, **kwargs):
        details = {'file_path': file_path} if file_path else {}
        super().__init__(message, details=details, recoverable=False, **kwargs)


class EmptyContentError(ParsingError):
    """Не удалось извлечь содержимое"""
    def __init__(self, file_path: str):
        super().__init__(
            f"Could not extract text from file",
            file_path=file_path
        )


class AIServiceError(TZDReaderError):
    """Ошибки взаимодействия с AI сервисом"""
    def __init__(
        self, 
        message: str, 
        provider: str = None,
        model: str = None,
        **kwargs
    ):
        details = {}
        if provider:
            details['provider'] = provider
        if model:
            details['model'] = model
        super().__init__(message, details=details, recoverable=False, **kwargs)


class TemporaryError(TZDReaderError):
    """Временные ошибки, требующие повторной попытки"""
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        details = {'retry_after': retry_after} if retry_after else {}
        super().__init__(message, details=details, recoverable=True, **kwargs)


class RateLimitError(TemporaryError):
    """Превышен лимит запросов"""
    def __init__(self, provider: str, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded for {provider}",
            retry_after=retry_after,
            details={'provider': provider}
        )


class TimeoutError(TemporaryError):
    """Таймаут операции"""
    def __init__(self, operation: str, timeout: int):
        super().__init__(
            f"Operation '{operation}' timed out after {timeout}s",
            details={'operation': operation, 'timeout': timeout}
        )


class ConfigurationError(TZDReaderError):
    """Ошибки конфигурации"""
    def __init__(self, message: str, config_key: str = None, **kwargs):
        details = {'config_key': config_key} if config_key else {}
        super().__init__(message, details=details, recoverable=False, **kwargs)
```

### Интеграция в `agent.py`

```python
# В начале файла
from .exceptions import (
    TZDReaderError,
    ValidationError,
    EmptyFileListError,
    TooManyFilesError,
    ParsingError,
    EmptyContentError,
    AIServiceError,
    TemporaryError,
    RateLimitError,
    TimeoutError,
    ConfigurationError
)

# Обновить tzd_reader функцию
def tzd_reader(
    files: List[str], 
    engine: str = "gpt", 
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Main function with improved error handling"""
    
    # Валидация входных данных
    if not files:
        raise EmptyFileListError()
    
    if len(files) > 20:
        raise TooManyFilesError(count=len(files))
    
    if engine.lower() not in ['gpt', 'claude', 'auto']:
        raise ValidationError(
            f"Unsupported AI engine: {engine}",
            field="engine",
            details={'supported': ['gpt', 'claude', 'auto']}
        )
    
    start_time = time.time()
    
    try:
        combined_text = _process_files_with_parsers(files, base_dir)
        
        if not combined_text.strip():
            raise EmptyContentError("Could not extract text from any file")
        
        analyzer = SecureAIAnalyzer()
        
        # ... остальная логика ...
        
    except (ValidationError, SecurityError, ParsingError) as e:
        # Ожидаемые ошибки - пробрасываем дальше
        logger.error(f"Expected error in tzd_reader: {e}", exc_info=True)
        raise
        
    except TemporaryError as e:
        # Временные ошибки - логируем и пробрасываем
        logger.warning(f"Temporary error in tzd_reader: {e}")
        raise
        
    except Exception as e:
        # Неожиданные ошибки - оборачиваем в TZDReaderError
        logger.error(f"Unexpected error in tzd_reader: {e}", exc_info=True)
        raise TZDReaderError(
            f"Unexpected error during analysis: {str(e)}",
            details={'error_type': type(e).__name__}
        ) from e
```

### Обработка в роутере

```python
# app/routers/tzd_router.py
from agents.tzd_reader.exceptions import (
    TZDReaderError,
    ValidationError,
    TemporaryError
)

@router.post("/analyze")
async def analyze_tzd_documents(...):
    try:
        result = tzd_reader(files=file_paths, engine=ai_engine)
        # ... success handling ...
        
    except ValidationError as e:
        # Ошибки валидации - 400 Bad Request
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
        
    except TemporaryError as e:
        # Временные ошибки - 503 Service Unavailable
        retry_after = e.details.get('retry_after', 60)
        raise HTTPException(
            status_code=503,
            detail=e.to_dict(),
            headers={'Retry-After': str(retry_after)}
        )
        
    except TZDReaderError as e:
        # Другие ошибки TZDReader - 500 Internal Server Error
        logger.error(f"TZD analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=e.to_dict()
        )
        
    except Exception as e:
        # Неожиданные ошибки
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                'error_type': 'UnexpectedError',
                'message': 'An unexpected error occurred',
                'recoverable': False
            }
        )
```

---

## 2️⃣ Retry-логика с Exponential Backoff

### Установка зависимости

```bash
pip install tenacity
```

### Обновление `agent.py`

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

class SecureAIAnalyzer:
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(TemporaryError),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def analyze_with_llm_service_with_retry(
        self, 
        text: str, 
        provider: str = "claude"
    ) -> Dict[str, Any]:
        """Анализ с автоматическими повторами при временных сбоях"""
        
        try:
            response = await self.llm_service.run_prompt(
                provider=provider,
                prompt=text,
                system_prompt=self.get_analysis_prompt(),
                model=self._get_model(provider),
                max_tokens=4000
            )
            
            if not response.get("success"):
                error_msg = response.get("error", "Unknown error")
                
                # Определяем тип ошибки
                if self._is_rate_limit_error(error_msg):
                    raise RateLimitError(provider=provider, retry_after=60)
                elif self._is_timeout_error(error_msg):
                    raise TimeoutError(operation="llm_analysis", timeout=60)
                elif self._is_temporary_error(error_msg):
                    raise TemporaryError(f"Temporary error: {error_msg}")
                else:
                    raise AIServiceError(
                        f"AI service error: {error_msg}",
                        provider=provider
                    )
            
            # Обработка успешного ответа
            result_text = response.get("content", "")
            if not result_text:
                raise AIServiceError("Empty response from LLM service")
            
            json_text = self._extract_json_from_response(result_text)
            result = json.loads(json_text)
            
            # Добавляем метаданные
            result['ai_model'] = response.get("model")
            result['provider'] = provider
            result['retry_count'] = getattr(self, '_retry_count', 0)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {e}")
            raise AIServiceError(
                f"Invalid JSON response: {e}",
                provider=provider
            )
    
    def _is_rate_limit_error(self, error_msg: str) -> bool:
        """Проверка на rate limit ошибку"""
        rate_limit_keywords = [
            'rate limit',
            'too many requests',
            'quota exceeded',
            '429'
        ]
        return any(kw in error_msg.lower() for kw in rate_limit_keywords)
    
    def _is_timeout_error(self, error_msg: str) -> bool:
        """Проверка на timeout ошибку"""
        timeout_keywords = ['timeout', 'timed out', 'deadline exceeded']
        return any(kw in error_msg.lower() for kw in timeout_keywords)
    
    def _is_temporary_error(self, error_msg: str) -> bool:
        """Проверка на временную ошибку"""
        temporary_keywords = [
            'temporary',
            'service unavailable',
            'connection error',
            '503',
            '502'
        ]
        return any(kw in error_msg.lower() for kw in temporary_keywords)
    
    def _get_model(self, provider: str) -> str:
        """Получение модели для провайдера"""
        if provider == "claude":
            return self.claude_model
        elif provider == "openai":
            return self.openai_model
        else:
            return "auto"
```

### Тесты для retry-логики

```python
# tests/test_retry_logic.py
import pytest
from unittest.mock import AsyncMock, patch
from agents.tzd_reader.agent import SecureAIAnalyzer
from agents.tzd_reader.exceptions import RateLimitError, TemporaryError

@pytest.mark.asyncio
async def test_retry_on_rate_limit():
    """Проверка повторных попыток при rate limit"""
    analyzer = SecureAIAnalyzer()
    
    # Мокируем LLM service
    with patch.object(analyzer, 'llm_service') as mock_llm:
        # Первые 2 попытки - rate limit, третья - успех
        mock_llm.run_prompt = AsyncMock(side_effect=[
            {'success': False, 'error': 'Rate limit exceeded'},
            {'success': False, 'error': 'Rate limit exceeded'},
            {
                'success': True,
                'content': '{"project_object": "Test"}',
                'model': 'gpt-4'
            }
        ])
        
        result = await analyzer.analyze_with_llm_service_with_retry(
            text="Test text",
            provider="openai"
        )
        
        assert result['project_object'] == "Test"
        assert mock_llm.run_prompt.call_count == 3

@pytest.mark.asyncio
async def test_retry_exhausted():
    """Проверка исчерпания попыток"""
    analyzer = SecureAIAnalyzer()
    
    with patch.object(analyzer, 'llm_service') as mock_llm:
        # Все попытки - rate limit
        mock_llm.run_prompt = AsyncMock(return_value={
            'success': False,
            'error': 'Rate limit exceeded'
        })
        
        with pytest.raises(RateLimitError):
            await analyzer.analyze_with_llm_service_with_retry(
                text="Test text",
                provider="openai"
            )
        
        assert mock_llm.run_prompt.call_count == 3
```

---

## 3️⃣ Структурированное Логирование

### Установка зависимостей

```bash
pip install structlog python-json-logger
```

### Обновление `utils/logging_config.py`

```python
"""
Конфигурация структурированного логирования для TZDReader
"""
import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

import structlog
from pythonjsonlogger import jsonlogger


def setup_structured_logging(log_level: str = "INFO"):
    """
    Настройка структурированного логирования
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    """
    
    # Создаем директорию для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Настройка стандартного logging
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            },
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/tzd_reader.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "json",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/tzd_reader_errors.log",
                "maxBytes": 10485760,
                "backupCount": 5,
                "formatter": "json",
                "level": "ERROR",
            },
        },
        "root": {
            "handlers": ["console", "file", "error_file"],
            "level": log_level,
        },
        "loggers": {
            "agents.tzd_reader": {
                "handlers": ["console", "file", "error_file"],
                "level": log_level,
                "propagate": False,
            },
        },
    })
    
    # Настройка structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Получить структурированный логгер
    
    Args:
        name: Имя модуля
        
    Returns:
        Настроенный structlog логгер
    """
    return structlog.get_logger(name)


# Utility функции для контекстного логирования
class LogContext:
    """Менеджер контекста для логирования"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
    
    def __enter__(self):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.clear_contextvars()
```

### Использование в `agent.py`

```python
from utils.logging_config import get_logger, LogContext
import uuid

logger = get_logger(__name__)

def tzd_reader(
    files: List[str], 
    engine: str = "gpt", 
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Main function with structured logging"""
    
    # Генерируем уникальный ID запроса
    request_id = str(uuid.uuid4())
    
    # Создаем контекст логирования
    with LogContext(
        request_id=request_id,
        component="tzd_reader",
        files_count=len(files),
        engine=engine
    ):
        logger.info(
            "analysis_started",
            files=[Path(f).name for f in files]
        )
        
        start_time = time.time()
        
        try:
            # Валидация
            if not files:
                logger.error("validation_failed", reason="empty_file_list")
                raise EmptyFileListError()
            
            logger.debug("validation_passed")
            
            # Парсинг файлов
            logger.info("parsing_started")
            combined_text = _process_files_with_parsers(files, base_dir)
            logger.info(
                "parsing_completed",
                text_length=len(combined_text)
            )
            
            # AI анализ
            logger.info("ai_analysis_started", provider=engine)
            analyzer = SecureAIAnalyzer()
            result = analyzer.analyze_with_gpt(combined_text)
            logger.info(
                "ai_analysis_completed",
                ai_model=result.get('ai_model')
            )
            
            # Формирование результата
            duration = time.time() - start_time
            result['processing_metadata'] = {
                'request_id': request_id,
                'processed_files': len(files),
                'processing_time_seconds': round(duration, 2),
                'ai_engine': engine.lower(),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(
                "analysis_completed_successfully",
                duration=duration,
                processed_files=len(files)
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "analysis_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration=duration,
                exc_info=True
            )
            raise
```

---

## 4️⃣ Мониторинг и Метрики

### Установка Prometheus client

```bash
pip install prometheus-client
```

### Создание `agents/tzd_reader/monitoring.py`

```python
"""
Мониторинг и метрики для TZDReader
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time
from typing import Callable, Any
from contextlib import contextmanager

# Счетчики
tzd_requests_total = Counter(
    'tzd_requests_total',
    'Total number of TZD analysis requests',
    ['engine', 'status']
)

tzd_files_processed_total = Counter(
    'tzd_files_processed_total',
    'Total number of files processed',
    ['file_type', 'status']
)

tzd_errors_total = Counter(
    'tzd_errors_total',
    'Total number of errors',
    ['error_type', 'recoverable']
)

# Гистограммы (для латентности)
tzd_processing_duration_seconds = Histogram(
    'tzd_processing_duration_seconds',
    'Time spent processing TZD requests',
    ['engine', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

tzd_file_size_bytes = Histogram(
    'tzd_file_size_bytes',
    'Size of processed files in bytes',
    ['file_type'],
    buckets=[1024, 10240, 102400, 1048576, 10485760]  # 1KB to 10MB
)

# Gauge (текущие значения)
tzd_active_requests = Gauge(
    'tzd_active_requests',
    'Number of active TZD requests'
)

# Info (статическая информация)
tzd_info = Info(
    'tzd_info',
    'Information about TZD Reader service'
)

# Установка статической информации
tzd_info.info({
    'version': '2.0',
    'supported_engines': 'gpt,claude,auto',
    'max_file_size_mb': '10',
    'supported_formats': 'pdf,docx,txt'
})


class MetricsCollector:
    """Сборщик метрик для TZDReader"""
    
    @staticmethod
    @contextmanager
    def track_request(engine: str):
        """
        Контекстный менеджер для отслеживания запроса
        
        Usage:
            with MetricsCollector.track_request("gpt"):
                result = tzd_reader(files, "gpt")
        """
        tzd_active_requests.inc()
        start_time = time.time()
        status = "error"
        
        try:
            yield
            status = "success"
        finally:
            duration = time.time() - start_time
            tzd_processing_duration_seconds.labels(
                engine=engine,
                operation="full_analysis"
            ).observe(duration)
            tzd_requests_total.labels(engine=engine, status=status).inc()
            tzd_active_requests.dec()
    
    @staticmethod
    def track_file(file_path: str, file_size: int, status: str = "success"):
        """Отслеживание обработки файла"""
        from pathlib import Path
        file_type = Path(file_path).suffix.lstrip('.')
        
        tzd_files_processed_total.labels(
            file_type=file_type,
            status=status
        ).inc()
        
        tzd_file_size_bytes.labels(file_type=file_type).observe(file_size)
    
    @staticmethod
    def track_error(error: Exception, recoverable: bool = False):
        """Отслеживание ошибки"""
        error_type = type(error).__name__
        tzd_errors_total.labels(
            error_type=error_type,
            recoverable=str(recoverable).lower()
        ).inc()
    
    @staticmethod
    def track_operation(operation: str):
        """
        Декоратор для отслеживания операций
        
        Usage:
            @MetricsCollector.track_operation("parsing")
            def parse_file(file_path):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                engine = kwargs.get('engine', 'unknown')
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    tzd_processing_duration_seconds.labels(
                        engine=engine,
                        operation=operation
                    ).observe(duration)
            
            return wrapper
        return decorator


# Вспомогательные функции
def get_metrics_summary() -> dict:
    """Получение сводки метрик для health check"""
    from prometheus_client import REGISTRY
    
    metrics = {}
    for collector in REGISTRY._collector_to_names:
        if hasattr(collector, '_name') and collector._name.startswith('tzd_'):
            metrics[collector._name] = collector._value.get()
    
    return metrics
```

### Интеграция метрик в `agent.py`

```python
from .monitoring import MetricsCollector

def tzd_reader(
    files: List[str], 
    engine: str = "gpt", 
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Main function with metrics"""
    
    with MetricsCollector.track_request(engine):
        try:
            # ... основная логика ...
            
            # Отслеживаем каждый файл
            for file_path in files:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    MetricsCollector.track_file(
                        file_path, 
                        file_size, 
                        status="success"
                    )
            
            return result
            
        except Exception as e:
            # Отслеживаем ошибку
            recoverable = isinstance(e, (ValidationError, TemporaryError))
            MetricsCollector.track_error(e, recoverable=recoverable)
            raise

# Декорирование вспомогательных функций
@MetricsCollector.track_operation("parsing")
def _process_files_with_parsers(files: List[str], base_dir: Optional[str] = None) -> str:
    """Process files with metrics tracking"""
    # ... существующий код ...
```

### Добавление метрик эндпоинта

```python
# app/main.py
from prometheus_client import make_asgi_app

# Создаем ASGI приложение для метрик
metrics_app = make_asgi_app()

# Монтируем метрики
app.mount("/metrics", metrics_app)
```

### Health check с метриками

```python
# app/routers/tzd_router.py
from agents.tzd_reader.monitoring import get_metrics_summary

@router.get("/health/metrics")
async def health_with_metrics():
    """Health check с метриками производительности"""
    return {
        "service": "TZD Reader",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": get_metrics_summary()
    }
```

---

## 5️⃣ Асинхронная Обработка Файлов

### Обновление `agent.py` для async

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict, Any, Optional

async def _process_single_file_async(
    file_path: str,
    base_dir: Optional[str],
    validator: FileSecurityValidator,
    doc_parser
) -> Optional[Dict[str, str]]:
    """Асинхронная обработка одного файла"""
    
    try:
        # Валидация (быстрая, в основном потоке)
        validator.validate_all(file_path, base_dir)
        
        # Парсинг (медленный, в отдельном процессе)
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor() as executor:
            text = await loop.run_in_executor(
                executor,
                doc_parser.parse,
                file_path
            )
        
        if text and text.strip():
            normalized_text = normalize_diacritics(text)
            return {
                'file_path': file_path,
                'text': normalized_text,
                'size': len(normalized_text)
            }
        
        logger.warning(f"Empty text in file: {file_path}")
        return None
        
    except SecurityError as e:
        logger.error(f"Security validation failed for {file_path}: {e}")
        raise
        
    except Exception as e:
        logger.error(f"File processing error {file_path}: {e}")
        return None


async def _process_files_async(
    files: List[str],
    base_dir: Optional[str] = None
) -> str:
    """Асинхронная параллельная обработка файлов"""
    
    validator = FileSecurityValidator()
    doc_parser = DocParser()
    
    # Создаем задачи для всех файлов
    tasks = [
        _process_single_file_async(file_path, base_dir, validator, doc_parser)
        for file_path in files
    ]
    
    # Выполняем параллельно
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Фильтруем и собираем результаты
    text_parts = []
    processed_count = 0
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Processing exception: {result}")
            continue
        
        if result is None:
            continue
        
        file_header = f"\n=== File: {Path(result['file_path']).name} ===\n"
        text_parts.extend([file_header, result['text'], "\n"])
        processed_count += 1
    
    if not text_parts:
        raise EmptyContentError("Could not extract text from any file")
    
    combined_text = ''.join(text_parts)
    logger.info(f"Processed {processed_count}/{len(files)} files, {len(combined_text)} chars")
    
    return combined_text


# Синхронная обертка для обратной совместимости
def _process_files_with_parsers(
    files: List[str],
    base_dir: Optional[str] = None
) -> str:
    """Синхронная обертка над асинхронной обработкой"""
    return asyncio.run(_process_files_async(files, base_dir))
```

---

## 6️⃣ Кеширование Результатов

### Создание `agents/tzd_reader/cache.py`

```python
"""
Кеширование результатов TZDReader для повышения производительности
"""
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TZDCache:
    """
    Кеш результатов анализа TZDReader
    
    Features:
    - Хеширование содержимого файлов для определения уникальности
    - LRU eviction при превышении лимита
    - TTL для автоматического истечения кеша
    """
    
    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600  # 1 час
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Вычисление SHA256 хеша файла"""
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                # Читаем файл частями для экономии памяти
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            # В случае ошибки используем путь и время модификации
            stat = Path(file_path).stat()
            fallback = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.sha256(fallback.encode()).hexdigest()
    
    def _generate_cache_key(
        self,
        files: List[str],
        engine: str
    ) -> str:
        """Генерация ключа кеша на основе файлов и движка"""
        # Сортируем файлы для консистентности
        sorted_files = sorted(files)
        
        # Вычисляем хеши всех файлов
        file_hashes = [self._compute_file_hash(f) for f in sorted_files]
        
        # Комбинируем хеши с движком
        combined = f"{','.join(file_hashes)}|{engine.lower()}"
        
        # Возвращаем короткий хеш
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(
        self,
        files: List[str],
        engine: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получение результата из кеша
        
        Returns:
            Cached result or None if not found or expired
        """
        cache_key = self._generate_cache_key(files, engine)
        
        if cache_key not in self._cache:
            logger.debug(f"Cache miss for key: {cache_key[:16]}...")
            return None
        
        # Проверяем TTL
        cache_time = self._access_times[cache_key]
        age = time.time() - cache_time
        
        if age > self.ttl_seconds:
            logger.info(f"Cache expired for key: {cache_key[:16]}... (age: {age}s)")
            self._remove(cache_key)
            return None
        
        # Обновляем время доступа (для LRU)
        self._access_times[cache_key] = time.time()
        
        logger.info(f"Cache hit for key: {cache_key[:16]}... (age: {age}s)")
        return self._cache[cache_key].copy()
    
    def set(
        self,
        files: List[str],
        engine: str,
        result: Dict[str, Any]
    ) -> None:
        """Сохранение результата в кеш"""
        cache_key = self._generate_cache_key(files, engine)
        
        # Если кеш полон, удаляем самый старый элемент (LRU)
        if len(self._cache) >= self.max_size and cache_key not in self._cache:
            self._evict_lru()
        
        # Сохраняем результат
        self._cache[cache_key] = result.copy()
        self._access_times[cache_key] = time.time()
        
        logger.info(
            f"Cached result for key: {cache_key[:16]}... "
            f"(cache size: {len(self._cache)}/{self.max_size})"
        )
    
    def _evict_lru(self) -> None:
        """Удаление наименее недавно использованного элемента"""
        if not self._access_times:
            return
        
        # Находим ключ с самым старым временем доступа
        oldest_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        self._remove(oldest_key)
        logger.debug(f"Evicted LRU entry: {oldest_key[:16]}...")
    
    def _remove(self, cache_key: str) -> None:
        """Удаление элемента из кеша"""
        self._cache.pop(cache_key, None)
        self._access_times.pop(cache_key, None)
    
    def clear(self) -> None:
        """Очистка всего кеша"""
        count = len(self._cache)
        self._cache.clear()
        self._access_times.clear()
        logger.info(f"Cache cleared ({count} entries removed)")
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика кеша"""
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds,
            'usage_percent': (len(self._cache) / self.max_size * 100) if self.max_size > 0 else 0
        }


# Глобальный экземпляр кеша
_global_cache = TZDCache()


def get_cache() -> TZDCache:
    """Получение глобального экземпляра кеша"""
    return _global_cache
```

### Интеграция кеша в `agent.py`

```python
from .cache import get_cache

def tzd_reader(
    files: List[str],
    engine: str = "gpt",
    base_dir: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Main function with caching"""
    
    cache = get_cache()
    
    # Проверяем кеш (если включен)
    if use_cache:
        cached_result = cache.get(files, engine)
        if cached_result:
            logger.info("Using cached result")
            cached_result['from_cache'] = True
            cached_result['cache_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return cached_result
    
    # Выполняем анализ
    start_time = time.time()
    
    try:
        # ... существующая логика анализа ...
        
        result = {
            # ... результат анализа ...
            'from_cache': False
        }
        
        # Сохраняем в кеш (если включен)
        if use_cache:
            cache.set(files, engine, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise
```

### API для управления кешем

```python
# app/routers/tzd_router.py
from agents.tzd_reader.cache import get_cache

@router.get("/cache/stats")
async def get_cache_stats():
    """Статистика кеша"""
    cache = get_cache()
    return cache.get_stats()

@router.post("/cache/clear")
async def clear_cache():
    """Очистка кеша"""
    cache = get_cache()
    cache.clear()
    return {"message": "Cache cleared successfully"}
```

---

## 📊 Проверка Эффективности Улучшений

### Скрипт для нагрузочного тестирования

```python
# tests/load_test.py
"""
Нагрузочное тестирование TZDReader
"""
import asyncio
import time
from pathlib import Path
import statistics

async def test_concurrent_requests(file_path: str, num_requests: int = 10):
    """Тест параллельных запросов"""
    from agents.tzd_reader import TZDReader
    
    reader = TZDReader(engine="gpt")
    
    async def single_request():
        start = time.time()
        try:
            result = reader.analyze([file_path])
            return time.time() - start, True
        except Exception as e:
            return time.time() - start, False
    
    # Запускаем параллельно
    tasks = [single_request() for _ in range(num_requests)]
    results = await asyncio.gather(*tasks)
    
    # Анализ результатов
    durations = [r[0] for r in results]
    successes = [r[1] for r in results]
    
    print(f"\n=== Load Test Results ===")
    print(f"Total requests: {num_requests}")
    print(f"Successful: {sum(successes)}")
    print(f"Failed: {num_requests - sum(successes)}")
    print(f"\nDuration statistics:")
    print(f"  Min: {min(durations):.2f}s")
    print(f"  Max: {max(durations):.2f}s")
    print(f"  Mean: {statistics.mean(durations):.2f}s")
    print(f"  Median: {statistics.median(durations):.2f}s")


if __name__ == "__main__":
    test_file = "test_data/sample.pdf"
    asyncio.run(test_concurrent_requests(test_file, num_requests=20))
```

---

## ✅ Чеклист Внедрения

### Фаза 1: Базовые Улучшения (Неделя 1)
- [ ] Создать `exceptions.py` с иерархией исключений
- [ ] Обновить `agent.py` для использования новых исключений
- [ ] Обновить `tzd_router.py` для правильной обработки ошибок
- [ ] Добавить retry-логику с tenacity
- [ ] Написать тесты для новых исключений

### Фаза 2: Логирование и Мониторинг (Неделя 2)
- [ ] Установить structlog и настроить `logging_config.py`
- [ ] Обновить все логирование на структурированное
- [ ] Создать `monitoring.py` с метриками Prometheus
- [ ] Интегрировать метрики в `agent.py`
- [ ] Добавить `/metrics` эндпоинт

### Фаза 3: Производительность (Неделя 3)
- [ ] Реализовать асинхронную обработку файлов
- [ ] Создать систему кеширования (`cache.py`)
- [ ] Интегрировать кеш в `agent.py`
- [ ] Добавить API для управления кешем
- [ ] Провести нагрузочное тестирование

### Фаза 4: Финализация (Неделя 4)
- [ ] Обновить документацию
- [ ] Написать интеграционные тесты
- [ ] Настроить CI/CD для проверки метрик
- [ ] Провести код-ревью
- [ ] Развернуть в production

---

## 📞 Поддержка

При возникновении вопросов обращайтесь:
- **Документация:** [TZD_ARCHITECTURE_REVIEW.md](./TZD_ARCHITECTURE_REVIEW.md)
- **Issues:** GitHub Issues
- **Logs:** `logs/tzd_reader.log`, `logs/tzd_reader_errors.log`

---

**Версия:** 1.0  
**Дата:** 2024-01-10  
**Статус:** Ready for Implementation
