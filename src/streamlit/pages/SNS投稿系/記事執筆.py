import streamlit as st
import os
import json
import gspread
import requests
import time
from anthropic import Anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from io import BytesIO
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import ast
import functools

dotenv.load_dotenv()


MODEL = "claude-sonnet-4-20250514"    
google_search_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
ai_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# Google Drive設定
PARENT_FOLDER_ID = "1O_TG3aDkzs1sOVE1v6B4hjByNmsgAwCx"

# OAuth2.0認証設定
SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate_oauth():
    """Service Account認証でGoogle Drive APIクライアントを取得"""
    try:
        # Streamlit secretsからService Account認証情報を取得
        if 'gcp_service_account2' in st.secrets:
            service_account_info = st.secrets['gcp_service_account2']
            
            # Service Account認証情報を作成
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
            
            return build('drive', 'v3', credentials=credentials)
        
        # フォールバック: 環境変数から認証情報を取得
        credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        token_json = os.getenv('GOOGLE_TOKEN_JSON')
        
        if credentials_json and token_json:
            # Heroku環境での認証
            credentials_data = json.loads(credentials_json)
            token_data = json.loads(token_json)
            
            # 認証情報を作成
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            
            # トークンが期限切れの場合は更新
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # 新しい認証フローを開始
                    flow = InstalledAppFlow.from_client_config(credentials_data, SCOPES)
                    creds = flow.run_local_server(port=0)
            
            return build('drive', 'v3', credentials=creds)
        else:
            # ローカル環境用のOAuth2.0認証
            creds = None
            # token.jsonがあれば読み込み
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            # 認証が必要な場合
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            
            return build('drive', 'v3', credentials=creds)
    
    except Exception as e:
        st.write(f"Failed to initialize Google Drive client: {str(e)}")
        return None

html_writing_rule: str = """\
            <h2>, <h3>, <h4>, <h5>, <h6>
            - 見出しスタイル (大きさ順)
            - 記事の構造化と主要なポイントを示すために使用

            <p>
            - 段落スタイル
            - 本文の文章を記述するために使用

            <a>
            - リンクスタイル
            - 関連ページへのリンクを設定するために使用

            <ul>, <ol>, <li>
            - リストスタイル
            - 箇条書きリストや番号付きリストを作成するために使用

            <table>, <tr>, <td>, <th>
            - テーブルスタイル
            - データを表形式で表示するために使用

            <blockquote>
            - 引用スタイル
            - 他の情報源からの引用を示すために使用

            <pre>, <code>
            - コードブロックスタイル
            - プログラムコードやターミナルの出力を表示するために使用

            <figure>, <figcaption>
            - 図の説明スタイル
            - 画像やイラストに説明を付けるために使用

            <font color=red> テキスト </font>
            - 赤文字スタイル
            - 重要でネガティブな情報を示すために使用

            <font color=blue> テキスト </font>
            - 青文字スタイル
            - 重要でポジティブな情報を示すために使用
            """

def get_gspread_client():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    try:
        # Streamlit secretsからService Account認証情報を取得
        if 'gcp_service_account2' in st.secrets:
            service_account_info = st.secrets['gcp_service_account2']
            
            # Service Account認証情報を作成
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
            
            return gspread.authorize(credentials)
        
        # フォールバック: 環境変数から認証情報を取得
        credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        token_json = os.getenv('GOOGLE_TOKEN_JSON')
        
        if credentials_json and token_json:
            # Heroku環境での認証
            credentials_data = json.loads(credentials_json)
            token_data = json.loads(token_json)
            
            # 認証情報を作成
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            
            # トークンが期限切れの場合は更新
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # 新しい認証フローを開始
                    flow = InstalledAppFlow.from_client_config(credentials_data, SCOPES)
                    creds = flow.run_local_server(port=0)
            
            return gspread.authorize(creds)
        else:
            # ローカル環境用のOAuth2.0認証
            creds = None
            # token.jsonがあれば読み込み
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            # 認証が必要な場合
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

            return gspread.authorize(creds)

    except Exception as e:
        st.write(f"Failed to initialize gspread client: {str(e)}")
        return None

def extract_domain_from_url(url):
    """URLからドメインを正確に抽出する関数"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # www.プレフィックスを除去
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except:
        return None

def search_google(keyword, num_results=10):
    """Google Custom Search APIを使用してキーワード検索を実行"""
    if not google_search_api_key or not search_engine_id:
        st.write("Google Search API設定が不足しています")
        return []
    
    # 除外したいサイトのドメインリスト
    excluded_domains = [
        # ソーシャルメディアプラットフォーム
        'instagram.com', 'twitter.com', 'x.com', 'facebook.com', 'linkedin.com',
        'tiktok.com', 'youtube.com', 'reddit.com', 'pinterest.com',
        
        # 動的コンテンツサイト
        'spotify.com', 'music.apple.com', 'soundcloud.com', 'vimeo.com',
        'dailymotion.com', 'twitch.tv', 'netflix.com', 'amazon.com',
        
        # その他の除外したいサイト
        'amazon.co.jp', 'rakuten.co.jp', 'yahoo.co.jp', 'google.com',
        'wikipedia.org', 'wikipedia.jp', 'qiita.com', 'zenn.dev',
        'note.com', 'hatena.ne.jp', 'ameblo.jp', 'fc2.com',
        'livedoor.com', 'goo.ne.jp', 'infoseek.co.jp'
    ]
    
    # 除外キーワードを構築
    exclude_terms = []
    for domain in excluded_domains:
        exclude_terms.append(f"-site:{domain}")
    
    # 検索クエリに除外条件を追加
    search_query = f"{keyword} {' '.join(exclude_terms)}"
    
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': google_search_api_key,
            'cx': search_engine_id,
            'q': search_query,
            'num': min(num_results, 10),  # Google Custom Searchは最大10件
            'lr': 'lang_ja',  # 日本語検索結果を優先
            'gl': 'jp'  # 日本の地域設定
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        results = []
        excluded_count = 0
        
        if 'items' in data:
            for item in data['items']:
                url = item.get('link', '')
                
                # 正確なドメイン抽出と判定
                url_domain = extract_domain_from_url(url)
                should_exclude = False
                excluded_domain = None
                
                if url_domain:
                    for domain in excluded_domains:
                        # 完全一致またはサブドメインの場合のみ除外
                        if url_domain == domain or url_domain.endswith('.' + domain):
                            should_exclude = True
                            excluded_domain = domain
                            break
                
                if not should_exclude:
                    results.append({
                        'title': item.get('title', ''),
                        'url': url,
                        'snippet': item.get('snippet', '')
                    })
                else:
                    excluded_count += 1
                    st.write(f"    除外されたサイト: {url} (ドメイン: {excluded_domain})")
        
        st.write(f"    検索結果: {len(results)}件 (除外: {excluded_count}件)")
        return results
    
    except Exception as e:
        st.write(f"❌ Google検索エラー: {str(e)}")
        return []
    
# 見出し構成文字列をH2ごとのグループに分ける処理
def group_headings_by_h2(article_structure):
    """見出し構成文字列をH2ごとにグループ分けする関数"""
    grouped_headings = []
    current_h2_group = None
    
    # 文字列を行ごとに分割
    lines = article_structure.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:  # 空行をスキップ
            continue
            
        # H2見出しを検出（"H2 "で始まる行）
        if line.startswith('H2 '):
            # 新しいH2グループを作成
            heading_text = line.strip()  # 見出しレベルも含めて保存
            current_h2_group = {
                'h2_title': heading_text,
                'ordered_headings': [heading_text]  # 順番を保持するためのリスト
            }
            grouped_headings.append(current_h2_group)
        
        # H3見出しを検出（"H3 "で始まる行）
        elif line.startswith('H3 ') and current_h2_group is not None:
            heading_text = line.strip()  # 見出しレベルも含めて保存
            current_h2_group['ordered_headings'].append(heading_text)
        
        # H4見出しを検出（"H4 "で始まる行）
        elif line.startswith('H4 ') and current_h2_group is not None:
            heading_text = line.strip()  # 見出しレベルも含めて保存
            current_h2_group['ordered_headings'].append(heading_text)
    
    return grouped_headings


def extract_main_content(url, url_index=None):
    """URLからメインコンテンツを抽出"""
    url_log_prefix = f"[URL{url_index}]" if url_index else "[URL]"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 不要な要素を削除（script, style, noscriptのみ）
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()
        
        # 全文から見出しタグ（H1〜H6）を抽出
        all_headings = soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6'])
        
        # 完全一致で除外する見出しのキーワード
        exact_exclude_keywords = [
            'PR','FAQ','情報', '配信中','プライバシーポリシー', 'イベント', '最新の記事', '参考文献','共有', 
            '利用規約', 'よくある質問','サービス','参照文献', 'よく寄せられる質問','関連するコンテンツ',
            '関連する用語', 'タグ', 'ランキング', 'はてなブログをはじめよう！', '関連会社', '製品情報', '私たちの取り組み', 
            'サービス紹介', '', 'お役立ち資料','copyright','総合', 'トピックス', '関連のある記事',
            '参考情報', '更新履歴', '参考','search','最近の投稿', 'SNS', '関連ファイル', 'お問合せ先', 'その他', 
            'よく検索されているワード', 'おすすめ資料', '公式SNS', '注意事項', '資格',
            'ad', '映像', 'ビデオ', '著作権', 'もっと読む' ,'タグ一覧', 'top', '最後に', '投稿者', '関連AIツール', 
            '急上昇AIツール','ダウンロード', 'この投稿を報告する', '銀行振込', 'メーカーサイト', '筆者プロフィール',
            '著者プロフィール', '著者', '筆者', '関連サービス', '今日のピックアップ', 'おすすめの書籍', '注目記事',
            'あなたにお薦め','ランキング IT', '運営会社', '関連サイト', '追記', '出典', 'バックナンバー', 'あわせて読みたい',
            '気になる資料を今すぐダウンロード','タグで探す', 'ブログ', '製品','資料ダウンロード', '記事ランキング','RSSフィード',
            '会員メニュー','サイト内メニュー','読み進める','よく読まれている記事','お薦めコンテンツ', '関連Webサイト',
            'エピソード','番組について','サイト内の現在位置','製品外観','製品仕様','問合せ先','用語解説','今日の生放送',
            '当サイトの情報','地域で選ぶ','メディア','サービス資料','ヘルプとサポート','お客さま事例','ラインナップ',
            'メールマガジン登録','月間ランキング','サービス・ソリューションTOP','製品TOP','料金TOP','中堅中小企業向けサイトTOP',
            '経営情報TOP','トップ記事','関連トピックス','海外ビジネス情報','関連マーケットレポート','メールマガジン',
            '動画コンテンツ集', 'ビジネスランキング','最新情報','吉原 一樹','アプリのプライバシー',
            'サステナビリティTOP', 'OPEN HUB TOP', 'Smart World TOP', 'サービス・ソリューション TOP', 'モバイル TOP',
            'ドコモビジネスウォッチTOP', '中堅中小企業向けサービス・ソリューションTOP', 'ドコモビジネスオンラインショップ',
            'はじめてでも安心のサポート体制','料金についてはこちら','ご提供サービス一覧','News'


            'Recent Posts',
            'アフリカ、中東、インド',
            'アジア太平洋',
            'ヨーロッパ',
            'ラテンアメリカ、カリブ海地域',
            '米国およびカナダ'

        ]
                
        # 部分一致で除外する見出しのキーワード
        partial_exclude_keywords = [
            # 日本語
            '脚注', '注釈', '引用', 'リンク', '映像', 'ビデオ', '特集', 'コラム', '連載', '講座', 'メルマガ登録',
            '広告', 'スポンサー', 'プロモーション', 'コメント', 'レビュー', '口コミ', 'シェア', 'ソーシャル','発信中',
            'ナビゲーション', 'サイトマップ', 'お問い合わせ', '問い合わせ', 'コンタクト', '免責事項', '関連商品', '関連書籍',
            'コピーライト', 'Copyright', 'ページトップ', 'ページ上部', 'ページ下部', 'サイドバー', 'サイドメニュー', '補足情報',
            '新着記事', '参考記事', '関連記事', '管理人', 'アーカイブ', 'カテゴリー', '取引', 'お知らせ', 'ニュース', '最新記事',
            '商標', 'SDGs', '目次', 'セミナー', 'キーワード', '相談', '保護者', 'CONTACT', 'この記事を書いた人', '資料請求',
            '製品関連', 'おすすめの記事', '監修者', 'この情報は役に立ちましたか', 'ありがとうございます。', '会社概要', 'お役立ち情報', '会社概要',
            '製品・バージョン', '関連情報', 'おすすめ記事', '注目の記事', 'カテゴリ', '当社', '会社情報','注目情報','カタログ',
            'お気に入り', 'トライアル', 'おすすめのタグ', '人気の記事', '関連テーマ', '執筆者', '索引', 'の方は', '関連する記事', 'あわせて読みたい記事', 
            '閲覧履歴', '人気記事', '関連タグ', '人気タグ', 'アクセスランキング', '無料でダウンロード', 'ダウンロードください', 'ダウンロードしてください'
            '企業概要', '企業ビジョン', '地域の取り組み', '採用情報', 'メンバー紹介', 'メディア掲載', 'ウェビナー', '会社案内', 'この記事を書いたライター',
            '他のおすすめ', 'よくあるご質問', 'おすすめ商品', '他のおすすめ', '企業情報', 'その他のソリューション', '関連ソリューション', 'おすすめソリューション',
            'お客様の声', '注目トピックス','ヒントを探す', '関する記事', '新着','参考資料', 'ピックアップコンテンツ', '製品一覧', 'ソリューション一覧', '編集部',
            '関連コンテンツ', 'タグから探す', '関連する他の記事', 'ご検討中', 'ホワイトペーパー', 'このページを共有', 'ここから先は', 'ツールを探す',
            'メーカーサイト', '監修', '新商品', '記事一覧', '受け付け中','ピックアップ', '公式SNS','の記事', 'おすすめ無料サービス', 'おすすめの投稿',
            '関連するプロダクト', '日本一透明性の高いAIプロフェッショナル集団','資料ダウンロード','勉強会','最新家電','NTTデータ',
            '記事検索','株式会社ブレインパッド','最新号紹介','その他情報','作成者','DXメルマガ配信中','募集中','IR情報','フォロー',
            'メディア','最新情報','紹介されました','お読みください','リコーの'
                        
            # 英語
            'references', 'bibliography', 'footnotes', 'notes', 'citations', 'CATEGORY', 'LINK', 'COMPANY', 'CONTACT',
            'related', 'links', 'external', 'useful', 'video', 'videos', 'media', 'multimedia', 'gallery', 'Pick Up',
            'featured', 'special', 'column', 'series', 'collection', 'advertisement', 'sponsored', 'promotion', 'promo',
            'comments', 'reviews', 'ratings', 'feedback', 'testimonials', 'share', 'sharing', 'social', 'follow',
            'navigation', 'menu', 'sitemap', 'breadcrumb', 'contact', 'about', 'INDEX', 'privacy', 'terms', 'disclaimer',
            'legal', 'ARTICLE', 'sidebar', 'widget', 'EVENT', 'more', 'read more', 'continue reading', 'full article',
            'subscribe', 'newsletter', 'sign up', 'join', 'popular', 'trending', 'most read', 'recommended', 'RANKING',
            'categories', 'tags', 'archive', 'login', 'sign in', 'register', 'account', 'Recommend', 'RECRUIT', 'PRODUCTS', 
            'SERVICE','Footer','Members',
            'undefined', 'PICKUP TOPICS'
        ]
        
        # 見出しの階層構造を考慮したグループ削除機能
        def should_exclude_heading(heading):
            """見出しが除外対象かどうかを判定"""
            text_content = heading.get_text(strip=True)
            
            # 完全一致チェック
            for keyword in exact_exclude_keywords:
                if keyword.lower() == text_content.lower():
                    return True, f"完全一致: {keyword}"
            
            # 部分一致チェック
            for keyword in partial_exclude_keywords:
                if keyword.lower() in text_content.lower():
                    return True, f"部分一致: {keyword}"
            
            return False, None
        
        def get_heading_level(heading):
            """見出しのレベルを取得（H2=2, H3=3, ...）"""
            return int(heading.name[1])
        
        def find_next_heading_of_same_level(headings, current_index, target_level):
            """同じレベルの次の見出しを探す"""
            for i in range(current_index + 1, len(headings)):
                if get_heading_level(headings[i]) == target_level:
                    return i
            return len(headings)  # 見つからない場合は最後
        
        # 見出しを階層構造でグループ化して除外
        all_headings_before_filter = []
        excluded_headings = []
        headings = []
        excluded_indices = set()  # 除外された見出しのインデックス
        
        # 「まとめ」見出しの位置を特定
        matome_index = -1
        for i, heading in enumerate(all_headings):
            text_content = heading.get_text(strip=True)
            if text_content.lower() == 'まとめ':
                matome_index = i
                break
        
        # 最初のパス：除外対象の見出しを特定
        for i, heading in enumerate(all_headings):
            tag_name = heading.name
            text_content = heading.get_text(strip=True)
            
            # フィルタリング前の見出しを記録
            clean_heading_before = f"<{tag_name}>{text_content}</{tag_name}>"
            all_headings_before_filter.append(clean_heading_before)
            
            # 「まとめ」見出し以降のすべての見出しを除外（まとめ見出し自体は残す）
            if matome_index != -1 and i > matome_index:
                excluded_indices.add(i)
                excluded_headings.append({
                    'heading': clean_heading_before,
                    'excluded_keyword': 'まとめ',
                    'group_size': 1,
                    'reason': 'まとめ見出し以降の削除'
                })
                continue
            
            # 除外対象かどうかをチェック
            should_exclude, excluded_keyword = should_exclude_heading(heading)
            
            if should_exclude:
                # 除外対象の場合、その見出しとその下位見出しをグループとして除外
                current_level = get_heading_level(heading)
                next_same_level_index = find_next_heading_of_same_level(all_headings, i, current_level)
                
                # 現在の見出しから次の同じレベルまでの範囲を除外
                for j in range(i, next_same_level_index):
                    excluded_indices.add(j)
                
                # 除外理由を判定
                if next_same_level_index - i > 1:
                    # グループとして削除された場合
                    reason = f"上位見出しが削除 (キーワード: {excluded_keyword})"
                else:
                    # 単独で削除された場合
                    reason = f"''''''{excluded_keyword}''''' "
                
                excluded_headings.append({
                    'heading': clean_heading_before,
                    'excluded_keyword': excluded_keyword,
                    'group_size': next_same_level_index - i,
                    'reason': reason
                })
        
        # 2番目のパス：除外されていない見出しのみを有効な見出しリストに追加
        for i, heading in enumerate(all_headings):
            if i not in excluded_indices:
                tag_name = heading.name
                text_content = heading.get_text(strip=True)
                clean_heading = f"<{tag_name}>{text_content}</{tag_name}>"
                headings.append(clean_heading)
        
        # # 見出しフィルタリング結果をログに出力
        # log_collector.add_log(f"{url_log_prefix} 📝 見出しフィルタリング結果:")
        # log_collector.add_log(f"{url_log_prefix}   - フィルタリング前: {len(all_headings_before_filter)}件")
        # log_collector.add_log(f"{url_log_prefix}   - 除外された見出し: {len(excluded_headings)}件")
        
        # 除外された見出しの詳細をログに出力（URL毎にまとめて出力）
        
        # 全文を取得して整形
        text = soup.get_text(separator='\n', strip=True)
        # 複数の改行を1つに統一
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # 先頭と末尾の空白を削除
        text = text.strip()
        
        # コンテンツ保護サイトのチェック
        if 'Content is protected' in text or 'content is protected' in text.lower():
            # 保護されたコンテンツの場合、タイトルから基本的な情報を抽出
            title = soup.find('title').get_text() if soup.find('title') else ''
            return {
                'url': url,
                'title': title,
                'main_content': f'コンテンツが保護されています。タイトル: {title}',
                'headings': [f'<h1>{title}</h1>'] if title else []
            }
        
        return {
            'url': url,
            'title': soup.find('title').get_text() if soup.find('title') else '',
            'main_content': text[:2000] + '...' if len(text) > 2000 else text,  # 2000文字で制限
            'headings': headings  # H1〜H6の見出し（HTMLタグ付き）
        }
            
    except Exception as e:
        return {
            'url': url,
            'title': '',
            'main_content': f'エラー: {str(e)}',
            'headings': []
        }

def process_article_group(group_data):
    """
    記事グループを並列処理する関数
    
    Args:
        group_data: 辞書形式で以下のキーを含む
            - group_index: グループのインデックス
            - group: グループデータ
            - keyword: キーワード
            - html_writing_rule: HTML記述ルール
            - full_article_structure: 記事全体の構成案
            - full_title: 記事全体のタイトル
    
    Returns:
        dict: 処理結果を含む辞書
    """
    group_index = group_data['group_index']
    group = group_data['group']
    keyword = group_data['keyword']
    html_writing_rule = group_data['html_writing_rule']
    full_article_structure = group_data['full_article_structure']
    full_title = group_data['full_title']
    
    st.write(f"  グループ {group_index} 処理開始")
    
    try:
        # 構成案を元の順番通りにまとめる
        full_structure = '\n'.join(group['ordered_headings'])
        
        # 記事本文生成
        prompt = f"""
        あなたは優秀な介護関するSEO記事執筆者です。

       【キーワード】と記事全体の構成案を参考にしつつ、構成案の1セクションのみを執筆してください。
        セクション毎に分けて執筆しており、記事全体の他のセクションの内容に関して執筆すると重複してしまう為構成案以外の内容は一切書かないでください。

        キーワード: {keyword}

        構成案: {full_structure} 

        記事全体の構成案:
        {full_article_structure}

        HTMLの記述方式:
        {html_writing_rule}

        注意点:
        - 【構成案】は、見出しの一覧です。H2~H4までの見出し自体には一切変更せずに見出しにあった内容の本文を執筆してください。H5以下の見出しがある場合はH4の本文として扱ってください。
        - 【構成案】は、記事全体の見出しの一つのH2見出しのグループです。H2見出しのグループごとに分けて執筆しています。他のH2見出しの執筆と内容が重複してしまう可能性があるので執筆するセクションの【構成案】にない内容は以外は一切書かないでください。
        - SEO最適化を意識し、自然な形でキーワードを含めてください。
        - 読者にとって価値のある情報を提供してください。
        - 内容が網羅的にリッチになるように執筆してください。
        - 各章は箇条書きだけではなく、読みやすい導入文をつけた上で、起承転結か列挙の形式で書く様にしてください。
        - 執筆するのは記事の一部のみのため、<body>タグや<html>タグは不要です。余分な説明も不要です。
        - 会社名などの固有名詞を使うときは嘘ではない情報を必ず使ってください。
        - サービス価格など、事実確認が必要と思われる情報は伏せた文章にしてください。
        - 本文以外の内容は一切出力しないでください。
        """
        
        response = ai_client.messages.create(
            model=MODEL,
            max_tokens=10000,
            messages=[{"role": "user", "content": prompt}],
        )
        article_content = response.content[0].text
        
        final_article_content = article_content
        
        return {
            'group_index': group_index,
            'article_content': final_article_content,
            'success': True
        }
        
    except Exception as e:
        st.write(f"    ❌ グループ {group_index} の処理でエラーが発生しました: {str(e)}")
        return {
            'group_index': group_index,
            'article_content': f"<h2>エラーが発生しました</h2><p>グループ {group_index} の処理中にエラーが発生しました。</p>",
            'success': False
        }

def save_to_drive(content: str, filename: str, folder_name: str) -> str:
    """
    Google Driveにファイルを保存する関数

    Args:
        content: 保存するコンテンツ
        filename: ファイル名
        folder_name: 保存先フォルダ名

    Returns:
        str: 保存したファイルのURL
    """
    try:
        # OAuth2.0認証でDrive APIのサービスを構築
        service = authenticate_oauth()
        
        if service is None:
            st.write("❌ Google Drive認証に失敗しました")
            return None

        # テーマに基づいたフォルダを検索または作成
        folder_query = f"name = '{folder_name}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        folder_results = (
            service.files()
            .list(q=folder_query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        folder_items = folder_results.get("files", [])

        if not folder_items:
            # フォルダが存在しない場合は新規作成
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [PARENT_FOLDER_ID],
            }
            folder = service.files().create(body=folder_metadata, fields="id").execute()
            folder_id = folder.get("id")
        else:
            folder_id = folder_items[0]["id"]

        # ファイルのメタデータを設定
        file_metadata = {"name": filename, "parents": [folder_id]}

        # 文字列をバイトに変換し、BytesIOオブジェクトを作成
        content_bytes = content.encode("utf-8")
        file_content = BytesIO(content_bytes)

        # MediaIoBaseUploadでファイルをアップロード
        media = MediaIoBaseUpload(
            file_content, mimetype="text/plain", chunksize=1024 * 1024, resumable=True
        )

        # ファイルをアップロード
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )

        return file.get("webViewLink")

    except Exception as e:
        st.write(f"ファイルの保存中にエラーが発生しました: {str(e)}")
        return None

def main():
    
    number_input = st.number_input("執筆する記事の件数を入れてください", value=1, min_value=1, max_value=100)
    if st.button("処理開始"):

        try:
            sp_client = get_gspread_client()
            if sp_client is None:
                st.write("❌ Google Spreadsheet接続に失敗しました")
                return
            
            workbook = sp_client.open_by_url(
                "https://docs.google.com/spreadsheets/d/12Qm5JuRnR32kS3barxSVC1DKKdZBOv5IW5nyajB7_ZA/edit?gid=0#gid=0"
            )
            theme = "執筆"
            
            # 選択されたシートのデータを取得
            selected_sheet = workbook.worksheet(theme)
            sheet_data = selected_sheet.get_all_values()
            headers = sheet_data[0]
        except Exception as e:
            st.write(f"❌ スプレッドシート処理でエラーが発生しました: {str(e)}")
            return
        
        # ヘッダーから列のインデックスを取得
        url_col_index = None
        search_count_col_index = None
        slug_col_index = None
        priority_col_index = None
        
        for i, header in enumerate(headers):
            if header == "投稿後URL":
                url_col_index = i
            elif header == "検索数":
                search_count_col_index = i
            elif header == "slug":
                slug_col_index = i
            elif header == "優先":
                priority_col_index = i
        
        if url_col_index is None or search_count_col_index is None:
            st.write("❌ 必要な列（投稿後URLまたは検索数）が見つかりません")
            return
        

        # slug列の値を取得（空白を除く）
        existing_slugs = []
        if slug_col_index is not None:
            for row in sheet_data[1:]:  # ヘッダーを除いて処理
                if len(row) > slug_col_index and row[slug_col_index].strip():
                    existing_slugs.append(row[slug_col_index].strip())
        
        # 投稿後URLが空欄の行を抽出（優先フラグ付きとそうでないものを分ける）
        priority_rows = []
        normal_rows = []
        
        
        for i, row in enumerate(sheet_data[1:], 1):  # ヘッダーを除いて処理
            if i < len(sheet_data) and len(row) > max(url_col_index, search_count_col_index):
                if not row[url_col_index] or row[url_col_index].strip() == "":
                    try:
                        # 検索数のカンマを除去して数値に変換
                        search_count_str = row[search_count_col_index].replace(",", "")
                        search_count = int(search_count_str) if search_count_str.strip() else 0
                        
                        # 優先フラグがあるかチェック
                        has_priority = False
                        if priority_col_index is not None and len(row) > priority_col_index:
                            has_priority = bool(row[priority_col_index] and row[priority_col_index].strip())
                        
                        if has_priority:
                            priority_rows.append((i, row, search_count))
                        else:
                            normal_rows.append((i, row, search_count))
                            
                    except (ValueError, IndexError):
                        # 数値変換できない場合は0として扱う
                        has_priority = False
                        if priority_col_index is not None and len(row) > priority_col_index:
                            has_priority = bool(row[priority_col_index] and row[priority_col_index].strip())
                        
                        if has_priority:
                            priority_rows.append((i, row, 0))
                        else:
                            normal_rows.append((i, row, 0))
        
        # 優先フラグ付きの行を検索数で降順ソート
        priority_rows.sort(key=lambda x: x[2], reverse=True)
        
        # 通常の行を検索数で降順ソート
        normal_rows.sort(key=lambda x: x[2], reverse=True)
        
        # 優先フラグ付きの行を先に、その後通常の行を追加
        empty_url_rows = priority_rows + normal_rows
        
        # 指定された件数分取得
        selected_rows = empty_url_rows[:number_input]
        
        # 結果を表示
        if selected_rows:
            
            # ヘッダーから必要な列のインデックスを取得
            id_col_index = None
            kw_col_index = None
            
            for i, header in enumerate(headers):
                if header == "ID":
                    id_col_index = i
                elif header == "結合":
                    kw_col_index = i
            
                        # URL処理を並列化する関数（forループの外に移動）
                def process_url(url_data):
                    url_index, url = url_data
                    url_log_prefix = f"[URL{url_index}]"
                    
                    try:
                        content_data = extract_main_content(url, url_index)
                        
                        # ページタイトルと見出しを一つの変数にまとめる（見出しがある場合のみ）
                        if content_data['headings']:
                            page_info = {
                                'title': content_data['title'],
                                'headings': content_data['headings'],
                                'url_index': url_index,
                                'url': url
                            }
                            return page_info
                        else:
                            return None
                    except Exception as e:
                        st.write(f"{url_log_prefix} ❌ コンテンツ抽出エラー: {str(e)}")
                        return None

            for i, (row_num, row, search_count) in enumerate(selected_rows):
                time.sleep(10)
                # ID列の値を取得
                keyword_id = row[id_col_index] if id_col_index is not None and id_col_index < len(row) else "N/A"
                
                # 結合列の値を取得
                keyword = row[kw_col_index] if kw_col_index is not None and kw_col_index < len(row) else "N/A"
                
                st.write(f"=== キーワード: {keyword} (行番号: {row_num}) ===")

                # Google検索を実行
                try:
                    search_results = search_google(keyword, 10)
                except Exception as e:
                    st.write(f"❌ Google検索でエラーが発生しました: {str(e)}")
                    search_results = []
                
                # 検索結果のURLをリスト化
                search_urls = [result['url'] for result in search_results]
                
                # ページタイトルと見出しをまとめる変数
                all_titles_and_headings = []


                # 並列処理の実行
                url_tasks = [(i, url) for i, url in enumerate(search_urls, 1)]
                max_workers = min(10, len(search_urls))  # 最大10件の並列処理
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 各URLを並列実行
                    future_to_url = {
                        executor.submit(process_url, url_data): url_data[0]
                        for url_data in url_tasks
                    }
                    
                    # 結果を順序通りに収集するための辞書
                    results = {}
                    
                    # 完了したタスクから結果を収集
                    for future in as_completed(future_to_url):
                        url_index = future_to_url[future]
                        try:
                            result = future.result()
                            if result:
                                results[url_index] = result
                        except Exception as e:
                            st.write(f"❌ URL {url_index} の並列処理でエラーが発生しました: {str(e)}")
                    
                    # 順序通りに結果をall_titles_and_headingsに追加し、まとめてログ出力
                    for i in range(1, len(search_urls) + 1):
                        if i in results:
                            result = results[i]
                            all_titles_and_headings.append(result)
                            
                            # URL毎にまとめてログ出力
                            url_log_prefix = f"[URL{i}]"
                            st.write(f"{url_log_prefix} ✅ 見出し抽出完了 ✅ ({len(result['headings'])}件)")
                            
                            # 抽出された見出しの詳細をログに出力
                            for j, heading in enumerate(result['headings'], 1):
                                st.write(f"{heading}")
                        else:
                            url_log_prefix = f"[URL{i}]"

                prompt = f"""
                あなたは優秀な介護に関するSEO記事執筆者です。
                【上位記事構成】は【キーワード】で検索した結果の上位サイトの見出しです。
                介護に関する上位サイトの見出しが網羅的された見出し構成案を【要件】に従って作成してください。

                【上位記事構成】
                {all_titles_and_headings}

                【キーワード】
                {keyword}

                【要件】
                - 【上位記事構成】は機械的にキーワードで検索した結果の上位サイトの見出しの為、介護に関係の無い記事の見出しが混入している可能性があります。その場合はその見出しは構成案に入れないでください。
                - 【上位記事構成】の介護に関する見出しは削らないで網羅的にする。
                - 意味合いとして重複する見出しは統合する。
                - 全ての見出しは独自の言い回しになるように書き換えてください。
                - 多言語の可能性があるが全て日本語に統一してください。
                - H3、H4はそれぞれ上位の見出しに紐付く為、上位の見出しは変わらないようにする。
                - H3とH4も意味合いとして重複する見出しは統合する。
                - 事例紹介で個人名やキーワードと無関係の社名が入っている場合は、その名前は必ず削除してください。
                - 構成案以外の出力は絶対にしない。
                - 上位記事構成が少ない場合に限り、キーワードから読者が知りたいと思うH2やH3の見出しを追加してください。
                - 機械的にHタグを取ってきているので【キーワード】に関係の無い見出しが混入してしまっている可能性があります。その場合はその見出しは出力に入れないでください。

                【出力形式】
                - 見出し構成案を出力例のように出力してください。
                - 見出しレベルは、h2, h3, h4のいずれかのみです。
                - 見出し構成案は、見出しレベルと見出しテキストのリストです。
                
                【出力例】
                H2 H2見出し1
                H3 H3見出し1
                H4 H4見出し1
                H4 H4見出し2
                H4 H4見出し3
                H3 H3見出し2
                H3 H3見出し3

                H2 H2見出し2
                H3 H3見出し3
                H4 H4見出し3
                """
                try:
                    response = ai_client.messages.create(
                        model=MODEL,
                        max_tokens=4000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    article_structure = response.content[0].text
                except Exception as e:
                    st.write(f"❌ 記事構成案作成でエラーが発生しました: {str(e)}")
                    continue

                this_year = datetime.now().year
                title_prompt = f"""
                以下の記事構成案に基づいて、SEOに最適化されたキーワードが必ず入った記事タイトルを生成してください。
                

                記事構成案:
                {article_structure}

                キーワード:
                {keyword}

                要件:
                - タイトルは25~33文字以内
                - 必ずキーワードの単語はタイトルに含める
                - キーワードの単語はできるだけ冒頭付近に自然な形で含める
                - 読者の興味を引く魅力的な表現を使用
                - 記事の価値提案が明確に伝わるようにする
                - 個人名や会社名が入っている場合、その者が関わっているかのような書き方は絶対にしない
                - タイトルに今年の年を含めたい場合は{this_year}が今年の年なので間違えないようにしてください。（必ずしも年を含める必要はない）
                タイトルのみを出力してください。説明は不要です
                """
                try:
                    response = ai_client.messages.create(
                        model=MODEL,
                        max_tokens=100,
                        messages=[{"role": "user", "content": title_prompt}]
                    )
                    title = response.content[0].text
                except Exception as e:
                    st.write(f"❌ 記事タイトル生成でエラーが発生しました: {str(e)}")
                    continue


                description_prompt = f"""
                    以下の記事全文を元にこの記事を読んだらどういった情報が得られるのか、どんな悩みが解決できるのかを要約して、記事の冒頭で記事全体を紹介する150文字程度のサマリーを生成してください。

                    記事見出し構成:
                    {all_titles_and_headings}

                    要件:
                    - 記事の主要なポイントを簡潔に説明
                    - 読者が得られる価値を明確に示す
                    - 具体的な事実等を含める
                    - 自然な日本語で読みやすく
                    サマリーのみを出力してください。説明は不要です
                    """
                try:
                    description_response = ai_client.messages.create(
                        model=MODEL,
                        max_tokens=1000,
                        messages=[{"role": "user", "content": description_prompt}],
                    )
                    description = description_response.content[0].text
                except Exception as e:
                    st.write(f"❌ 記事サマリー生成でエラーが発生しました: {str(e)}")
                    continue

                    
                # グループ分けを実行
                grouped_headings = group_headings_by_h2(article_structure)
                
                # 並列処理のためのデータ準備
                group_tasks = []
                
                for i, group in enumerate(grouped_headings, 1):
                    group_data = {
                        'group_index': i,
                        'group': group,
                        'keyword': keyword,
                        'html_writing_rule': html_writing_rule,
                        'full_article_structure': article_structure,
                        'full_title': title
                    }
                    group_tasks.append(group_data)
                
                # 並列処理の実行
                article_contents = []
                results = {}
                
                # 最大スレッド数を制限（API制限を考慮）
                max_workers = min(10, len(grouped_headings))
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 各タスクを並列実行
                    future_to_group = {
                        executor.submit(process_article_group, group_data): group_data['group_index']
                        for group_data in group_tasks
                    }
                    
                    # 完了したタスクから結果を収集（順序を保持）
                    for future in as_completed(future_to_group):
                        group_index = future_to_group[future]
                        try:
                            result = future.result()
                            results[group_index] = result
                        except Exception as e:
                            st.write(f"❌ グループ {group_index} の並列処理でエラーが発生しました: {str(e)}")
                            results[group_index] = {
                                'group_index': group_index,
                                'article_content': f"<h2>エラーが発生しました</h2><p>グループ {group_index} の処理中にエラーが発生しました。</p>",
                                'success': False
                            }
                
                # 結果を順序通りに並べ替え
                for i in range(1, len(grouped_headings) + 1):
                    if i in results:
                        article_contents.append(results[i]['article_content'])
                    else:
                        article_contents.append(f"<h2>エラーが発生しました</h2><p>グループ {i} の処理結果が見つかりませんでした。</p>")
                

                # 項目別の値を表示
                # 記事本文のリストを文字列に変換
                article_contents_str = "\n\n".join(article_contents) if article_contents else "記事本文なし"
                
                # 冒頭にdescriptionを追加
                article_contents_str = f"{description}\n\n{article_contents_str}"
                
                # ファイル名をキーワードで生成
                filename = keyword
                
                debug_info = {
                    "ID": str(keyword_id),
                    "KW": str(keyword),
                    "記事タイトル": str(title),
                    "記事本文": article_contents_str,
                    "ファイル名": str(filename),
                    "ドキュメントURL": "今後作成"
                }
                
                try:
                    # ファイル名に.txt拡張子を追加
                    drive_filename = f"{filename}.txt"
                    
                    # 保存するコンテンツを作成（タイトルと本文を含む）
                    save_content = f"タイトル: {title}\n\n{article_contents_str}"
                    
                    # Google Driveに保存
                    drive_url = save_to_drive(save_content, drive_filename, "AI・DX")
                    
                    if drive_url:
                        pass
                    else:
                        st.write("❌ Google Driveへの保存に失敗しました")
                        drive_url = "保存失敗"
                except Exception as e:
                    st.write(f"❌ Google Drive保存中にエラーが発生しました: {str(e)}")
                    drive_url = "保存エラー"

                debug_info = {
                    "ID": str(keyword_id),
                    "KW": str(keyword),
                    "記事タイトル": str(title),
                    "記事本文": article_contents_str,
                    "ファイル名": str(filename),
                    "ドキュメントURL": drive_url
                }


                # 記事作成完了のログ出力
                st.write(f"✅ 記事作成完了 - ID: {debug_info['ID']}")

                try:
                    # 対象行を検索（ID列とdebug_infoのIDが一致する行）
                    all_values = selected_sheet.get_all_values()
                    target_row_number = None
                    
                    for i, row in enumerate(all_values[1:], start=2):  # ヘッダーを除いて処理
                        if row[0] == debug_info["ID"]:  # ID列と一致
                            target_row_number = i
                            break
                    
                    if target_row_number:
                        # ヘッダー行から列のインデックスを取得
                        headers = all_values[0]
                        
                        # 各列のインデックスを取得
                        writing_content_col = None
                        posting_date_col = None
                        title_col = None
                        engine_col = None
                        
                        for i, header in enumerate(headers):
                            if header == "執筆本文":
                                writing_content_col = i
                            elif header == "記事作成日":
                                posting_date_col = i
                            elif header == "タイトル":
                                title_col = i
                            elif header == "エンジン":
                                engine_col = i
                        
                        # 本日の日付を取得
                        today = datetime.now().strftime("%Y/%m/%d")
                        
                        # 更新するデータを準備
                        updates = []
                        
                        if writing_content_col is not None:
                            updates.append({
                                "range": f"{chr(65 + writing_content_col)}{target_row_number}",
                                "values": [[debug_info["ドキュメントURL"]]]
                            })
                        
                        if posting_date_col is not None:
                            updates.append({
                                "range": f"{chr(65 + posting_date_col)}{target_row_number}",
                                "values": [[today]]
                            })
                        
                        if title_col is not None:
                            updates.append({
                                "range": f"{chr(65 + title_col)}{target_row_number}",
                                "values": [[debug_info["記事タイトル"]]]
                            })
                        
                        if engine_col is not None:
                            updates.append({
                                "range": f"{chr(65 + engine_col)}{target_row_number}",
                                "values": [["claude"]]
                            })
                        
                        # バッチ更新を実行
                        if updates:
                            selected_sheet.batch_update(updates)
                        else:
                            st.write("⚠️ 更新対象の列が見つかりませんでした")
                    else:
                        st.write(f"❌ ID {debug_info['ID']} に対応する行が見つかりませんでした")
                        
                except Exception as e:
                    st.write(f"❌ スプレッドシートの更新中にエラーが発生しました: {str(e)}")
                
                # 各記事処理完了
                st.write(f"=== キーワード: {keyword} 処理完了 ===")
            
            st.write("=== 全キーワード処理完了 ===")
                
        else:
            st.write("❌ 条件に合う行が見つかりませんでした")
    

if __name__ == "__main__":
    main()