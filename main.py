import os
import sys
import importlib.util
import hashlib
import time
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

login_id = os.getenv("LOGINID")
login_password = os.getenv("PASSWORD")

# パスワードハッシュ化（実際の運用ではbcrypt等を使用することを推奨）
def hash_password(password: str) -> str:
    """パスワードをハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

# 環境変数から取得したパスワードをハッシュ化
expected_password_hash = hash_password(login_password) if login_password else None

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from src.streamlit.components.base import init_page_config

# ファビコンの設定（ログインチェックの前に移動）
st.set_page_config(
    page_title="lallapalloozaアプリ",  # アプリ名を設定してください
    page_icon="🐿️",  # ここにファビコンとして使用したい絵文字または画像のパスを指定
    layout="wide",
)

def is_safe_path(base_path: str, target_path: str) -> bool:
    """パスが安全かどうかを検証"""
    try:
        base = Path(base_path).resolve()
        target = Path(target_path).resolve()
        return base in target.parents or base == target
    except (ValueError, RuntimeError):
        return False


def load_page_safely(page_path: str, pages_dir: str) -> bool:
    """安全にページを読み込む"""
    try:
        # パス検証
        if not is_safe_path(pages_dir, page_path):
            st.error("無効なパスです")
            return False
        
        # ファイル拡張子の検証
        if not page_path.endswith('.py'):
            st.error("Pythonファイルのみ実行可能です")
            return False
        
        # ファイルの存在確認
        if not os.path.exists(page_path):
            st.error("ファイルが見つかりません")
            return False
        
        # 安全なモジュール読み込み
        spec = importlib.util.spec_from_file_location("page_module", page_path)
        if spec is None or spec.loader is None:
            st.error("モジュールの読み込みに失敗しました")
            return False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # main関数が存在する場合は実行
        if hasattr(module, 'main'):
            module.main()
        else:
            st.warning("ページにmain関数が見つかりません")
        
        return True
        
    except ImportError as e:
        st.error(f"モジュールのインポートエラー: {e}")
        return False
    except SyntaxError as e:
        st.error(f"構文エラー: {e}")
        return False
    except Exception as e:
        import traceback
        st.error(f"予期しないエラーが発生しました: {e}\n{traceback.format_exc()}")
        return False


def check_password():
    """パスワード認証を行う"""
    # セッション状態の初期化
    if "auth" not in st.session_state:
        st.session_state.auth = {
            "authenticated": False,
            "login_time": None,
            "login_attempts": 0
        }
    
    # セッション有効期限（8時間）
    SESSION_TIMEOUT = 8 * 60 * 60  # 8時間
    
    # 認証済みでセッションが有効な場合
    if (st.session_state.auth["authenticated"] and 
        st.session_state.auth["login_time"] and 
        time.time() - st.session_state.auth["login_time"] < SESSION_TIMEOUT):
        return True
    
    # セッションが期限切れの場合、認証状態をリセット
    if st.session_state.auth["login_time"] and time.time() - st.session_state.auth["login_time"] >= SESSION_TIMEOUT:
        st.session_state.auth["authenticated"] = False
        st.session_state.auth["login_time"] = None
        st.warning("セッションが期限切れです。再度ログインしてください。")

    # ログイン試行回数制限（5回）
    if st.session_state.auth["login_attempts"] >= 5:
        st.error("ログイン試行回数が上限に達しました。しばらく時間をおいてから再試行してください。")
        return False

    if not st.session_state.auth["authenticated"]:
        # ユーザー名とパスワードの入力フォーム
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if not username or not password:
                st.error("ユーザー名とパスワードを入力してください")
                st.session_state.auth["login_attempts"] += 1
                return False
            
            # パスワードハッシュ化して比較
            password_hash = hash_password(password)
            
            if username == login_id and password_hash == expected_password_hash:
                st.session_state.auth["authenticated"] = True
                st.session_state.auth["login_time"] = time.time()
                st.session_state.auth["login_attempts"] = 0
                st.success("ログインに成功しました")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが違います")
                st.session_state.auth["login_attempts"] += 1
                return False
        return False

    return True


# メイン処理
if check_password():
    st.markdown(
        """
    <style>
    .st-emotion-cache-oq308l.eczjsme2 {
        font-family: 'Arial', sans-serif;
        font-size: 18px;
        font-weight: 600;
        color: #333;
        padding: 10px 15px;
        border-left: 4px solid #98e15b;
        background-color: #f8f8f8;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
    PAGES_DIR = "src/streamlit/pages"
    
    # カテゴリー定義（フォルダ名と表示名のマッピング）
    CATEGORIES = {
        "SNS投稿系": "📱 SNS投稿系",
        "その他": "🔧 その他",
    }

    # パスを絶対パスに変換
    pages_dir_abs = os.path.abspath(PAGES_DIR)
    if not os.path.exists(pages_dir_abs):
        st.error(f"ページディレクトリが見つかりません: {PAGES_DIR}")
        st.stop()

    dir_list = os.listdir(pages_dir_abs)
    pages = []
    dirs = []

    for file in dir_list:
        path = os.path.join(pages_dir_abs, file)
        if os.path.isdir(path):
            dirs.append(file)
            continue

    dirs = sorted(dirs)
    for dir in dirs:
        dir_path = os.path.join(pages_dir_abs, dir)
        files = [
            f
            for f in os.listdir(dir_path)
            if f != ".DS_Store" and f != "__pycache__" and f.endswith(".py")
        ]
        files = sorted(files)

        for file in files:
            path = os.path.join(dir_path, file)
            file_name = os.path.splitext(file)[0]
            trimed_file_name = file_name.split("_", 1)[1] if "_" in file_name else file_name
            trimed_dir_name = dir.split("_", 1)[1] if "_" in dir else dir
            pages.append({
                "path": path,
                "title": trimed_file_name,
                "category": dir,  # フォルダ名をカテゴリーとして使用
                "display_category": CATEGORIES.get(dir, dir)  # 表示用のカテゴリー名
            })

    # ページ選択用のセッション変数
    if "selected_page" not in st.session_state:
        st.session_state.selected_page = pages[0]["path"] if pages else None

    # サイドバーでカテゴリー分け表示
    if pages:
        st.sidebar.write("**📁 アプリカテゴリー**")
        
        # カテゴリー別にページを表示
        category_pages = {}
        for page in pages:
            category = page["category"]
            if category not in category_pages:
                category_pages[category] = []
            category_pages[category].append(page)
        
        # カテゴリーを表示順序でソート
        category_order = ["SNS投稿系", "YouTube系", "投資・株価系", "wp_test", "その他"]
        sorted_categories = sorted(category_pages.keys(), 
                                 key=lambda x: category_order.index(x) if x in category_order else 999)
        
        for category in sorted_categories:
            pages_in_category = category_pages[category]
            display_name = CATEGORIES.get(category, category)
            
            # デフォルトでSNS投稿系を展開
            expanded = (category == "SNS投稿系")
            
            with st.sidebar.expander(display_name, expanded=expanded):
                for page in pages_in_category:
                    # 現在選択されているページかどうかを判定
                    is_selected = st.session_state.selected_page == page["path"]
                    
                    # ボタンを作成
                    if st.button(f"📱 {page['title']}", key=f"page_{page['title']}", use_container_width=True):
                        st.session_state.selected_page = page["path"]
                        st.rerun()
        
        # ログアウトボタン
        st.sidebar.write("---")
        if st.sidebar.button("🚪 ログアウト"):
            st.session_state.auth["authenticated"] = False
            st.session_state.auth["login_time"] = None
            st.session_state.selected_page = None
            st.rerun()
        
        # 選択されたページを読み込み
        load_page_safely(st.session_state.selected_page, pages_dir_abs)
    else:
        st.sidebar.write("ページがありません")

        # ログアウトボタン
        if st.sidebar.button("ログアウト"):
            st.session_state.auth["authenticated"] = False
            st.session_state.auth["login_time"] = None
            st.session_state.selected_page = None
            st.rerun()
else:
    # ログイン前は何もしない
    pass
