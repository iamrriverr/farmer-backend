# src/routes/chat.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.websockets import WebSocket, WebSocketDisconnect
from typing import Dict, Any
from psycopg2.extras import Json
import json

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from ..models import QueryRequest, QueryResponse, Source
from ..auth import get_current_user, verify_websocket_token, get_db
from ..database import PostgreSQLManager
from ..rag import RAGSystem, IntentClassifier
from ..config import Config

router = APIRouter(prefix="/chat", tags=["聊天"])


# ============================================================
# 輔助函數：獲取 LLM 實例
# ============================================================
def get_llm(streaming=False):
    """
    獲取 LLM 實例（根據配置選擇 GPT 或 Gemini）
    
    Args:
        streaming: 是否啟用串流模式
        
    Returns:
        LLM 實例
    """
    if Config.PRIMARY_LLM == "gpt":
        # 使用 OpenAI GPT
        return ChatOpenAI(
            model=Config.GPT_MODEL,
            openai_api_key=Config.OPENAI_API_KEY,
            temperature=Config.GPT_TEMPERATURE,
            max_tokens=Config.GPT_MAX_TOKENS,
            streaming=streaming
        )
    else:
        # 使用 Google Gemini（備用）
        return ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.7,
            streaming=streaming
        )


# ============================================================
# REST API 查詢（帶對話記憶 + 🔥混合搜尋）
# ============================================================
@router.post("/query", response_model=QueryResponse)
async def query_with_rag(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
    req: Request = None
):
    """
    RAG 查詢（支援對話記憶 + 🔥混合搜尋）
    
    - **question**: 問題
    - **k**: RAG 檢索數量（1-20）
    - **conversation_id**: 對話 ID（選填，提供則啟用記憶）
    """
    try:
        db = req.app.state.db
        vector_manager = req.app.state.vector_manager
        
        # 步驟 1: 意圖判斷
        intent_classifier = IntentClassifier()
        intent_result = intent_classifier.classify(request.question)
        
        # 步驟 2: 載入對話歷史（如果有 conversation_id）
        history_text = ""
        if request.conversation_id:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT role, content 
                        FROM chat_history 
                        WHERE conversation_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT 10
                        """,
                        (request.conversation_id,)
                    )
                    messages = cur.fetchall()
                    
                    if messages:
                        history_text = "\n【歷史對話】\n"
                        for role, content in reversed(messages):
                            if role == "user":
                                history_text += f"用戶: {content}\n"
                            else:
                                history_text += f"AI: {content}\n"
                        history_text += "\n"
        
        # 步驟 3: 🔥 RAG 檢索（使用混合搜尋）
        context_text = ""
        sources = []
        
        if intent_result["use_rag"]:
            try:
                # 🔥 優先使用混合搜尋
                if Config.ENABLE_HYBRID_SEARCH and vector_manager.hybrid_manager:
                    relevant_docs = vector_manager.hybrid_search(
                        query=request.question,
                        k=request.k
                    )
                    print(f"✅ 混合搜尋返回 {len(relevant_docs)} 個文件")
                else:
                    # 回退到純向量搜尋
                    relevant_docs = vector_manager.similarity_search(
                        query=request.question,
                        k=request.k
                    )
                    print(f"✅ 向量搜尋返回 {len(relevant_docs)} 個文件")
                
                if relevant_docs:
                    context_text = "\n【相關文件】\n"
                    for i, doc in enumerate(relevant_docs, 1):
                        context_text += f"{i}. {doc.page_content}\n\n"
                        sources.append(Source(
                            source=doc.metadata.get("filename", "未知"),
                            department=doc.metadata.get("department", ""),
                            content=doc.page_content[:200]
                        ))
            except Exception as e:
                print(f"❌ 檢索失敗: {e}")
        
        # 步驟 4: 構建 Prompt（包含歷史和上下文）
        if intent_result["use_rag"]:
            prompt = f"""
你是農會的 AI 助手。請根據歷史對話和相關文件回答問題。

{history_text}
{context_text}

【當前問題】
{request.question}

【回答要求】
1. 考慮歷史對話的上下文
2. 基於提供的文件內容回答
3. 如果用戶提到「它」「那個」等代詞，從歷史對話中理解指涉
4. 保持對話的連貫性
5. 使用友善、專業的語氣
"""
        else:
            prompt = f"""
你是農會的 AI 助手。請根據歷史對話回答問題。

{history_text}

【當前問題】
{request.question}

【回答要求】
1. 考慮歷史對話的上下文
2. 使用友善、專業的語氣
3. 如果不在服務範圍內，禮貌地說明
"""
        
        # 步驟 5: 生成回答（使用 GPT）
        llm = get_llm(streaming=False)
        answer = llm.invoke(prompt).content
        
        # 步驟 6: 儲存對話記錄（如果有 conversation_id）
        if request.conversation_id:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    # 儲存用戶訊息
                    cur.execute(
                        """
                        INSERT INTO chat_history 
                        (conversation_id, role, content, created_at)
                        VALUES (%s, %s, %s, NOW())
                        """,
                        (request.conversation_id, "user", request.question)
                    )
                    
                    # 儲存 AI 回應
                    cur.execute(
                        """
                        INSERT INTO chat_history 
                        (conversation_id, role, content, sources, intent, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            request.conversation_id,
                            "assistant",
                            answer,
                            Json([s.dict() for s in sources]),
                            Json(intent_result)
                        )
                    )
                    
                    # 更新對話資訊
                    cur.execute(
                        """
                        UPDATE conversations 
                        SET message_count = message_count + 2,
                            last_message_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (request.conversation_id,)
                    )
                    
                    conn.commit()
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            context_count=len(sources),
            conversation_id=request.conversation_id,
            intent=intent_result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢失敗: {str(e)}"
        )


# ============================================================
# WebSocket 即時聊天（帶對話記憶 + 🔥混合搜尋）
# ============================================================
@router.websocket("/ws/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(...)
):
    """
    WebSocket 即時聊天（支援對話記憶 + 🔥混合搜尋）
    
    連線 URL: ws://localhost:8000/chat/ws/{conversation_id}?token={jwt_token}
    """
    # 步驟 1: 驗證 Token
    user = verify_websocket_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # 步驟 2: 建立連線
    await websocket.accept()
    
    # 取得資料庫和向量管理器
    from main import app
    db = app.state.db
    vector_manager = app.state.vector_manager
    
    # 發送連線成功訊息
    await websocket.send_json({
        "type": "connected",
        "message": f"✅ WebSocket 已連線（使用 {Config.get_model_name()}）",
        "conversation_id": conversation_id,
        "user_id": user["id"],
        "ai_model": Config.get_model_name(),
        "hybrid_search": "enabled" if Config.ENABLE_HYBRID_SEARCH else "disabled"
    })
    
    # 輔助函數：取得對話歷史
    def get_conversation_history(limit=10):
        """取得最近的對話歷史"""
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT role, content 
                    FROM chat_history 
                    WHERE conversation_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                    """,
                    (conversation_id, limit)
                )
                messages = cur.fetchall()
                return [(msg[0], msg[1]) for msg in reversed(messages)]
    
    # 步驟 3: 持續監聽訊息
    try:
        while True:
            data = await websocket.receive_json()
            question = data.get("content")
            k = data.get("k", 5)
            
            if not question:
                continue
            
            # 步驟 4: 意圖判斷
            intent_classifier = IntentClassifier()
            intent_result = intent_classifier.classify(question)
            
            await websocket.send_json({
                "type": "intent",
                "intent": intent_result["type"],
                "use_rag": intent_result["use_rag"],
                "confidence": intent_result.get("confidence", 0.0)
            })
            
            # 步驟 5: 載入對話歷史（對話記憶）
            history = get_conversation_history(limit=10)
            
            history_text = ""
            if history:
                history_text = "\n【歷史對話】\n"
                for role, content in history:
                    if role == "user":
                        history_text += f"用戶: {content}\n"
                    else:
                        history_text += f"AI: {content}\n"
                history_text += "\n"
            
            # 步驟 6: 🔥 RAG 檢索（使用混合搜尋）
            context_text = ""
            sources = []
            
            if intent_result["use_rag"]:
                try:
                    # 🔥 優先使用混合搜尋
                    if Config.ENABLE_HYBRID_SEARCH and vector_manager.hybrid_manager:
                        relevant_docs = vector_manager.hybrid_search(
                            query=question,
                            k=k
                        )
                        print(f"✅ 混合搜尋返回 {len(relevant_docs)} 個文件")
                    else:
                        # 回退到純向量搜尋
                        relevant_docs = vector_manager.similarity_search(
                            query=question,
                            k=k
                        )
                        print(f"✅ 向量搜尋返回 {len(relevant_docs)} 個文件")
                    
                    if relevant_docs:
                        context_text = "\n【相關文件】\n"
                        for i, doc in enumerate(relevant_docs, 1):
                            context_text += f"{i}. {doc.page_content}\n\n"
                            sources.append({
                                "source": doc.metadata.get("filename", "未知"),
                                "department": doc.metadata.get("department", ""),
                                "content": doc.page_content[:200]
                            })
                except Exception as e:
                    print(f"❌ RAG 檢索失敗: {e}")
            
            # 步驟 7: 構建 Prompt（包含歷史和上下文）
            if intent_result["use_rag"]:
                prompt = f"""
你是農會的 AI 助手。請根據歷史對話和相關文件回答問題。

{history_text}
{context_text}

【當前問題】
{question}

【回答要求】
1. **重要**：仔細閱讀歷史對話，理解上下文和指涉關係
2. 如果用戶提到「它」「那個」「第一個」「剛才說的」等代詞或指涉詞，從歷史對話中找到具體所指
3. 基於提供的文件內容回答
4. 保持對話的連貫性和一致性
5. 使用友善、專業的語氣
"""
            else:
                prompt = f"""
你是農會的 AI 助手。請根據歷史對話回答問題。

{history_text}

【當前問題】
{question}

【回答要求】
1. **重要**：仔細閱讀歷史對話，理解上下文
2. 如果用戶提到「它」「那個」等代詞，從歷史對話中理解指涉
3. 保持對話的連貫性
4. 使用友善、專業的語氣
5. 如果不在服務範圍內，禮貌地說明
"""
            
            # 步驟 8: 使用 LLM 生成回答（串流）
            llm = get_llm(streaming=True)
            
            full_response = ""
            chunk_index = 0
            
            try:
                async for chunk in llm.astream(prompt):
                    content = chunk.content
                    full_response += content
                    
                    await websocket.send_json({
                        "type": "chunk",
                        "content": content,
                        "chunk_index": chunk_index
                    })
                    chunk_index += 1
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"生成回答時發生錯誤: {str(e)}"
                })
                continue
            
            # 步驟 9: 發送完成訊息
            await websocket.send_json({
                "type": "done",
                "total_chunks": chunk_index,
                "sources": sources,
                "full_response": full_response
            })
            
            # 步驟 10: 儲存對話記錄到資料庫（保存記憶）
            try:
                with db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO chat_history 
                            (conversation_id, role, content, created_at)
                            VALUES (%s, %s, %s, NOW())
                            """,
                            (conversation_id, "user", question)
                        )
                        
                        cur.execute(
                            """
                            INSERT INTO chat_history 
                            (conversation_id, role, content, sources, intent, created_at)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                            """,
                            (
                                conversation_id,
                                "assistant",
                                full_response,
                                Json(sources),
                                Json(intent_result)
                            )
                        )
                        
                        cur.execute(
                            """
                            UPDATE conversations 
                            SET message_count = message_count + 2,
                                last_message_at = NOW(),
                                updated_at = NOW()
                            WHERE id = %s AND user_id = %s
                            """,
                            (conversation_id, user["id"])
                        )
                        
                        conn.commit()
                        
            except Exception as e:
                print(f"儲存對話記錄失敗: {e}")
                await websocket.send_json({
                    "type": "warning",
                    "message": "對話記錄儲存失敗，但不影響使用"
                })
    
    except WebSocketDisconnect:
        print(f"✅ WebSocket 正常斷線: conversation_id={conversation_id}, user_id={user['id']}")
    
    except Exception as e:
        print(f"❌ WebSocket 異常: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"連線發生錯誤: {str(e)}"
            })
        except:
            pass


# ============================================================
# 🔥 測試端點：對比三種搜尋方式
# ============================================================
@router.post("/test-search-comparison", tags=["測試"])
async def test_search_comparison(
    query: str = Query(..., description="測試查詢"),
    k: int = Query(5, description="返回數量", ge=1, le=20),
    current_user: dict = Depends(get_current_user),
    req: Request = None
):
    """
    對比三種搜尋方式的結果
    
    - **純向量搜尋** (Vector Search)
    - **純 BM25 搜尋** (Keyword Search)
    - **混合搜尋** (Hybrid Search = BM25 + Vector)
    
    用於測試和比較不同搜尋策略的效果
    """
    vector_manager = req.app.state.vector_manager
    
    if not vector_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="向量資料庫未初始化"
        )
    
    results = {
        "query": query,
        "k": k,
        "comparison": {}
    }
    
    # 1. 純向量搜尋
    try:
        vector_docs = vector_manager.similarity_search(query, k=k)
        results["comparison"]["vector_only"] = {
            "method": "向量相似度搜尋 (Semantic Search)",
            "count": len(vector_docs),
            "results": [
                {
                    "rank": idx + 1,
                    "source": d.metadata.get("filename", "未知"),
                    "content": d.page_content[:150] + "...",
                    "department": d.metadata.get("department", "")
                }
                for idx, d in enumerate(vector_docs)
            ]
        }
    except Exception as e:
        results["comparison"]["vector_only"] = {"error": str(e)}
    
    # 2. 純 BM25 搜尋
    if vector_manager.hybrid_manager:
        try:
            bm25_docs = vector_manager.hybrid_manager.get_bm25_only(query, k=k)
            results["comparison"]["bm25_only"] = {
                "method": "BM25 關鍵字搜尋 (Keyword Search)",
                "count": len(bm25_docs),
                "results": [
                    {
                        "rank": idx + 1,
                        "source": d.metadata.get("filename", "未知"),
                        "content": d.page_content[:150] + "...",
                        "department": d.metadata.get("department", "")
                    }
                    for idx, d in enumerate(bm25_docs)
                ]
            }
        except Exception as e:
            results["comparison"]["bm25_only"] = {"error": str(e)}
    else:
        results["comparison"]["bm25_only"] = {
            "error": "BM25 未啟用",
            "reason": "請設定 ENABLE_HYBRID_SEARCH=true"
        }
    
    # 3. 混合搜尋
    if vector_manager.hybrid_manager:
        try:
            hybrid_docs = vector_manager.hybrid_search(query, k=k)
            results["comparison"]["hybrid"] = {
                "method": "混合搜尋 (Hybrid = BM25 + Vector)",
                "count": len(hybrid_docs),
                "weights": {
                    "bm25": Config.BM25_WEIGHT,
                    "vector": Config.VECTOR_WEIGHT
                },
                "results": [
                    {
                        "rank": idx + 1,
                        "source": d.metadata.get("filename", "未知"),
                        "content": d.page_content[:150] + "...",
                        "department": d.metadata.get("department", "")
                    }
                    for idx, d in enumerate(hybrid_docs)
                ]
            }
        except Exception as e:
            results["comparison"]["hybrid"] = {"error": str(e)}
    else:
        results["comparison"]["hybrid"] = {
            "error": "混合搜尋未啟用",
            "reason": "請設定 ENABLE_HYBRID_SEARCH=true"
        }
    
    return results


# ============================================================
# 意圖分類測試端點
# ============================================================
@router.post("/classify-intent", tags=["測試"])
async def classify_intent(
    question: str = Query(..., description="問題內容"),
    current_user: dict = Depends(get_current_user)
):
    """
    測試意圖分類
    
    判斷問題是否需要 RAG 檢索
    """
    try:
        intent_classifier = IntentClassifier()
        result = intent_classifier.classify(question)
        
        return {
            "question": question,
            "intent": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"意圖分類失敗: {str(e)}"
        )
