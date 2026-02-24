import json
import asyncio
import logging
from sqlalchemy.orm import Session
from database import SessionLocal, DATA_DIR
import models
from services import arxiv_service, openreview_service, pdf_service, gemini_service
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Concurrency limit
MAX_CONCURRENT_PAPERS = 3
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_PAPERS)

def log_error_to_chat(db: Session, paper: models.Paper, error_msg: str):
    """Helper to log error message to chat history so it's visible in UI."""
    try:
        msg = models.ChatMessage(
            paper_id=paper.id,
            role="assistant",
            content=f"**Error Processing Paper:** {error_msg}"
        )
        db.add(msg)
    except Exception as e:
        logger.error(f"Failed to log error to chat: {e}")

async def process_paper(paper_id: str):
    db: Session = SessionLocal()
    try:
        paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
        if not paper:
            return

        # Double check status
        if paper.status != "queued":
            return

        # Update status to processing
        paper.status = "processing"
        db.commit()
        
        logger.info(f"Processing paper: {paper.title} ({paper.id})")

        # 1. Search
        # Try Arxiv first
        search_result = await asyncio.get_event_loop().run_in_executor(executor, arxiv_service.search_arxiv, paper.title)
        
        if not search_result:
            # Try OpenReview
            search_result = await asyncio.get_event_loop().run_in_executor(executor, openreview_service.search_openreview, paper.title)
        
        if not search_result:
            paper.status = "failed"
            paper.failure_reason = "Paper not found in Arxiv or OpenReview (ICLR/NeurIPS/ICML 2023-2026)"
            log_error_to_chat(db, paper, paper.failure_reason)
            db.commit()
            return

        # Update metadata
        paper.source = search_result["source"]
        paper.source_url = search_result["source_url"]
        # paper.title = search_result["title"] # Update title to official one? Maybe optional.
        db.commit()

        # 2. Download PDF
        pdf_url = search_result["pdf_url"]
        if not pdf_url:
            paper.status = "failed"
            paper.failure_reason = "PDF URL not found"
            log_error_to_chat(db, paper, paper.failure_reason)
            db.commit()
            return
            
        # Define save path: data/pdfs/{task_id}/{paper_id}.pdf
        save_path = os.path.join(DATA_DIR, "pdfs", paper.task_id, f"{paper.id}.pdf")
        
        success = await asyncio.get_event_loop().run_in_executor(executor, pdf_service.download_pdf, pdf_url, save_path)
        
        if not success:
            paper.status = "failed"
            paper.failure_reason = "Failed to download PDF"
            log_error_to_chat(db, paper, paper.failure_reason)
            db.commit()
            return
            
        paper.pdf_path = save_path
        db.commit()

        # 3. Interpret with Gemini
        # Get template
        task = db.query(models.Task).filter(models.Task.id == paper.task_id).first()
        template = db.query(models.Template).filter(models.Template.id == task.template_id).first()
        
        if not template:
            paper.status = "failed"
            paper.failure_reason = "Template not found"
            log_error_to_chat(db, paper, paper.failure_reason)
            db.commit()
            return

        try:
            # Parse template content (JSON list of prompts)
            try:
                prompts = json.loads(template.content)
                if not isinstance(prompts, list):
                     prompts = [template.content]
            except json.JSONDecodeError:
                prompts = [template.content]

            # Pass task.model_name (which might be None, default handled in service)
            model_name = task.model_name if task.model_name else "gemini-3-flash-preview"
            
            interpretation_text, chat_history = await asyncio.get_event_loop().run_in_executor(
                executor, 
                gemini_service.interpret_paper, 
                save_path, 
                prompts,
                model_name
            )
            
            # Save interpretation
            interp = models.Interpretation(
                paper_id=paper.id,
                content=interpretation_text,
                template_used=template.content
            )
            db.add(interp)
            
            # Save Chat History (So it appears in the chat view)
            for turn in chat_history:
                # turn structure: {'user': {'role': 'user', 'parts': [{'text': '...'}]}, 'model': {'role': 'model', 'parts': [{'text': '...'}]}, 'meta': {...}}
                
                # 1. User Message
                user_text = turn['user']['parts'][0]['text']
                user_msg = models.ChatMessage(
                    paper_id=paper.id,
                    role='user',
                    content=user_text
                )
                db.add(user_msg)
                
                # 2. Assistant Message
                model_text = turn['model']['parts'][0]['text']
                meta = turn.get('meta', {})
                assistant_msg = models.ChatMessage(
                    paper_id=paper.id,
                    role='assistant',
                    content=model_text,
                    cost=meta.get('cost', 0.0),
                    time_cost=meta.get('time_cost', 0.0)
                )
                db.add(assistant_msg)
            
            paper.status = "done"
            db.commit()
            
        except Exception as e:
            logger.error(f"Error interpreting paper {paper.id}: {e}")
            paper.status = "failed"
            paper.failure_reason = str(e)
            log_error_to_chat(db, paper, paper.failure_reason)
            db.commit()
            
    except Exception as e:
        logger.error(f"Error processing paper {paper_id}: {e}")
        # Try to update status if possible
        try:
            paper.status = "failed"
            paper.failure_reason = f"System error: {str(e)}"
            log_error_to_chat(db, paper, paper.failure_reason)
            db.commit()
        except:
            pass
    finally:
        db.close()

async def processor_loop():
    logger.info("Starting background processor loop")
    while True:
        db: Session = SessionLocal()
        try:
            # Find papers that are queued and belong to tasks that are running
            papers = db.query(models.Paper).join(models.Task).filter(
                models.Paper.status == "queued",
                models.Task.status == "running"
            ).limit(MAX_CONCURRENT_PAPERS).all()
            
            if not papers:
                await asyncio.sleep(2)
                continue
                
            tasks = []
            for paper in papers:
                tasks.append(process_paper(paper.id))
            
            if tasks:
                await asyncio.gather(*tasks)
                
        except Exception as e:
            logger.error(f"Error in processor loop: {e}")
            await asyncio.sleep(5)
        finally:
            db.close()
