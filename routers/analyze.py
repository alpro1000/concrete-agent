# routers/analyze.py
from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import tempfile
import logging
from typing import List

# Import the hybrid analyze function
from agents.concrete_agent_hybrid import analyze_concrete

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/concrete/advanced")
async def analyze_concrete_advanced(
    docs: List[UploadFile] = File(..., description="Project documentation files"),
    smeta: UploadFile = File(..., description="Budget/estimate file"),
    use_claude: bool = True,
    claude_mode: str = "enhancement"  # enhancement | primary | fallback
):
    """
    Расширенный анализ бетонных конструкций с настраиваемыми параметрами
    
    Claude modes:
    - enhancement: Claude только для улучшения сложных случаев (по умолчанию)
    - primary: всегда используем Claude для максимальной точности
    - fallback: Claude только если локальный анализ ничего не нашел
    """
    if not docs:
        raise HTTPException(status_code=400, detail="Необходимо загрузить хотя бы один документ")
    
    if claude_mode not in ["enhancement", "primary", "fallback"]:
        raise HTTPException(status_code=400, detail="Неверный claude_mode. Используйте: enhancement, primary, fallback")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_paths = []

            # Сохраняем документы
            for i, doc in enumerate(docs):
                if not doc.filename:
                    continue
                    
                ext = os.path.splitext(doc.filename)[1].lower()
                if ext not in ['.pdf', '.docx', '.doc', '.txt', '.xml']:
                    logger.warning(f"Пропускаем неподдерживаемый файл: {doc.filename}")
                    continue
                
                filename = f"doc_{i}_{doc.filename}"
                path = os.path.join(tmpdir, filename)
                
                with open(path, "wb") as f:
                    content = await doc.read()
                    f.write(content)
                
                doc_paths.append(path)

            if not doc_paths:
                raise HTTPException(status_code=400, detail="Не найдено поддерживаемых документов")

            # Сохраняем смету
            smeta_ext = os.path.splitext(smeta.filename)[1].lower()
            if smeta_ext not in ['.xls', '.xlsx', '.xml', '.csv']:
                raise HTTPException(status_code=400, detail=f"Неподдерживаемый формат сметы: {smeta_ext}")
            
            smeta_filename = f"smeta_{smeta.filename}"
            smeta_path = os.path.join(tmpdir, smeta_filename)
            
            with open(smeta_path, "wb") as f:
                content = await smeta.read()
                f.write(content)

            logger.info(f"Запуск расширенного анализа: Claude={use_claude}, Mode={claude_mode}")
            
            # Выполняем анализ с пользовательскими настройками
            result = await analyze_concrete(
                doc_paths=doc_paths,
                smeta_path=smeta_path,
                use_claude=use_claude,
                claude_mode=claude_mode
            )
            
            logger.info(f"Анализ завершен: метод={result.get('analysis_method')}")
            return result

    except Exception as e:
        logger.error(f"Ошибка расширенного анализа: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@router.post("/concrete")
async def analyze_concrete_route(
    docs: List[UploadFile] = File(..., description="Project documentation files (PDF, DOCX, TXT)"),
    smeta: UploadFile = File(..., description="Budget/estimate file (XLS, XLSX, XML)")
):
    """
    Стандартный анализ бетонных конструкций (использует настройки по умолчанию)
    """
    if not docs:
        raise HTTPException(status_code=400, detail="Необходимо загрузить хотя бы один документ")
    
    if not smeta:
        raise HTTPException(status_code=400, detail="Необходимо загрузить файл сметы")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_paths = []

            # Сохраняем документы
            for i, doc in enumerate(docs):
                if not doc.filename:
                    continue
                    
                ext = os.path.splitext(doc.filename)[1].lower()
                if ext not in ['.pdf', '.docx', '.doc', '.txt', '.xml']:
                    logger.warning(f"Пропускаем неподдерживаемый файл: {doc.filename}")
                    continue
                
                filename = f"doc_{i}_{doc.filename}"
                path = os.path.join(tmpdir, filename)
                
                with open(path, "wb") as f:
                    content = await doc.read()
                    f.write(content)
                
                doc_paths.append(path)
                logger.info(f"Сохранен документ: {filename}")

            if not doc_paths:
                raise HTTPException(status_code=400, detail="Не найдено поддерживаемых документов")

            # Сохраняем смету
            smeta_ext = os.path.splitext(smeta.filename)[1].lower()
            if smeta_ext not in ['.xls', '.xlsx', '.xml', '.csv']:
                raise HTTPException(status_code=400, detail=f"Неподдерживаемый формат сметы: {smeta_ext}")
            
            smeta_filename = f"smeta_{smeta.filename}"
            smeta_path = os.path.join(tmpdir, smeta_filename)
            
            with open(smeta_path, "wb") as f:
                content = await smeta.read()
                f.write(content)
            
            logger.info(f"Сохранена смета: {smeta_filename}")

            # Выполняем гибридный анализ
            use_claude = os.getenv("USE_CLAUDE", "true").lower() == "true"
            claude_mode = os.getenv("CLAUDE_MODE", "enhancement")  # enhancement | primary | fallback
            
            logger.info(f"Запуск анализа: Claude={use_claude}, Mode={claude_mode}")
            
            result = await analyze_concrete(
                doc_paths=doc_paths,
                smeta_path=smeta_path,
                use_claude=use_claude,
                claude_mode=claude_mode
            )
            
            logger.info(f"Анализ завершен успешно. Найдено марок бетона: {len(result.get('concrete_summary', []))}")
            
            return result

    except Exception as e:
        logger.error(f"Ошибка анализа: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@router.post("/materials")
async def analyze_materials_route(
    docs: List[UploadFile] = File(..., description="Project documentation files")
):
    """
    Анализ строительных материалов (кроме бетона) из проектной документации
    """
    # TODO: Implement materials analysis
    return {"message": "Materials analysis not implemented yet"}

@router.get("/supported-formats")
async def get_supported_formats():
    """
    Получить список поддерживаемых форматов файлов
    """
    return {
        "documents": [".pdf", ".docx", ".doc", ".txt", ".xml"],
        "estimates": [".xls", ".xlsx", ".xml", ".csv"]
    }
