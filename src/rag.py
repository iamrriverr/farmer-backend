# src/rag.py
from typing import Dict, Optional, List, AsyncGenerator
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain.schema import Document
import json
import re
import asyncio

from .config import Config
from .database import PostgreSQLManager
from .loader import DocumentLoader
from .vector import VectorStoreManager


class IntentClassifier:
    """
    使用 LLM 進行意圖分類
    判斷是否需要 RAG、閒聊或超出範圍
    """
    
    def __init__(self):
        # 使用配置中的主要 LLM
        if Config.PRIMARY_LLM == "gpt":
            self.classifier_llm = ChatOpenAI(
                model=Config.GPT_MODEL,
                openai_api_key=Config.OPENAI_API_KEY,
                temperature=0.3,  # 低溫度確保穩定判斷
                max_tokens=100
            )
            print("✅ 意圖分類器：使用 GPT")
        else:
            self.classifier_llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash-8b",
                google_api_key=Config.GOOGLE_API_KEY,
                temperature=0.3
            )
            print("✅ 意圖分類器：使用 Gemini Flash")
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是意圖分類助手。請判斷問題類型並以 JSON 回應。

分類標準：
1. RAG - 需要查詢文件的業務問題
   - 農業技術（種植、病蟲害、施肥等）
   - 政策補助（申請、資格、流程等）
   - 具體操作方法
   - 文件資料查詢
   
2. CHITCHAT - 一般對話
   - 問候語
   - 關於助手的問題
   - 閒聊
   
3. OUT_OF_SCOPE - 超出範圍
   - 與農業無關的問題
   - 金融投資、娛樂八卦、政治等

回應格式（僅 JSON）：
{{"intent": "RAG|CHITCHAT|OUT_OF_SCOPE", "confidence": 0.0-1.0, "reason": "簡短原因"}}"""),
            ("human", "問題：{question}")
        ])
    
    def classify(self, question: str) -> Dict:
        """同步分類"""
        try:
            chain = self.prompt | self.classifier_llm
            response = chain.invoke({"question": question})
            content = response.content.strip()
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Fallback
                content_upper = content.upper()
                if "RAG" in content_upper:
                    result = {"intent": "RAG", "confidence": 0.8, "reason": "LLM 判斷"}
                elif "CHITCHAT" in content_upper:
                    result = {"intent": "CHITCHAT", "confidence": 0.8, "reason": "LLM 判斷"}
                else:
                    result = {"intent": "OUT_OF_SCOPE", "confidence": 0.8, "reason": "LLM 判斷"}
            
            intent = result.get("intent", "CHITCHAT").upper()
            
            return {
                "use_rag": intent == "RAG",
                "type": intent.lower(),  # 改為 type 以符合其他地方的使用
                "confidence": float(result.get("confidence", 0.8)),
                "reason": result.get("reason", "LLM 判斷")
            }
        except Exception as e:
            print(f"⚠️ 意圖分類失敗: {e}，預設使用 RAG")
            return {
                "use_rag": True,
                "type": "rag",
                "confidence": 0.6,
                "reason": "分類失敗，預設策略"
            }
    
    async def classify_async(self, question: str) -> Dict:
        """非同步分類"""
        try:
            chain = self.prompt | self.classifier_llm
            response = await chain.ainvoke({"question": question})
            content = response.content.strip()
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                content_upper = content.upper()
                if "RAG" in content_upper:
                    result = {"intent": "RAG", "confidence": 0.8, "reason": "LLM 判斷"}
                elif "CHITCHAT" in content_upper:
                    result = {"intent": "CHITCHAT", "confidence": 0.8, "reason": "LLM 判斷"}
                else:
                    result = {"intent": "OUT_OF_SCOPE", "confidence": 0.8, "reason": "LLM 判斷"}
            
            intent = result.get("intent", "CHITCHAT").upper()
            
            return {
                "use_rag": intent == "RAG",
                "type": intent.lower(),
                "confidence": float(result.get("confidence", 0.8)),
                "reason": result.get("reason", "LLM 判斷")
            }
        except Exception as e:
            print(f"⚠️ 非同步意圖分類失敗: {e}")
            return self.classify(question)


class RAGSystem:
    """PostgreSQL + Chroma RAG 系統（智能意圖識別 + 動態處理）"""

    def __init__(self):
        self.db_manager = PostgreSQLManager()
        self.vector_manager = VectorStoreManager(
            persist_directory=Config.CHROMA_PERSIST_DIR,
            collection_name=Config.CHROMA_COLLECTION
        )
        self.rag_chain = None
        
        # 初始化意圖分類器
        self.intent_classifier = IntentClassifier()
        
        # 主要 LLM（用於 RAG 和對話）
        if Config.PRIMARY_LLM == "gpt":
            self.chat_llm = ChatOpenAI(
                model=Config.GPT_MODEL,
                openai_api_key=Config.OPENAI_API_KEY,
                temperature=Config.GPT_TEMPERATURE,
                max_tokens=Config.GPT_MAX_TOKENS,
                streaming=True
            )
            
            # 用於意圖提取的 LLM（使用更便宜的模型）
            self.intent_llm = ChatOpenAI(
                model="gpt-4o-mini",  # 使用 mini 版本節省成本
                openai_api_key=Config.OPENAI_API_KEY,
                temperature=0
            )
            print(f"✅ 對話 LLM：使用 {Config.GPT_MODEL}")
        else:
            self.chat_llm = ChatGoogleGenerativeAI(
                model=Config.GEMINI_MODEL,
                google_api_key=Config.GOOGLE_API_KEY,
                temperature=0.7,
                streaming=True
            )
            self.intent_llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0
            )
            print("✅ 對話 LLM：使用 Gemini")
        
        print("✅ RAG 系統已初始化（智能意圖識別 + 動態處理）")

    def init_database(self):
        """初始化資料庫"""
        self.db_manager.init_database()

    def _extract_intent(self, question: str) -> Dict[str, any]:
        """
        使用 LLM 從問題中提取意圖和過濾條件
        """
        intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一個專業的意圖識別模型。請根據用戶的問題,提取部門、業務類別、年份、文件類型和純粹的問題,並以 JSON 格式返回。

JSON 格式範例:
{{
  "department": "業務",
  "job_type": "繼承業務",
  "year": 2024,
  "document_type": "作業指南",
  "pure_question": "繼承存款申請需要哪些文件?"
}}

重要規則:
1. 如果沒有提到,對應欄位設為 null
2. pure_question 應該是完整的疑問句,但不包含過濾條件
3. job_type 是部門內的細分業務類別
4. 部門對應規則:
   - "財務"、"財務部"、"會計" → "財務"
   - "研發"、"R&D"、"技術部" → "研發"
   - "人資"、"HR"、"人力資源" → "人資"
   - "業務"、"業務部"、"銷售" → "業務"
5. 業務類別識別範例:
   - "繼承業務"、"遺產繼承"、"繼承存款" → "繼承業務"
   - "保險業務"、"保單"、"理賠" → "保險業務"
6. 如果只提到業務類別沒有提到部門,可以推斷為「業務」部門
"""),
            ("human", "{question}")
        ])

        chain = intent_prompt | self.intent_llm

        try:
            response = chain.invoke({"question": question})
            content = response.content
            json_match = re.search(r'\{[^\}]+\}', content, re.DOTALL)
            if json_match:
                try:
                    intent_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    cleaned_content = json_match.group().replace('\n', '').replace('\r', '')
                    intent_data = json.loads(cleaned_content)

                return {
                    "department": intent_data.get("department"),
                    "job_type": intent_data.get("job_type"),
                    "year": int(intent_data.get("year")) if intent_data.get("year") else None,
                    "document_type": intent_data.get("document_type"),
                    "pure_question": intent_data.get("pure_question", question)
                }
            else:
                print("⚠️ 意圖識別失敗,使用原始問題")
                return {
                    "department": None,
                    "job_type": None,
                    "year": None,
                    "document_type": None,
                    "pure_question": question
                }
        except Exception as e:
            print(f"❌ 意圖提取失敗: {e}")
            return {
                "department": None,
                "job_type": None,
                "year": None,
                "document_type": None,
                "pure_question": question
            }

    def _is_document_vectorized(self, document_id: str) -> bool:
        """檢查文件是否已向量化（快取機制）"""
        try:
            results = self.vector_manager.vectorstore._collection.get(
                where={"document_id": document_id},
                limit=1
            )
            return len(results['ids']) > 0
        except:
            return False
    
    def _process_documents_to_vectors(self, doc_infos: List[Dict]) -> int:
        """處理文件並轉換為向量"""
        all_chunks = []
        processed_count = 0
        
        for doc_info in doc_infos:
            document_id = doc_info['document_id']
            
            if self._is_document_vectorized(document_id):
                print(f"⏭️  跳過已處理: {doc_info['filename']}")
                continue
            
            print(f"📄 處理: {doc_info['filename']}")
            
            try:
                documents = DocumentLoader.load_document(doc_info['source_url'])
                if not documents:
                    print(f"  ✗ 載入失敗")
                    self.db_manager.update_document_status(document_id, 'failed', '文件載入失敗')
                    continue
                
                chunks = DocumentLoader.split_into_chunks(
                    documents,
                    chunk_size=Config.CHUNK_SIZE,
                    chunk_overlap=Config.CHUNK_OVERLAP
                )
                
                for chunk in chunks:
                    chunk.metadata.update({
                        'document_id': document_id,
                        'department': doc_info.get('department', ''),
                        'job_type': doc_info.get('job_type'),
                        'year': doc_info.get('year'),
                        'document_type': doc_info.get('document_type', 'general'),
                        'filename': doc_info['filename']
                    })
                
                all_chunks.extend(chunks)
                processed_count += 1
                print(f"  ✓ 生成 {len(chunks)} 個切片")
                
                self.db_manager.update_document_status(document_id, 'processing')
                
            except Exception as e:
                print(f"  ✗ 處理失敗: {e}")
                self.db_manager.update_document_status(document_id, 'failed', str(e))
                continue
        
        if all_chunks:
            print(f"🔄 向量化 {len(all_chunks)} 個新切片...")
            self.vector_manager.add_documents(all_chunks)
            
            for doc_info in doc_infos:
                if self._is_document_vectorized(doc_info['document_id']):
                    self.db_manager.update_document_status(doc_info['document_id'], 'completed')
        
        return processed_count

    async def chat_stream(
        self,
        question: str,
        conversation_id: str = None,
        user_id: int = None,
        k: int = 5
    ) -> AsyncGenerator[Dict, None]:
        """
        智能聊天串流（自動判斷是否使用 RAG）
        
        新增功能：先判斷意圖，再決定處理方式
        """
        print(f"\n{'='*60}")
        print(f"🤔 分析問題: {question}")
        print(f"🤖 使用模型: {Config.get_model_name()}")
        print(f"{'='*60}")
        
        # 階段 0: 意圖分類
        print("🔍 [階段 0] 意圖分類中...")
        try:
            intent_result = await self.intent_classifier.classify_async(question)
        except:
            intent_result = self.intent_classifier.classify(question)
        
        # 發送意圖分析結果
        yield {
            "type": "intent",
            "use_rag": intent_result["use_rag"],
            "intent": intent_result["type"],
            "confidence": intent_result["confidence"],
            "reason": intent_result["reason"]
        }
        
        print(f"📊 意圖分析結果:")
        print(f"   類型: {intent_result['type']}")
        print(f"   置信度: {intent_result['confidence']:.2f}")
        print(f"   原因: {intent_result['reason']}")
        print(f"   使用 RAG: {'是' if intent_result['use_rag'] else '否'}")
        print(f"{'='*60}\n")
        
        # 根據意圖選擇處理方式
        if intent_result["type"] == "out_of_scope":
            # 超出範圍
            out_of_scope_message = """抱歉，這個問題超出了我的服務範圍。😊

我主要協助以下領域的問題：
• 🌾 農業技術諮詢（種植、病蟲害、施肥等）
• 💰 農業政策與補助申請
• 📋 農會相關業務查詢
• 🔍 農業文件資料查詢

您可以換個與農業相關的問題試試看！"""
            
            for line in out_of_scope_message.split('\n'):
                yield {
                    "type": "content",
                    "content": line + "\n"
                }
                await asyncio.sleep(0.03)
            
            yield {"type": "sources", "sources": []}
            return
        
        elif intent_result["use_rag"]:
            # 使用 RAG 流程
            print("🔍 啟用 RAG 檢索模式\n")
            
            filters_intent = self._extract_intent(question)
            
            filters = {}
            if filters_intent['department']:
                filters['department'] = filters_intent['department']
            if filters_intent['job_type']:
                filters['job_type'] = filters_intent['job_type']
            if filters_intent['year']:
                filters['year'] = filters_intent['year']
            if filters_intent['document_type']:
                filters['document_type'] = filters_intent['document_type']
            
            print(f"📋 過濾條件: {filters if filters else '無'}")
            
            valid_docs = self.db_manager.filter_documents(filters)
            print(f"📂 符合條件的文件: {len(valid_docs)} 個")
            
            if not valid_docs:
                no_doc_message = "根據您的條件，沒有找到相關文件。請嘗試調整問題或聯繫管理員上傳相關資料。"
                yield {"type": "content", "content": no_doc_message}
                yield {"type": "sources", "sources": []}
                return
            
            self._process_documents_to_vectors(valid_docs)
            
            valid_doc_ids = [doc['document_id'] for doc in valid_docs]
            chroma_filter = {"document_id": {"$in": valid_doc_ids}}
            
            retrieved_docs = self.vector_manager.similarity_search(
                query=filters_intent['pure_question'],
                k=k,
                filter=chroma_filter
            )
            
            if not retrieved_docs:
                yield {"type": "content", "content": "沒有找到相關文件內容。"}
                yield {"type": "sources", "sources": []}
                return
            
            context = "\n\n".join([doc.page_content for doc in retrieved_docs])
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""你是專業的農業助手。請根據以下文件內容回答問題。

規則：
1. 只使用提供的文件內容
2. 找不到答案時明確說明
3. 回答簡潔準確
4. 使用繁體中文

文件內容：
{context}"""),
                ("human", "{input}")
            ])
            
            chain = prompt | self.chat_llm
            
            async for chunk in chain.astream({"input": filters_intent['pure_question']}):
                if hasattr(chunk, 'content') and chunk.content:
                    yield {"type": "content", "content": chunk.content}
            
            sources = [
                {
                    "source": doc.metadata.get("filename", "未知"),
                    "department": doc.metadata.get("department", ""),
                    "content": doc.page_content[:200] + "..."
                }
                for doc in retrieved_docs
            ]
            
            yield {"type": "sources", "sources": sources}
        
        else:
            # 閒聊模式（直接 LLM）
            print("💬 啟用一般對話模式\n")
            
            context_messages = []
            if conversation_id:
                try:
                    with self.db_manager.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """SELECT message FROM chat_history
                                   WHERE session_id = %s
                                   ORDER BY created_at DESC LIMIT 6""",
                                (conversation_id,)
                            )
                            results = cur.fetchall()
                            
                            for row in reversed(results):
                                msg = row[0]
                                role = "user" if msg.get("type") == "human" else "assistant"
                                context_messages.append(f"{role}: {msg.get('content', '')}")
                except:
                    pass
            
            context_text = "\n".join(context_messages[-4:]) if context_messages else ""
            
            system_prompt = f"""你是農會的智能助手「小農助手」。

個性：友善、專業、有耐心
能力：農業技術諮詢、政策查詢

原則：
1. 問候或閒聊時簡短友善回應
2. 問到身份時簡單介紹自己
3. 具體問題時提醒可以詢問詳細內容
4. 使用繁體中文

{f"對話記錄：{context_text}" if context_text else ""}"""

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}")
            ])
            
            chain = prompt | self.chat_llm
            
            async for chunk in chain.astream({"input": question}):
                if hasattr(chunk, 'content') and chunk.content:
                    yield {"type": "content", "content": chunk.content}
            
            yield {"type": "sources", "sources": []}

    def smart_query(self, question: str, k: int = 5) -> Dict:
        """智能查詢（保持原有接口，內部使用意圖判斷）"""
        print(f"\n=== 開始智能查詢 (使用 {Config.get_model_name()}) ===")
        print(f"原始問題: {question}")
        
        intent_check = self.intent_classifier.classify(question)
        
        if not intent_check["use_rag"]:
            return {
                "answer": "此問題不適合使用文件查詢，建議改為一般對話模式。",
                "context": [],
                "intent": intent_check
            }
        
        intent = self._extract_intent(question)
        
        filters = {}
        if intent['department']:
            filters['department'] = intent['department']
        if intent['job_type']:
            filters['job_type'] = intent['job_type']
        if intent['year']:
            filters['year'] = intent['year']
        if intent['document_type']:
            filters['document_type'] = intent['document_type']
        
        valid_docs = self.db_manager.filter_documents(filters)
        
        if not valid_docs:
            return {
                "answer": "沒有找到符合條件的文件。",
                "context": [],
                "intent": intent
            }
        
        self._process_documents_to_vectors(valid_docs)
        
        valid_doc_ids = [doc['document_id'] for doc in valid_docs]
        chroma_filter = {"document_id": {"$in": valid_doc_ids}}
        retriever = self.vector_manager.get_retriever(k=k, filter=chroma_filter)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是專業的文件問答助手。請根據提供的文件內容回答問題。

重要規則:
1. 只使用提供的文件內容來回答
2. 找不到答案時明確說明
3. 回答要精確、簡潔
4. 使用繁體中文

文件內容:
{context}"""),
            ("human", "{input}")
        ])
        
        # 使用配置中的 LLM
        if Config.PRIMARY_LLM == "gpt":
            llm = ChatOpenAI(
                model=Config.GPT_MODEL,
                openai_api_key=Config.OPENAI_API_KEY,
                temperature=0
            )
        else:
            llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        result = rag_chain.invoke({"input": intent['pure_question']})
        result['intent'] = intent
        result['filters_applied'] = filters
        result['intent_classification'] = intent_check
        
        return result

    def query(
        self, 
        question: str, 
        department: Optional[str] = None,
        year: Optional[int] = None,
        document_type: Optional[str] = None,
        k: int = 5
    ) -> Dict:
        """傳統查詢（手動指定過濾條件）"""
        filters = {}
        if department:
            filters['department'] = department
        if year:
            filters['year'] = year
        if document_type:
            filters['document_type'] = document_type
        
        valid_docs = self.db_manager.filter_documents(filters)
        
        if not valid_docs:
            return {
                "answer": "根據指定的過濾條件,沒有找到符合的文件。",
                "context": []
            }
        
        self._process_documents_to_vectors(valid_docs)
        
        valid_doc_ids = [doc['document_id'] for doc in valid_docs]
        chroma_filter = {"document_id": {"$in": valid_doc_ids}}
        retriever = self.vector_manager.get_retriever(k=k, filter=chroma_filter)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是專業的文件問答助手。請根據提供的文件內容回答問題。

重要規則:
1. 只使用提供的文件內容來回答
2. 找不到答案時明確說明
3. 使用繁體中文

文件內容:
{context}"""),
            ("human", "{input}")
        ])
        
        if Config.PRIMARY_LLM == "gpt":
            llm = ChatOpenAI(
                model=Config.GPT_MODEL,
                openai_api_key=Config.OPENAI_API_KEY,
                temperature=0
            )
        else:
            llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        result = rag_chain.invoke({"input": question})
        
        return result

    def close(self):
        """關閉連接"""
        self.db_manager.close()


# 便捷函數
def get_llm(streaming=False):
    """
    獲取 LLM 實例（根據配置選擇 GPT 或 Gemini）
    
    Args:
        streaming: 是否啟用串流模式
        
    Returns:
        LLM 實例
    """
    if Config.PRIMARY_LLM == "gpt":
        return ChatOpenAI(
            model=Config.GPT_MODEL,
            openai_api_key=Config.OPENAI_API_KEY,
            temperature=Config.GPT_TEMPERATURE,
            max_tokens=Config.GPT_MAX_TOKENS,
            streaming=streaming
        )
    else:
        return ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.7,
            streaming=streaming
        )
