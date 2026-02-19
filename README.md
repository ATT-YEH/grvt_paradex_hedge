# grvt_paradex_hedge
grvt_paradex_hedge/

├── .env                    # 存放私鑰與 API Key

├── requirements.txt        # 核心依賴

├── launch.py               # 原 launch_hedge_grvtparadex.py

├── main_logic.py           # 原 hedge_mode_grvtparadex.py

├── reporter.py             # (新) 專門處理 Telegram 訊息的模組

└── exchanges/

    ├── __init__.py
	
    ├── grvthedge.py        # GRVT 客戶端封裝
	
    ├── account.py          # Paradex 帳戶處理
	
    └── interceptor.py      # Auth 攔截器
