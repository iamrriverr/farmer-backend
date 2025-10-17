# src/vector.py
from typing import List, Dict, Optional
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document
from langchain_community.vectorstores.utils import filter_complex_metadata
from .config import Config

class VectorStoreManager:
    """
    Chroma 向量資料庫管理器
    支援 OpenAI 和 Google Gemini Embeddings
    🔥 支援混合搜尋（BM25 + 向量搜尋）
    """
    
    def __init__(
        self,
        persist_directory: str = None,
        collection_name: str = None,
        use_gemini: bool = False
    ):
        """
        初始化向量資料庫管理器
        
        Args:
            persist_directory: 持久化目錄路徑
            collection_name: Collection 名稱
            use_gemini: 是否使用 Gemini Embeddings（預設使用 OpenAI）
        """
        self.persist_directory = persist_directory or Config.CHROMA_PERSIST_DIR
        self.collection_name = collection_name or Config.CHROMA_COLLECTION
        
        # 初始化 Embeddings
        if use_gemini:
            try:
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model=Config.EMBEDDING_MODEL,
                    google_api_key=Config.GOOGLE_API_KEY
                )
                print("✅ 使用 Google Gemini Embeddings")
            except Exception as e:
                print(f"⚠️ Gemini Embeddings 初始化失敗: {e}，切換到 OpenAI")
                self.embeddings = OpenAIEmbeddings(model=Config.EMBEDDING_MODEL)
                print("✅ 使用 OpenAI Embeddings")
        else:
            self.embeddings = OpenAIEmbeddings(model=Config.EMBEDDING_MODEL)
            print("✅ 使用 OpenAI Embeddings")
        
        self.vectorstore = None
        self.hybrid_manager = None  # 🔥 混合搜尋管理器（延遲初始化）
        self.init_vectorstore()
    
    def init_vectorstore(self):
        """初始化向量資料庫"""
        try:
            self.vectorstore = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            print(f"✅ Chroma 向量資料庫已初始化 (Collection: {self.collection_name})")
        except Exception as e:
            print(f"❌ Chroma 初始化失敗: {e}")
            raise
    
    def init_hybrid_search(self, documents: List[Document] = None):
        """
        🔥 初始化混合搜尋（BM25 + 向量搜尋）
        
        Args:
            documents: 文件列表（用於建立 BM25 索引）
        """
        try:
            from .hybrid_search import HybridSearchManager
            
            # 取得向量檢索器
            retriever = self.get_retriever(k=10)
            
            # 建立混合搜尋管理器
            self.hybrid_manager = HybridSearchManager(
                vector_retriever=retriever,
                documents=documents
            )
            print(f"✅ 混合搜尋已啟用（BM25 + 向量搜尋），文件數：{len(documents) if documents else 0}）")
        except Exception as e:
            print(f"⚠️ 混合搜尋初始化失敗: {e}")
            self.hybrid_manager = None
    
    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        bm25_weight: float = None,
        vector_weight: float = None,
        filter: Optional[Dict] = None
    ) -> List[Document]:
        """
        🔥 執行混合搜尋（BM25 + 向量搜尋）
        
        Args:
            query: 搜尋查詢
            k: 返回文件數量
            bm25_weight: BM25 權重（預設使用 Config）
            vector_weight: 向量權重（預設使用 Config）
            filter: Metadata 過濾條件
            
        Returns:
            合併後的文件列表
        """
        if not self.hybrid_manager:
            print("⚠️ 混合搜尋未啟用，回退到純向量搜尋")
            return self.similarity_search(query, k=k, filter=filter)
        
        # 使用配置的權重
        bm25_w = bm25_weight if bm25_weight is not None else Config.BM25_WEIGHT
        vector_w = vector_weight if vector_weight is not None else Config.VECTOR_WEIGHT
        
        return self.hybrid_manager.hybrid_search(
            query=query,
            k=k,
            bm25_weight=bm25_w,
            vector_weight=vector_w,
            filter=filter
        )
    
    def clean_metadata(self, documents: List[Document]) -> List[Document]:
        """清理 metadata，確保符合 Chroma 要求"""
        cleaned_docs = []
        for doc in documents:
            cleaned_metadata = {}
            for key, value in doc.metadata.items():
                if isinstance(value, list):
                    cleaned_metadata[key] = ", ".join(str(v) for v in value) if value else ""
                elif isinstance(value, dict):
                    import json
                    cleaned_metadata[key] = json.dumps(value, ensure_ascii=False)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    cleaned_metadata[key] = value
                else:
                    cleaned_metadata[key] = str(value)
            
            cleaned_doc = Document(
                page_content=doc.page_content,
                metadata=cleaned_metadata
            )
            cleaned_docs.append(cleaned_doc)
        
        return cleaned_docs
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文件到向量資料庫"""
        try:
            cleaned_docs = self.clean_metadata(documents)
            cleaned_docs = filter_complex_metadata(cleaned_docs)
            ids = self.vectorstore.add_documents(cleaned_docs)
            print(f"✅ 已添加 {len(ids)} 個文件到向量資料庫")
            self.vectorstore.persist()
            
            # 🔥 同步更新 BM25 索引
            if self.hybrid_manager:
                self.hybrid_manager.add_documents(cleaned_docs)
                print(f"✅ BM25 索引已更新")
            
            return ids
        except Exception as e:
            print(f"❌ 添加文件失敗: {e}")
            raise
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Document]:
        """相似度搜尋（純向量搜尋）"""
        try:
            if filter:
                results = self.vectorstore.similarity_search(query=query, k=k, filter=filter)
            else:
                results = self.vectorstore.similarity_search(query=query, k=k)
            return results
        except Exception as e:
            print(f"❌ 相似度搜尋失敗: {e}")
            return []
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[tuple]:
        """相似度搜尋（帶分數）"""
        try:
            if filter:
                results = self.vectorstore.similarity_search_with_score(query=query, k=k, filter=filter)
            else:
                results = self.vectorstore.similarity_search_with_score(query=query, k=k)
            return results
        except Exception as e:
            print(f"❌ 相似度搜尋失敗: {e}")
            return []
    
    def get_retriever(self, k: int = 5, filter: Optional[Dict] = None, search_type: str = "similarity"):
        """取得檢索器（用於 LangChain）"""
        search_kwargs = {"k": k}
        if filter:
            search_kwargs["filter"] = filter
        
        return self.vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )
    
    def delete_documents(self, ids: List[str]):
        """刪除文件"""
        try:
            self.vectorstore.delete(ids=ids)
            print(f"✅ 已刪除 {len(ids)} 個文件")
        except Exception as e:
            print(f"❌ 刪除文件失敗: {e}")
            raise
    
    def get_collection_count(self) -> int:
        """取得 Collection 中的文件數量"""
        try:
            return self.vectorstore._collection.count()
        except Exception as e:
            print(f"❌ 取得文件數量失敗: {e}")
            return 0
