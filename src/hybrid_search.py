# src/hybrid_search.py
from typing import List, Dict, Optional
from langchain.schema import Document
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
import jieba
import re

class ChineseTextPreprocessor:
    """
    中文文本預處理器
    針對中文和農業領域優化的分詞
    """
    
    def __init__(self):
        # 🔥 農業領域自定義詞典（擴充）
        self.custom_dict = [
            # 農業技術
            "水稻", "病蟲害", "施肥", "灌溉", "育苗", "稻熱病", "紋枯病", "白葉枯病",
            "有機肥", "化學肥", "滴灌", "噴灌", "溫室", "大棚", "除草劑", "殺蟲劑",
            "農藥", "肥料", "種子", "秧苗", "收割", "播種", "插秧", "翻土",
            
            # 政策補助
            "補助", "申請", "資格", "流程", "審核", "撥款", "農會", "農保", "農機補助",
            "老農津貼", "農民健康保險", "農業天然災害救助", "休耕補助",
            
            # 業務相關
            "繼承", "存款", "繼承人", "證件", "戶籍謄本", "正本", "國民身分證",
            "除戶謄本", "親屬關係證明", "遺產分割協議書", "印鑑證明", "身分證影本"
        ]
        
        for word in self.custom_dict:
            jieba.add_word(word)
        
        # 停用詞表（擴充）
        self.stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不',
            '人', '都', '一', '一個', '上', '也', '很', '到', '說',
            '要', '去', '你', '會', '著', '沒有', '看', '好',
            '這樣', '那樣', '如何', '什麼', '怎麼', '請問', '可以', '能',
            '為了', '因為', '所以', '但是', '而且', '或者', '還是', '已經'
        }
    
    def preprocess(self, text: str) -> List[str]:
        """
        預處理文本並返回分詞結果
        
        Args:
            text: 原始文本
            
        Returns:
            分詞後的 token 列表
        """
        # 1. 保留中文、英文、數字
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())
        
        # 2. jieba 分詞
        tokens = list(jieba.cut(text))
        
        # 3. 過濾停用詞和短詞
        tokens = [t for t in tokens if len(t) > 1 and t not in self.stopwords]
        
        return tokens

class HybridSearchManager:
    """
    混合搜尋管理器
    結合 BM25 和向量搜尋，使用 LangChain 的 EnsembleRetriever
    """
    
    def __init__(self, vector_retriever, documents: List[Document] = None):
        """
        初始化混合搜尋
        
        Args:
            vector_retriever: 向量檢索器（來自 VectorStoreManager）
            documents: 文件列表（用於建立 BM25 索引）
        """
        self.vector_retriever = vector_retriever
        self.preprocessor = ChineseTextPreprocessor()
        self.documents = documents or []
        self.bm25_retriever = None
        
        if self.documents:
            self._initialize_bm25()
    
    def _initialize_bm25(self):
        """初始化 BM25 檢索器"""
        try:
            # 使用自定義預處理函數
            self.bm25_retriever = BM25Retriever.from_documents(
                self.documents,
                preprocess_func=self.preprocessor.preprocess
            )
            # 設定返回文件數量
            self.bm25_retriever.k = 5
            print(f"✅ BM25 檢索器已初始化，文件數量：{len(self.documents)}")
        except Exception as e:
            print(f"❌ BM25 初始化失敗: {e}")
            self.bm25_retriever = None
    
    def add_documents(self, new_documents: List[Document]):
        """添加新文件到 BM25 索引"""
        self.documents.extend(new_documents)
        self._initialize_bm25()  # 重新初始化
        print(f"✅ BM25 索引已更新（總文件數：{len(self.documents)}）")
    
    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        filter: Optional[Dict] = None
    ) -> List[Document]:
        """
        執行混合搜尋
        
        Args:
            query: 搜尋查詢
            k: 返回文件數量
            bm25_weight: BM25 權重（0-1）
            vector_weight: 向量權重（0-1）
            filter: Metadata 過濾條件
            
        Returns:
            合併後的文件列表
        """
        if not self.bm25_retriever:
            print("⚠️ BM25 未初始化，僅使用向量搜尋")
            return self.vector_retriever.get_relevant_documents(query)[:k]
        
        try:
            # 設定檢索數量
            self.bm25_retriever.k = k
            
            # 建立 Ensemble Retriever（使用 RRF 演算法合併）
            ensemble_retriever = EnsembleRetriever(
                retrievers=[self.bm25_retriever, self.vector_retriever],
                weights=[bm25_weight, vector_weight],
                c=60  # RRF 的 k 參數
            )
            
            # 執行混合搜尋
            results = ensemble_retriever.get_relevant_documents(query)
            
            # 限制返回數量
            results = results[:k]
            
            print(f"✅ 混合搜尋完成：返回 {len(results)} 個結果（BM25={bm25_weight}, 向量={vector_weight}）")
            return results
            
        except Exception as e:
            print(f"❌ 混合搜尋失敗: {e}，回退到純向量搜尋")
            return self.vector_retriever.get_relevant_documents(query)[:k]
    
    def get_bm25_only(self, query: str, k: int = 5) -> List[Document]:
        """僅使用 BM25 搜尋（用於測試對比）"""
        if not self.bm25_retriever:
            return []
        self.bm25_retriever.k = k
        return self.bm25_retriever.get_relevant_documents(query)
    
    def get_vector_only(self, query: str, k: int = 5) -> List[Document]:
        """僅使用向量搜尋（用於測試對比）"""
        return self.vector_retriever.get_relevant_documents(query)[:k]
