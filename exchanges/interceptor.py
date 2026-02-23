"""
Auth 请求拦截器
为 /v1/auth 请求添加 token_usage=interactive 参数
"""


class ParadexProxyClient:
    """Paradex HTTP 客户端代理"""
    
    _patched = False
    _enabled = True
    _token_usage = "interactive"
    
    @classmethod
    def patch_http_client(cls, enabled: bool = True, token_usage: str = "interactive"):
        cls._enabled = enabled
        cls._token_usage = token_usage
        
        if cls._patched:
            return
        
        from paradex_py.api.http_client import HttpClient
        
        # 保存原始的 _prepare_request_kwargs 方法
        original_prepare = HttpClient._prepare_request_kwargs
        
        def patched_prepare(self, *args, **kwargs):
            # 获取 url 参数（第二个位置参数或关键字参数）
            if len(args) >= 2:
                url = args[1]
                args = list(args)
                
                # 修改 URL
                if cls._enabled and "/auth" in url and "token_usage" not in url:
                    separator = "&" if "?" in url else "?"
                    args[1] = f"{url}{separator}token_usage={cls._token_usage}"
                
                args = tuple(args)
            elif 'url' in kwargs:
                url = kwargs['url']
                if cls._enabled and "/auth" in url and "token_usage" not in url:
                    separator = "&" if "?" in url else "?"
                    kwargs['url'] = f"{url}{separator}token_usage={cls._token_usage}"
            
            return original_prepare(self, *args, **kwargs)
        
        HttpClient._prepare_request_kwargs = patched_prepare
        cls._patched = True
    
    @classmethod
    def enable(cls):
        cls._enabled = True
    
    @classmethod
    def disable(cls):
        cls._enabled = False
    
    @classmethod
    def set_token_usage(cls, value: str):
        cls._token_usage = value
    
    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled


def setup_paradex_with_token_usage(
    env: str = "prod",
    l2_private_key: str = None,
    l2_address: str = None,
    enabled: bool = True,
    token_usage: str = "interactive"
):
    from paradex_py import ParadexSubkey
    
    ParadexProxyClient.patch_http_client(enabled=enabled, token_usage=token_usage)
    
    paradex = ParadexSubkey(
        env=env,
        l2_private_key=l2_private_key,
        l2_address=l2_address
    )
    
    return paradex


class AuthInterceptor:
    @classmethod
    def install(cls, enabled: bool = True, token_usage: str = "interactive"):
        ParadexProxyClient.patch_http_client(enabled=enabled, token_usage=token_usage)
    
    @classmethod
    def enable(cls):
        ParadexProxyClient.enable()
    
    @classmethod
    def disable(cls):
        ParadexProxyClient.disable()
