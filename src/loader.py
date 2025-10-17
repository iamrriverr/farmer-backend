# src/loader.py
"""
文件載入器模組
支援多種文件格式的載入和分塊處理
"""
from typing import List, Dict, Optional
from pathlib import Path
from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredFileLoader,
    UnstructuredMarkdownLoader,
    TextLoader,
    CSVLoader,
    UnstructuredExcelLoader
)

    # LangChain >= 0.1.0
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os


class DocumentLoader:
    """
    統一的文件載入器
    支援多種格式：PDF, DOCX, TXT, MD, CSV, XLSX
    """
    
    # 支援的文件格式
    SUPPORTED_FORMATS = {
        '.pdf': PyPDFLoader,
        '.docx': Docx2txtLoader,
        '.doc': Docx2txtLoader,
        '.txt': TextLoader,
        '.md': UnstructuredMarkdownLoader,
        '.csv': CSVLoader,
        '.xlsx': UnstructuredExcelLoader,
        '.xls': UnstructuredExcelLoader,
    }
    
    @staticmethod
    def load_document(file_path: str) -> Optional[List[Document]]:
        """
        載入文件
        
        Args:
            file_path: 文件路徑
            
        Returns:
            Document 列表，失敗返回 None
        """
        try:
            # 檢查文件是否存在
            path = Path(file_path)
            if not path.exists():
                print(f"❌ 文件不存在: {file_path}")
                return None
            
            # 取得文件擴展名
            extension = path.suffix.lower()
            
            # 檢查是否支援
            if extension not in DocumentLoader.SUPPORTED_FORMATS:
                print(f"❌ 不支援的文件格式: {extension}")
                print(f"   支援的格式: {', '.join(DocumentLoader.SUPPORTED_FORMATS.keys())}")
                return None
            
            print(f"📄 載入文件: {path.name} ({extension})")
            
            # 選擇對應的 Loader
            loader_class = DocumentLoader.SUPPORTED_FORMATS[extension]
            
            # 特殊處理不同格式
            if extension == '.pdf':
                loader = loader_class(str(path), extract_images=True)
            elif extension == '.txt':
                loader = loader_class(str(path), encoding='utf-8')
            elif extension == '.csv':
                loader = loader_class(str(path), encoding='utf-8')
            else:
                loader = loader_class(str(path))
            
            # 載入文件
            documents = loader.load()
            
            if not documents:
                print(f"⚠️ 文件載入成功但內容為空: {path.name}")
                return None
            
            print(f"✅ 成功載入 {len(documents)} 個文件片段")
            
            # 添加基本 metadata
            for doc in documents:
                if 'source' not in doc.metadata:
                    doc.metadata['source'] = str(path)
                if 'filename' not in doc.metadata:
                    doc.metadata['filename'] = path.name
                if 'file_type' not in doc.metadata:
                    doc.metadata['file_type'] = extension.replace('.', '')
            
            return documents
            
        except Exception as e:
            print(f"❌ 載入文件失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def split_into_chunks(
        documents: List[Document],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Document]:
        """
        將文件分割成小塊
        
        Args:
            documents: Document 列表
            chunk_size: 每塊的大小（字元數）
            chunk_overlap: 塊之間的重疊大小
            
        Returns:
            分塊後的 Document 列表
        """
        try:
            # 使用 RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
            )
            
            # 分塊
            chunks = splitter.split_documents(documents)
            
            # 為每個 chunk 添加編號
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = i
                chunk.metadata['chunk_total'] = len(chunks)
            
            print(f"✅ 分塊完成: {len(documents)} 個文件 → {len(chunks)} 個分塊")
            
            return chunks
            
        except Exception as e:
            print(f"❌ 分塊失敗: {e}")
            return []
    
    @staticmethod
    def load_and_split(
        file_path: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Optional[List[Document]]:
        """
        載入並分塊（一步到位）
        
        Args:
            file_path: 文件路徑
            chunk_size: 塊大小
            chunk_overlap: 重疊大小
            
        Returns:
            分塊後的 Document 列表
        """
        documents = DocumentLoader.load_document(file_path)
        
        if not documents:
            return None
        
        chunks = DocumentLoader.split_into_chunks(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return chunks if chunks else None
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict:
        """
        取得文件資訊
        
        Args:
            file_path: 文件路徑
            
        Returns:
            文件資訊字典
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {"error": "文件不存在"}
            
            stat = path.stat()
            
            return {
                "filename": path.name,
                "file_path": str(path.absolute()),
                "file_size": stat.st_size,
                "file_size_mb": round(stat.st_size / 1024 / 1024, 2),
                "file_type": path.suffix.lower().replace('.', ''),
                "extension": path.suffix.lower(),
                "supported": path.suffix.lower() in DocumentLoader.SUPPORTED_FORMATS,
                "modified_time": stat.st_mtime,
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def validate_file(file_path: str) -> tuple[bool, str]:
        """
        驗證文件是否可以載入
        
        Args:
            file_path: 文件路徑
            
        Returns:
            (是否有效, 錯誤訊息)
        """
        path = Path(file_path)
        
        # 檢查文件是否存在
        if not path.exists():
            return False, f"文件不存在: {file_path}"
        
        # 檢查是否為文件
        if not path.is_file():
            return False, f"不是文件: {file_path}"
        
        # 檢查文件大小
        file_size = path.stat().st_size
        max_size = 100 * 1024 * 1024  # 100 MB
        if file_size > max_size:
            return False, f"文件過大: {round(file_size / 1024 / 1024, 2)} MB (最大 100 MB)"
        
        # 檢查文件格式
        extension = path.suffix.lower()
        if extension not in DocumentLoader.SUPPORTED_FORMATS:
            return False, f"不支援的格式: {extension}"
        
        # 檢查文件是否可讀
        try:
            with open(path, 'rb') as f:
                f.read(1)
        except Exception as e:
            return False, f"文件無法讀取: {str(e)}"
        
        return True, "文件驗證通過"
    
    @staticmethod
    def batch_load_documents(
        file_paths: List[str],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Document]:
        """
        批次載入多個文件
        
        Args:
            file_paths: 文件路徑列表
            chunk_size: 塊大小
            chunk_overlap: 重疊大小
            
        Returns:
            所有文件的分塊列表
        """
        all_chunks = []
        
        for file_path in file_paths:
            print(f"\n處理文件: {file_path}")
            
            # 驗證文件
            is_valid, error_msg = DocumentLoader.validate_file(file_path)
            if not is_valid:
                print(f"⚠️ 跳過: {error_msg}")
                continue
            
            # 載入並分塊
            chunks = DocumentLoader.load_and_split(
                file_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            if chunks:
                all_chunks.extend(chunks)
                print(f"✅ 新增 {len(chunks)} 個分塊")
            else:
                print(f"⚠️ 此文件未產生分塊")
        
        print(f"\n📊 批次處理完成: {len(file_paths)} 個文件 → {len(all_chunks)} 個分塊")
        
        return all_chunks


# 測試函數
def test_document_loader():
    """測試 DocumentLoader"""
    print("🧪 測試 DocumentLoader\n")
    
    # 測試文件資訊
    test_file = "./data/test.pdf"
    
    print("1. 取得文件資訊:")
    info = DocumentLoader.get_file_info(test_file)
    print(f"   {info}\n")
    
    # 測試驗證
    print("2. 驗證文件:")
    is_valid, msg = DocumentLoader.validate_file(test_file)
    print(f"   結果: {is_valid}")
    print(f"   訊息: {msg}\n")
    
    # 測試載入
    print("3. 載入文件:")
    documents = DocumentLoader.load_document(test_file)
    if documents:
        print(f"   ✅ 成功載入 {len(documents)} 個片段\n")
        
        # 測試分塊
        print("4. 分塊處理:")
        chunks = DocumentLoader.split_into_chunks(documents, chunk_size=500, chunk_overlap=100)
        print(f"   ✅ 生成 {len(chunks)} 個分塊\n")
        
        # 顯示第一個分塊
        if chunks:
            print("5. 第一個分塊內容:")
            print(f"   內容長度: {len(chunks[0].page_content)} 字元")
            print(f"   Metadata: {chunks[0].metadata}")
            print(f"   內容預覽: {chunks[0].page_content[:200]}...\n")
    else:
        print("   ❌ 載入失敗\n")


if __name__ == "__main__":
    test_document_loader()
