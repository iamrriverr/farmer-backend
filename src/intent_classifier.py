# src/intent_classifier.py
from typing import Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import json
import re

from .config import Config


class IntentClassifier:
    """
    使用輕量級 LLM 進行意圖分類
    
    判斷用戶問題是否需要 RAG 檢索、是否為閒聊或超出範圍
    """
    
    def __init__(self, api_key: str = None):
        """
        初始化分類器
        
        Args:
            api_key: Google API Key（可選，預設使用 Config）
        """
        # 使用 Gemini Flash 模型（速度快、成本低）
        self.classifier_llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-8b",  # 最輕量級的 Gemini 模型
            google_api_key=api_key or Config.GOOGLE_API_KEY,
            temperature=0,  # 確保判斷一致性
            max_tokens=50   # 只需要簡短的回應
        )
        
        # 建立 prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一個專業的意圖分類助手，負責判斷用戶問題的類型。

你的任務是分析問題並分類為以下三種類型之一：

1. **RAG** - 需要查詢文件資料庫的問題
   - 農業技術問題（種植、病蟲害、施肥、灌溉等）
   - 政策補助相關（申請流程、資格條件、金額等）
   - 具體操作方法（如何做某事）
   - 需要查詢文件、報告、記錄的問題
   - 專業知識查詢

2. **CHITCHAT** - 一般對話/閒聊
   - 問候語（你好、早安、謝謝等）
   - 關於助手本身的問題（你是誰、你會什麼）
   - 簡單的一般性問題
   - 情感表達
   - 不需要查詢資料的閒聊

3. **OUT_OF_SCOPE** - 超出服務範圍
   - 與農業完全無關的問題
   - 金融投資（股票、基金、理財）
   - 娛樂八卦（電影、明星、遊戲）
   - 政治敏感話題
   - 醫療診斷
   - 法律諮詢（非農業相關）

請以 JSON 格式回應，必須包含以下欄位：
{{
    "intent": "RAG|CHITCHAT|OUT_OF_SCOPE",
    "confidence": 0.0-1.0,
    "reason": "判斷原因的簡短說明（中文，20字內）"
}}

重要：只回傳 JSON，不要有其他文字。"""),
            ("human", "問題：{question}")
        ])
        
        print("✅ 意圖分類器初始化完成（使用 Gemini Flash）")
    
    def classify(self, question: str) -> Dict:
        """
        分類用戶問題
        
        Args:
            question: 用戶問題
            
        Returns:
            {
                "use_rag": bool,
                "intent": str,  # "rag", "chitchat", "out_of_scope"
                "confidence": float,  # 0-1
                "reason": str
            }
        """
        try:
            # 調用 LLM 進行分類
            chain = self.prompt | self.classifier_llm
            response = chain.invoke({"question": question})
            
            # 解析 LLM 回應
            content = response.content.strip()
            
            # 嘗試提取 JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # 如果無法解析 JSON，嘗試從文字中提取
                content_upper = content.upper()
                if "RAG" in content_upper and "OUT_OF_SCOPE" not in content_upper:
                    result = {
                        "intent": "RAG",
                        "confidence": 0.8,
                        "reason": "LLM 判斷為業務問題"
                    }
                elif "CHITCHAT" in content_upper:
                    result = {
                        "intent": "CHITCHAT",
                        "confidence": 0.8,
                        "reason": "LLM 判斷為一般對話"
                    }
                elif "OUT_OF_SCOPE" in content_upper:
                    result = {
                        "intent": "OUT_OF_SCOPE",
                        "confidence": 0.9,
                        "reason": "LLM 判斷為超出範圍"
                    }
                else:
                    raise ValueError(f"無法解析 LLM 回應: {content}")
            
            # 標準化 intent 為小寫
            intent = result.get("intent", "CHITCHAT").upper()
            
            # 轉換為標準格式
            return {
                "use_rag": intent == "RAG",
                "intent": intent.lower(),
                "confidence": float(result.get("confidence", 0.8)),
                "reason": result.get("reason", "LLM 自動判斷")
            }
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 解析失敗: {e}, 內容: {content}")
            # Fallback: 簡單關鍵字匹配
            return self._fallback_classify(question)
            
        except Exception as e:
            print(f"❌ 意圖分類失敗: {e}")
            # Fallback: 簡單關鍵字匹配
            return self._fallback_classify(question)
    
    def _fallback_classify(self, question: str) -> Dict:
        """
        備用分類方法（當 LLM 失敗時）
        使用簡單的關鍵字匹配
        """
        question_lower = question.lower()
        
        # 農業相關關鍵字
        agriculture_keywords = [
            "水稻", "病蟲害", "防治", "種植", "肥料", "農藥", "栽培", 
            "灌溉", "施肥", "除草", "補助", "申請", "政策", "規定",
            "文件", "資料", "報告", "如何", "怎麼", "方法"
        ]
        
        # 閒聊關鍵字
        chitchat_keywords = [
            "你好", "謝謝", "再見", "早安", "晚安", "哈囉",
            "你是誰", "你叫什麼"
        ]
        
        # 超出範圍關鍵字
        out_of_scope_keywords = [
            "股票", "投資", "理財", "電影", "音樂", "遊戲",
            "政治", "選舉"
        ]
        
        # 判斷邏輯
        if any(kw in question_lower for kw in out_of_scope_keywords):
            return {
                "use_rag": False,
                "intent": "out_of_scope",
                "confidence": 0.7,
                "reason": "關鍵字匹配：超出範圍"
            }
        elif any(kw in question_lower for kw in agriculture_keywords):
            return {
                "use_rag": True,
                "intent": "rag",
                "confidence": 0.7,
                "reason": "關鍵字匹配：業務相關"
            }
        elif any(kw in question_lower for kw in chitchat_keywords) and len(question) < 20:
            return {
                "use_rag": False,
                "intent": "chitchat",
                "confidence": 0.7,
                "reason": "關鍵字匹配：閒聊"
            }
        else:
            # 預設為 RAG（安全起見）
            return {
                "use_rag": True,
                "intent": "rag",
                "confidence": 0.5,
                "reason": "預設策略：業務問題"
            }
    
    async def classify_async(self, question: str) -> Dict:
        """
        非同步版本的分類（用於 async 環境）
        """
        try:
            chain = self.prompt | self.classifier_llm
            response = await chain.ainvoke({"question": question})
            
            content = response.content.strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                result = json.loads(json_match.group())
            else:
                content_upper = content.upper()
                if "RAG" in content_upper and "OUT_OF_SCOPE" not in content_upper:
                    result = {"intent": "RAG", "confidence": 0.8, "reason": "LLM 判斷"}
                elif "CHITCHAT" in content_upper:
                    result = {"intent": "CHITCHAT", "confidence": 0.8, "reason": "LLM 判斷"}
                elif "OUT_OF_SCOPE" in content_upper:
                    result = {"intent": "OUT_OF_SCOPE", "confidence": 0.9, "reason": "LLM 判斷"}
                else:
                    return self._fallback_classify(question)
            
            intent = result.get("intent", "CHITCHAT").upper()
            
            return {
                "use_rag": intent == "RAG",
                "intent": intent.lower(),
                "confidence": float(result.get("confidence", 0.8)),
                "reason": result.get("reason", "LLM 自動判斷")
            }
            
        except Exception as e:
            print(f"❌ 非同步意圖分類失敗: {e}")
            return self._fallback_classify(question)


# 測試函數
def test_classifier():
    """測試分類器"""
    classifier = IntentClassifier()
    
    test_cases = [
        "水稻有哪些常見的病蟲害？",
        "如何申請農業補助？",
        "你好，早安",
        "你是誰？",
        "幫我分析一下台積電的股票",
        "今天的天氣如何？",
        "種植水稻需要注意什麼？",
        "謝謝你的幫助",
        "最近有什麼好看的電影推薦？"
    ]
    
    print("\n" + "="*60)
    print("意圖分類測試")
    print("="*60 + "\n")
    
    for question in test_cases:
        result = classifier.classify(question)
        print(f"問題: {question}")
        print(f"結果: {result['intent']} (置信度: {result['confidence']:.2f})")
        print(f"原因: {result['reason']}")
        print(f"使用 RAG: {'是' if result['use_rag'] else '否'}")
        print("-" * 60)


if __name__ == "__main__":
    test_classifier()
