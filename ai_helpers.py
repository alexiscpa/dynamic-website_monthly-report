# ==================== AI 內容生成輔助函數 ====================

def generate_monthly_quote() -> str:
    """使用 Gemini API 生成每月激勵金句"""
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API 未設定,請在環境變數中設定 GEMINI_API_KEY"
        )
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = """你是一位專業的財務主管,請為財務處月報生成一句激勵人心的金句。

要求:
- 繁體中文
- 20-30 字
- 與財務工作相關
- 正向、專業、有深度
- 只回傳金句本身,不要有其他說明

範例風格:
- 細緻的數字背後,是財務人對公司價值的守護。
- 精準的帳目,是企業穩健前行的基石。
"""
        
        response = model.generate_content(prompt)
        quote = response.text.strip()
        
        # 移除可能的引號
        quote = quote.strip('"').strip('"').strip('"')
        
        return quote
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成金句失敗: {str(e)}"
        )

def generate_tax_news() -> List[dict]:
    """使用 Gemini API 生成 5 則稅務快訊"""
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API 未設定,請在環境變數中設定 GEMINI_API_KEY"
        )
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        current_month = datetime.now().strftime("%Y 年 %m 月")
        
        prompt = f"""你是一位台灣稅務專家,請生成 5 則 {current_month} 的稅務快訊。

要求:
- 繁體中文
- 每則包含「title」(10-15字) 和「content」(30-50字)
- 涵蓋台灣最新稅務法規、政策變動、申報提醒等
- 實用且專業
- 必須以 JSON 格式輸出,格式如下:
[
  {{"title": "標題", "content": "內容"}},
  {{"title": "標題", "content": "內容"}},
  {{"title": "標題", "content": "內容"}},
  {{"title": "標題", "content": "內容"}},
  {{"title": "標題", "content": "內容"}}
]

只回傳 JSON 陣列,不要有其他說明文字。
"""
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # 移除可能的 markdown 程式碼區塊標記
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()
        
        # 解析 JSON
        news_list = json.loads(content)
        
        # 驗證格式
        if not isinstance(news_list, list) or len(news_list) != 5:
            raise ValueError("生成的稅務快訊格式不正確")
        
        for item in news_list:
            if 'title' not in item or 'content' not in item:
                raise ValueError("稅務快訊項目缺少必要欄位")
        
        return news_list
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析 AI 回應失敗: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成稅務快訊失敗: {str(e)}"
        )
