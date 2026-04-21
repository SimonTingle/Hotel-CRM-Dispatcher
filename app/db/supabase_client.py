from fastapi import Request


def create_supabase_client(url: str, key: str, test_mode: bool = False):
    if test_mode or not url or url.startswith("https://test"):
        return None
    from supabase import create_client
    return create_client(url, key)


def get_supabase(request: Request):
    return request.app.state.supabase
