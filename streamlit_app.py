import os, json, re, time, sys, subprocess, shutil, platform
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import requests
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "ui_config.json"
ASSETS_DIR = BASE_DIR / "ui_assets"
SCREENSHOT_DIR = BASE_DIR / "submission_assets" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "app_name": "Disaster Tweet Intelligence",
    "api_url": "http://127.0.0.1:5000",
    "max_characters": 1000,
    "probability_caution_level": 0.65,
    "model_name": "Locked Production Model",
    "model_version": "unknown",
    "feature_id": "Final locked feature set",
    "evaluation_dataset": "Protected test set",
    "disclaimer": "This classifier is an analytical decision-support tool and is not an official emergency authority.",
    "performance": {},
    "confusion_matrix": {}
}

if CONFIG_PATH.exists():
    try:
        loaded_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        CONFIG = {**DEFAULT_CONFIG, **loaded_config}
    except Exception as exc:
        CONFIG = DEFAULT_CONFIG.copy()
        CONFIG["config_warning"] = f"ui_config.json could not be read: {exc}"
else:
    CONFIG = DEFAULT_CONFIG.copy()
    CONFIG["config_warning"] = "ui_config.json was not found; safe built-in defaults are being used."

API_URL = os.getenv("DISASTER_API_URL", CONFIG.get("api_url", "http://127.0.0.1:5000")).rstrip("/")
MAX_CHARS = int(CONFIG.get("max_characters", 1000))
CAUTION = float(CONFIG.get("probability_caution_level", 0.65))
CAPTURE_MODE = str(st.query_params.get("capture_mode", "0")) == "1"

st.set_page_config(
    page_title=CONFIG.get("app_name", "Disaster Tweet Intelligence"),
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
<style>
:root{
    --plum:#563247;
    --plum-dark:#3D2030;
    --plum-mid:#75465B;
    --gold:#D1A978;
    --border:#E5D8DE;
    --muted:#786A71;
    --soft:#FAF7F8;
    --success:#52705D;
    --danger:#9B4D46;
}
.block-container{max-width:1280px;padding-top:1.65rem;padding-bottom:3rem}
.hero{padding:28px 30px;border-radius:16px;background:linear-gradient(135deg,var(--plum-dark),#593148,var(--plum-mid));border-bottom:4px solid var(--gold);margin-bottom:18px}
.hero h1{font-family:Georgia,serif;color:white;font-weight:500;margin:4px 0 8px;font-size:2.15rem}
.hero p{color:#EBDDE4;margin:0;line-height:1.7;max-width:950px}
.hero-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.hero-pill{padding:6px 10px;border:1px solid rgba(255,255,255,.17);border-radius:999px;color:#F7EDF2;background:rgba(255,255,255,.06);font-size:11px}
.section{font-family:Georgia,serif;color:#4B2638;font-size:24px;margin:10px 0 5px}
.subsection{font-family:Georgia,serif;color:#4B2638;font-size:18px;margin:10px 0 5px}
.result{padding:22px;border:1px solid var(--border);border-radius:12px;margin-top:14px}
.disaster{background:#FFF2EF;border-left:5px solid var(--danger)}
.safe{background:#F1F7F3;border-left:5px solid var(--success)}
.counter{text-align:right;color:#817078;font-size:12px}
.warn{color:#A04E48;font-weight:700}
.info{padding:12px 14px;background:var(--soft);border-left:4px solid var(--gold);border-radius:5px;line-height:1.65}
.mini-card{padding:14px 15px;border:1px solid var(--border);border-radius:10px;background:#FCFAFB;min-height:100%}
.mini-card .kicker{font-size:10px;font-weight:700;letter-spacing:1px;color:#A36F83;text-transform:uppercase}
.mini-card .value{font:500 21px Georgia;color:#4B2638;margin:4px 0}
.mini-card .copy{font-size:12px;line-height:1.6;color:#6F6268}
.risk-card{padding:15px;border:1px solid var(--border);border-radius:10px;background:#FCFAFB;height:100%}
.risk-card b{font-family:Georgia,serif;color:#4B2638;font-size:16px;font-weight:500}
.risk-card p{font-size:12px;line-height:1.65;color:#6F6268;margin:.35rem 0 0}
.arch-flow{padding:16px;border:1px solid var(--border);border-radius:10px;background:linear-gradient(135deg,#FCFAFB,#F7F1F4);text-align:center;color:#4B2638;font-weight:650;letter-spacing:.2px}
.arch-flow span{color:#A36F83;font-weight:700;margin:0 10px}
[data-testid="stSidebar"]{background:#FAF7F8;border-right:1px solid #EEE4E8}
div[data-testid="stButton"] button:focus,div[data-testid="stTextArea"] textarea:focus,div[data-testid="stTextInput"] input:focus{outline:3px solid var(--gold)!important;outline-offset:2px!important}
div[data-testid="stMetric"]{background:#FCFAFB;border:1px solid var(--border);padding:10px 12px;border-radius:10px}
[data-baseweb="tab-list"]{gap:4px;flex-wrap:wrap}
[data-baseweb="tab"]{height:42px;border-radius:8px 8px 0 0;padding-left:14px;padding-right:14px;transition:all .18s ease}
[data-baseweb="tab"]:hover{background:#F4ECEF}
[data-baseweb="tab"][aria-selected="true"]{background:#F1E6EB;border-bottom:2px solid var(--plum)}
.hero-grid{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.8fr);gap:24px;align-items:center}
.hero-art{min-height:210px;border:1px solid rgba(255,255,255,.16);border-radius:14px;background:rgba(255,255,255,.055);display:flex;align-items:center;justify-content:center;padding:8px;overflow:hidden}
.hero-art svg{width:100%;height:auto;max-height:220px}
.visual-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:4px 0 20px}
.visual-card{border:1px solid var(--border);border-radius:13px;background:linear-gradient(180deg,#FFFFFF,#FBF8F9);overflow:hidden;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}
.visual-card:hover{transform:translateY(-2px);border-color:#D6C2CB;box-shadow:0 8px 24px rgba(74,38,56,.08)}
.visual-card-art{height:132px;background:linear-gradient(135deg,#F5EDF1,#FBF8F9);display:flex;align-items:center;justify-content:center;padding:8px;border-bottom:1px solid #EEE4E8}
.visual-card-art svg{width:100%;height:116px}
.visual-card-copy{padding:13px 14px 15px}
.visual-card-copy .eyebrow{font-size:9px;font-weight:700;letter-spacing:1.2px;color:#A36F83;text-transform:uppercase}
.visual-card-copy .title{font:500 17px Georgia;color:#4B2638;margin:3px 0 5px}
.visual-card-copy p{margin:0;color:#6F6268;font-size:11.5px;line-height:1.6}
.tour-box{display:grid;grid-template-columns:42px 1fr;gap:12px;align-items:start;padding:13px 15px;border:1px solid var(--border);border-left:4px solid var(--gold);border-radius:9px;background:#FCFAFB;margin-bottom:16px}
.tour-number{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#F0E5E9;color:#563247;font:600 13px Georgia}
.tour-box b{display:block;color:#4B2638;font-family:Georgia,serif;font-weight:500;margin-bottom:3px}
.tour-box p{margin:0;color:#6F6268;font-size:12px;line-height:1.6}
.scenario-art{height:116px;border:1px solid var(--border);border-radius:11px 11px 0 0;background:linear-gradient(135deg,#FBF6F8,#F3E9EE);display:flex;align-items:center;justify-content:center;overflow:hidden}
.scenario-art svg{width:100%;height:110px}
.scenario-label{border:1px solid var(--border);border-top:0;border-radius:0 0 11px 11px;padding:10px 12px;background:#fff;margin-bottom:7px}
.scenario-label b{font-family:Georgia,serif;color:#4B2638;font-size:14px;font-weight:500}
.scenario-label div{color:#7A6B72;font-size:10.5px;margin-top:2px;line-height:1.45}
.status-panel{padding:12px 13px;border:1px solid var(--border);border-radius:10px;background:#fff;margin-bottom:8px}
.status-line{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;color:#4B2638}
.status-dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.status-dot.online{background:#52705D;box-shadow:0 0 0 4px #E7F0EB}
.status-dot.offline{background:#A06A4A;box-shadow:0 0 0 4px #F8EDE6}
.status-detail{font-size:10.5px;color:#817078;margin-top:7px;line-height:1.45}
.result-visual{border:1px solid var(--border);border-radius:12px;background:linear-gradient(135deg,#FCFAFB,#F6EEF2);padding:8px;height:100%;display:flex;align-items:center;justify-content:center}
.result-visual svg{width:100%;max-height:220px}
.profile{padding:14px;border:1px solid var(--border);border-radius:10px;background:#FCFAFB}
.profile-row{display:grid;grid-template-columns:120px 1fr 38px;gap:10px;align-items:center;margin:9px 0}
.profile-label{font-size:11px;color:#61545A}
.profile-track{height:8px;border-radius:999px;background:#EEE4E8;overflow:hidden}
.profile-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#75465B,#D1A978)}
.profile-value{font-size:10px;color:#8D7681;text-align:right}
.feature-story{display:grid;grid-template-columns:220px 1fr;gap:16px;align-items:center;padding:15px;border:1px solid var(--border);border-radius:12px;background:#FCFAFB;margin:12px 0}
.feature-story svg{width:100%;max-height:160px}
.feature-story h4{font-family:Georgia,serif;color:#4B2638;font-size:19px;font-weight:500;margin:0 0 6px}
.feature-story p{font-size:12px;line-height:1.65;color:#6F6268;margin:0}

.command-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:0 0 18px}
.command-card{position:relative;padding:14px 15px;border:1px solid var(--border);border-radius:12px;background:linear-gradient(180deg,#FFFFFF,#FBF8F9);overflow:hidden;min-height:104px}
.command-card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,#75465B,#D1A978)}
.command-card .label{font-size:9px;letter-spacing:1.1px;text-transform:uppercase;color:#967B88;font-weight:700}
.command-card .big{font:500 21px Georgia;color:#4B2638;margin:7px 0 3px}
.command-card .small{font-size:10.5px;color:#817078;line-height:1.45}
.step-flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:8px 0 18px}
.step-card{position:relative;padding:15px;border:1px solid var(--border);border-radius:12px;background:#FCFAFB}
.step-card .num{display:inline-flex;width:28px;height:28px;align-items:center;justify-content:center;border-radius:50%;background:#F0E5E9;color:#563247;font:600 12px Georgia;margin-bottom:8px}
.step-card b{display:block;font-family:Georgia,serif;color:#4B2638;font-weight:500;font-size:15px}
.step-card p{margin:5px 0 0;color:#75666D;font-size:11px;line-height:1.55}
.signal-lens{padding:15px;border:1px solid var(--border);border-radius:12px;background:linear-gradient(135deg,#FCFAFB,#F7F1F4);margin:10px 0 4px}
.signal-lens .lens-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.signal-lens .lens-title{font:500 17px Georgia;color:#4B2638}
.signal-lens .lens-note{font-size:9.5px;color:#8A7780}
.signal-group{margin:9px 0}
.signal-group b{display:block;font-size:10px;color:#715E67;margin-bottom:6px}
.signal-tags{display:flex;flex-wrap:wrap;gap:6px}
.signal-tag{padding:5px 8px;border-radius:999px;background:#F0E5EA;border:1px solid #E1D0D8;color:#674553;font-size:9px;font-weight:650}
.signal-tag.muted{background:#F6F3F4;color:#8D7C84;border-color:#E9E1E4;font-weight:500}
.metric-bars{display:grid;gap:10px;margin:12px 0 18px}
.metric-row{display:grid;grid-template-columns:110px 1fr 62px;gap:10px;align-items:center}
.metric-name{font-size:10.5px;color:#66565E;font-weight:650}
.metric-track{height:9px;background:#EEE5E9;border-radius:999px;overflow:hidden}
.metric-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#75465B,#D1A978)}
.metric-val{text-align:right;font-size:10px;color:#7B6871;font-weight:700}
.matrix-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0 15px}
.matrix-cell{padding:14px;border:1px solid var(--border);border-radius:10px;background:#FCFAFB}
.matrix-cell.good{background:#F2F7F3;border-color:#D8E5DC}.matrix-cell.bad{background:#FFF4F0;border-color:#EAD8D1}
.matrix-cell .m-label{font-size:9px;color:#8B747E;text-transform:uppercase;letter-spacing:.8px;font-weight:700}
.matrix-cell .m-value{font:600 23px Georgia;color:#4B2638;margin:4px 0}
.matrix-cell .m-copy{font-size:10px;color:#7A6971;line-height:1.45}
.arch-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0}
.arch-card{padding:14px;border:1px solid var(--border);border-radius:11px;background:#FCFAFB;text-align:center}
.arch-card .a-icon{font-size:22px;margin-bottom:5px}.arch-card b{display:block;font-family:Georgia,serif;color:#4B2638;font-weight:500}.arch-card p{margin:4px 0 0;color:#7A6B72;font-size:9.5px;line-height:1.45}
.action-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:12px 0}
.action-card{padding:12px;border:1px solid var(--border);border-radius:10px;background:#FCFAFB}.action-card b{display:block;font-size:11px;color:#4B2638}.action-card span{display:block;margin-top:4px;font-size:9.5px;line-height:1.45;color:#7C6B73}
.premium-footer{margin-top:28px;padding:18px 20px;border-radius:12px;background:linear-gradient(135deg,#3D2030,#593148);color:#F6ECF0;display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap;border-bottom:3px solid #D1A978}
.premium-footer b{font-family:Georgia,serif;font-weight:500}.premium-footer span{font-size:10px;color:#DCCBD3}
@media(max-width:900px){.block-container{padding-left:1rem;padding-right:1rem}.hero h1{font-size:1.8rem}.hero-grid{grid-template-columns:1fr}.hero-art{min-height:160px}.visual-strip,.command-grid,.step-flow,.arch-grid,.action-strip{grid-template-columns:1fr 1fr}.feature-story{grid-template-columns:1fr}.profile-row{grid-template-columns:100px 1fr 34px}}
@media(max-width:560px){.visual-strip,.command-grid,.step-flow,.arch-grid,.action-strip{grid-template-columns:1fr}.metric-row{grid-template-columns:90px 1fr 50px}.matrix-grid{grid-template-columns:1fr}}

</style>
""",
    unsafe_allow_html=True
)


@st.cache_data(ttl=15, show_spinner=False)
def health():
    try:
        t = time.perf_counter()
        response = requests.get(f"{API_URL}/health", timeout=4)
        latency = (time.perf_counter() - t) * 1000
        payload = response.json() if response.ok else {}
        return response.ok, latency, payload
    except Exception:
        return False, None, {}


def predict(text):
    t = time.perf_counter()
    response = requests.post(f"{API_URL}/predict", json={"text": text}, timeout=15)
    latency = (time.perf_counter() - t) * 1000
    try:
        data = response.json()
    except Exception:
        data = {}
    if response.status_code != 200:
        raise RuntimeError(data.get("message", f"Prediction failed with HTTP {response.status_code}"))
    return data, latency


def reset_analysis():
    st.session_state.tweet_input = ""
    st.session_state.last_result = None
    st.session_state.last_error = None
    st.session_state.last_latency = None


def text_diagnostics(text):
    return {
        "Characters": len(text),
        "Words": len(re.findall(r"\b\w+\b", text)),
        "Hashtags": len(re.findall(r"#\w+", text)),
        "Mentions": len(re.findall(r"@\w+", text)),
        "URLs": len(re.findall(r"https?://\S+|www\.\S+", text)),
        "Exclamations": text.count("!"),
        "Questions": text.count("?"),
        "Uppercase tokens": len(re.findall(r"\b[A-Z]{2,}\b", text))
    }


def result_label(result):
    pred = int(result.get("prediction", 0))
    return pred, "Real Disaster" if pred == 1 else "Not a Disaster"


def probability_value(result):
    score = result.get("score")
    score_type = str(result.get("score_type", "Class Only"))
    if score is None:
        return None, score_type
    if score_type.lower().startswith("prob"):
        try:
            return float(score), score_type
        except Exception:
            return None, score_type
    return None, score_type


def history_entry(text, result, latency, source="Single Analysis"):
    pred, label = result_label(result)
    return {
        "Timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y · %H:%M:%S"),
        "Source": source,
        "Tweet": text,
        "Prediction": label,
        "Prediction Code": pred,
        "Score": result.get("score"),
        "Score Type": result.get("score_type", "Class Only"),
        "Latency ms": round(float(latency), 2),
        "Model Version": result.get("model_version", CONFIG.get("model_version", "unknown"))
    }


def variation_set(text):
    variants = {
        "Original": text,
        "Lowercase": text.lower(),
        "Remove URLs": re.sub(r"https?://\S+|www\.\S+", " ", text),
        "Remove mentions": re.sub(r"@\w+", " ", text),
        "Normalize hashtags": re.sub(r"#(\w+)", r"\1", text),
        "Reduce punctuation": re.sub(r"[^\w\s#@']", " ", text)
    }
    cleaned = {}
    for name, value in variants.items():
        value = re.sub(r"\s+", " ", value).strip()
        if value and value not in cleaned.values():
            cleaned[name] = value
    return cleaned


def visual_svg(kind):
    visuals = {
        "hero": """
<svg viewBox="0 0 420 230" role="img" aria-label="Illustration of social media disaster intelligence">
<defs><linearGradient id="hg1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F5E9EF"/><stop offset="1" stop-color="#D7B48A" stop-opacity=".35"/></linearGradient><linearGradient id="hg2" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#D1A978"/><stop offset="1" stop-color="#F0D5AE"/></linearGradient></defs>
<rect x="18" y="20" width="384" height="190" rx="24" fill="url(#hg1)" opacity=".28"/><path d="M25 176 C80 137 119 169 163 132 C205 97 245 145 294 102 C330 70 366 91 400 59" fill="none" stroke="#D1A978" stroke-width="4" stroke-linecap="round"/><path d="M25 188 H400" stroke="#FFFFFF" stroke-opacity=".24"/><g fill="#FFFFFF" fill-opacity=".16"><rect x="42" y="133" width="34" height="55" rx="3"/><rect x="82" y="116" width="47" height="72" rx="3"/><rect x="138" y="146" width="30" height="42" rx="3"/><rect x="310" y="127" width="38" height="61" rx="3"/><rect x="354" y="108" width="31" height="80" rx="3"/></g>
<g transform="translate(182 41)"><rect width="104" height="148" rx="18" fill="#FFF" fill-opacity=".96"/><rect x="10" y="12" width="84" height="28" rx="8" fill="#F4E9EE"/><circle cx="25" cy="26" r="7" fill="#75465B"/><rect x="38" y="20" width="43" height="5" rx="2.5" fill="#806D76"/><rect x="38" y="29" width="28" height="4" rx="2" fill="#B7A8AF"/><rect x="10" y="49" width="84" height="62" rx="9" fill="#FAF6F8"/><path d="M18 94 L31 79 L43 86 L58 63 L70 75 L86 58" fill="none" stroke="#9B4D46" stroke-width="3"/><circle cx="58" cy="63" r="4" fill="#D1A978"/><rect x="18" y="120" width="68" height="7" rx="3.5" fill="#E8DCE2"/><rect x="18" y="132" width="46" height="6" rx="3" fill="#E8DCE2"/></g>
<g transform="translate(292 57)"><circle cx="42" cy="42" r="38" fill="#3D2030" fill-opacity=".92"/><path d="M42 18 L63 59 H21 Z" fill="url(#hg2)"/><rect x="39" y="31" width="6" height="15" rx="3" fill="#4B2638"/><circle cx="42" cy="52" r="3" fill="#4B2638"/></g>
<g transform="translate(54 52)"><rect width="104" height="62" rx="14" fill="#FFF" fill-opacity=".95"/><circle cx="19" cy="20" r="7" fill="#D1A978"/><rect x="32" y="14" width="54" height="6" rx="3" fill="#6B5962"/><rect x="17" y="34" width="69" height="5" rx="2.5" fill="#DCCFD5"/><rect x="17" y="45" width="49" height="5" rx="2.5" fill="#E5DCE0"/></g></svg>""",
        "signal": """<svg viewBox="0 0 260 120" role="img" aria-label="Illustration of disaster signal detection"><rect x="8" y="10" width="244" height="100" rx="18" fill="#F8F1F4"/><circle cx="54" cy="60" r="31" fill="#EEE1E7"/><path d="M54 31 L77 76 H31 Z" fill="#D1A978"/><rect x="51" y="46" width="6" height="17" rx="3" fill="#563247"/><circle cx="54" cy="69" r="3" fill="#563247"/><path d="M101 66 C117 39 130 82 145 55 C158 32 171 78 187 51 C201 28 218 61 240 39" fill="none" stroke="#75465B" stroke-width="4" stroke-linecap="round"/><circle cx="187" cy="51" r="5" fill="#9B4D46"/></svg>""",
        "language": """<svg viewBox="0 0 260 120" role="img" aria-label="Illustration of social media language"><rect x="16" y="17" width="150" height="82" rx="18" fill="#F5EBEF"/><path d="M53 99 L42 112 L75 99" fill="#F5EBEF"/><circle cx="45" cy="49" r="10" fill="#75465B"/><rect x="63" y="39" width="75" height="7" rx="3.5" fill="#8D7882"/><rect x="34" y="65" width="103" height="6" rx="3" fill="#D7C7CE"/><rect x="34" y="78" width="74" height="6" rx="3" fill="#D7C7CE"/><g transform="translate(174 29)"><circle cx="33" cy="31" r="31" fill="#563247"/><text x="33" y="40" text-anchor="middle" fill="#F1D6AD" font-family="Arial" font-size="28" font-weight="700">#</text></g><circle cx="213" cy="88" r="15" fill="#D1A978"/><text x="213" y="93" text-anchor="middle" fill="#4B2638" font-family="Arial" font-size="16" font-weight="700">@</text></svg>""",
        "human": """<svg viewBox="0 0 260 120" role="img" aria-label="Illustration of human review"><rect x="16" y="18" width="228" height="84" rx="18" fill="#F8F2F4"/><circle cx="62" cy="49" r="19" fill="#D1A978"/><path d="M31 93 C36 70 49 64 62 64 C75 64 88 70 93 93" fill="#75465B"/><rect x="113" y="30" width="104" height="62" rx="10" fill="#FFF"/><circle cx="129" cy="47" r="6" fill="#52705D"/><path d="M126 47 l3 3 l6 -7" fill="none" stroke="#FFF" stroke-width="2"/><rect x="142" y="43" width="58" height="6" rx="3" fill="#B9A8B0"/><circle cx="129" cy="66" r="6" fill="#D1A978"/><rect x="142" y="62" width="49" height="6" rx="3" fill="#CDBDC4"/><circle cx="129" cy="82" r="6" fill="#9B4D46"/><rect x="142" y="78" width="63" height="6" rx="3" fill="#D8C8CE"/></svg>""",
        "flood": """<svg viewBox="0 0 220 110" role="img" aria-label="Flood response illustration"><rect width="220" height="110" fill="#F5EDF1"/><circle cx="178" cy="25" r="15" fill="#D1A978" opacity=".75"/><path d="M0 73 C24 60 44 88 68 73 C93 58 117 88 143 73 C166 60 192 85 220 69 V110 H0 Z" fill="#8E7080" opacity=".5"/><path d="M0 84 C28 69 52 96 78 82 C107 66 134 98 162 81 C183 69 202 85 220 78 V110 H0 Z" fill="#75465B" opacity=".72"/><path d="M54 64 L87 39 L120 64 V85 H54 Z" fill="#FFF"/><rect x="83" y="66" width="15" height="19" fill="#D1A978"/><path d="M46 64 L87 31 L128 64" fill="none" stroke="#563247" stroke-width="5"/></svg>""",
        "fire": """<svg viewBox="0 0 220 110" role="img" aria-label="Urban fire response illustration"><rect width="220" height="110" fill="#F7EFF2"/><rect x="24" y="43" width="54" height="52" rx="3" fill="#CDBCC4"/><rect x="87" y="30" width="51" height="65" rx="3" fill="#E1D4DA"/><rect x="147" y="50" width="49" height="45" rx="3" fill="#C9B8C0"/><path d="M111 74 C88 56 106 42 114 30 C119 46 131 48 127 65 C139 55 148 69 140 83 C134 95 119 99 106 93 C95 88 94 80 111 74 Z" fill="#D1A978"/><path d="M116 81 C107 72 114 63 120 57 C122 67 131 69 128 80 C126 90 114 91 109 86 Z" fill="#9B4D46"/></svg>""",
        "storm": """<svg viewBox="0 0 220 110" role="img" aria-label="Storm illustration"><rect width="220" height="110" fill="#F4ECF0"/><path d="M44 55 C45 39 57 30 73 32 C81 18 104 15 116 31 C136 26 153 38 153 55 C170 56 181 65 181 77 H40 C31 67 35 58 44 55 Z" fill="#A8909B"/><path d="M93 73 L77 96 H92 L85 110 L113 82 H99 L108 73 Z" fill="#D1A978"/><path d="M37 89 l-12 14 M145 88 l-11 16 M177 87 l-10 13" stroke="#75465B" stroke-width="4" stroke-linecap="round"/></svg>""",
        "everyday": """<svg viewBox="0 0 220 110" role="img" aria-label="Everyday conversation illustration"><rect width="220" height="110" fill="#F6F1F3"/><circle cx="169" cy="28" r="18" fill="#D1A978"/><path d="M22 87 H198" stroke="#CDBCC4" stroke-width="3"/><path d="M39 87 V54 L70 34 L101 54 V87" fill="#FFF" stroke="#D8C9D0"/><rect x="59" y="61" width="18" height="26" fill="#E7D8DE"/><circle cx="141" cy="68" r="16" fill="#75465B"/><path d="M118 93 C121 78 129 73 141 73 C153 73 161 78 164 93" fill="#A18491"/><circle cx="141" cy="64" r="5" fill="#D1A978"/></svg>""",
        "disaster_result": """<svg viewBox="0 0 360 220" role="img" aria-label="Disaster classification illustration"><defs><linearGradient id="dr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F8ECEE"/><stop offset="1" stop-color="#F3D9D2"/></linearGradient></defs><rect x="14" y="18" width="332" height="184" rx="24" fill="url(#dr)"/><circle cx="180" cy="94" r="54" fill="#FFF"/><path d="M180 45 L225 129 H135 Z" fill="#D1A978"/><rect x="176" y="70" width="8" height="32" rx="4" fill="#563247"/><circle cx="180" cy="113" r="5" fill="#563247"/><path d="M55 169 C91 140 121 174 151 153 C183 131 211 169 245 147 C272 130 296 147 319 133" fill="none" stroke="#9B4D46" stroke-width="4" stroke-linecap="round"/><circle cx="319" cy="133" r="6" fill="#9B4D46"/></svg>""",
        "safe_result": """<svg viewBox="0 0 360 220" role="img" aria-label="Non-disaster classification illustration"><defs><linearGradient id="sr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#EEF5F0"/><stop offset="1" stop-color="#F7F1E8"/></linearGradient></defs><rect x="14" y="18" width="332" height="184" rx="24" fill="url(#sr)"/><circle cx="180" cy="92" r="53" fill="#FFF"/><path d="M151 93 L172 114 L214 68" fill="none" stroke="#52705D" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><rect x="74" y="157" width="212" height="13" rx="6.5" fill="#D9E6DC"/><rect x="111" y="177" width="138" height="9" rx="4.5" fill="#E8DED6"/></svg>""",
        "compare": """<svg viewBox="0 0 360 180" role="img" aria-label="Text comparison illustration"><rect x="18" y="28" width="134" height="118" rx="16" fill="#F7F0F3"/><rect x="208" y="28" width="134" height="118" rx="16" fill="#F4EDF0"/><rect x="36" y="48" width="94" height="7" rx="3.5" fill="#876D79"/><rect x="36" y="66" width="78" height="6" rx="3" fill="#CBBAC2"/><rect x="36" y="83" width="90" height="6" rx="3" fill="#D8CBD0"/><rect x="226" y="48" width="94" height="7" rx="3.5" fill="#876D79"/><rect x="226" y="66" width="73" height="6" rx="3" fill="#CBBAC2"/><rect x="226" y="83" width="84" height="6" rx="3" fill="#D8CBD0"/><path d="M161 72 H199" stroke="#D1A978" stroke-width="5" stroke-linecap="round"/><path d="M190 61 L202 72 L190 83" fill="none" stroke="#D1A978" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="85" cy="118" r="11" fill="#52705D"/><circle cx="275" cy="118" r="11" fill="#52705D"/></svg>""",
        "earthquake": """<svg viewBox="0 0 220 110" role="img" aria-label="Earthquake illustration"><rect width="220" height="110" fill="#F5EFF2"/><path d="M22 89 H198" stroke="#B9A6AF" stroke-width="3"/><rect x="40" y="46" width="48" height="43" rx="3" fill="#FFF"/><rect x="134" y="37" width="43" height="52" rx="3" fill="#E7DAE0"/><path d="M108 24 L96 47 L111 56 L98 76 L115 86" fill="none" stroke="#9B4D46" stroke-width="5" stroke-linecap="round"/><path d="M41 46 L64 29 L87 46 M134 37 L155 22 L177 37" fill="none" stroke="#75465B" stroke-width="4"/><path d="M0 95 C35 89 54 101 82 96 C111 90 137 102 164 96 C187 91 204 99 220 95 V110 H0 Z" fill="#D9C8CF"/></svg>""",
        "wildfire": """<svg viewBox="0 0 220 110" role="img" aria-label="Wildfire illustration"><rect width="220" height="110" fill="#F7F0F2"/><circle cx="181" cy="24" r="15" fill="#D1A978" opacity=".65"/><path d="M19 90 L49 48 L79 90 Z M63 90 L97 39 L130 90 Z M117 90 L150 52 L183 90 Z" fill="#806473" opacity=".8"/><path d="M134 91 C114 75 126 57 136 46 C140 61 151 63 148 77 C159 68 168 82 161 94 C155 103 143 106 132 101 C122 97 120 89 134 91 Z" fill="#D1A978"/><path d="M139 94 C132 87 137 78 143 72 C145 81 151 83 149 92 C147 99 139 101 134 97 Z" fill="#9B4D46"/></svg>""",
        "accident": """<svg viewBox="0 0 220 110" role="img" aria-label="Road accident illustration"><rect width="220" height="110" fill="#F5EFF2"/><path d="M0 85 H220" stroke="#D3C4CB" stroke-width="18"/><path d="M20 85 H200" stroke="#FFF" stroke-width="2" stroke-dasharray="14 10"/><rect x="50" y="61" width="60" height="22" rx="7" fill="#75465B"/><path d="M62 61 L75 48 H96 L106 61" fill="#A88C99"/><circle cx="67" cy="85" r="8" fill="#4B2638"/><circle cx="96" cy="85" r="8" fill="#4B2638"/><path d="M145 45 L165 82 H125 Z" fill="#D1A978"/><rect x="142" y="58" width="6" height="13" rx="3" fill="#563247"/><circle cx="145" cy="75" r="3" fill="#563247"/></svg>""",
        "medical": """<svg viewBox="0 0 220 110" role="img" aria-label="Emergency medical illustration"><rect width="220" height="110" fill="#F6F0F3"/><rect x="32" y="48" width="113" height="39" rx="8" fill="#FFF" stroke="#D8C8CF"/><path d="M145 58 H174 L191 75 V87 H145 Z" fill="#E6D9DF"/><circle cx="59" cy="88" r="9" fill="#563247"/><circle cx="166" cy="88" r="9" fill="#563247"/><rect x="75" y="55" width="15" height="26" fill="#D1A978"/><rect x="69" y="61" width="27" height="14" fill="#D1A978"/><path d="M188 37 C195 28 205 35 202 44 C199 51 188 58 188 58 C188 58 177 51 174 44 C171 35 181 28 188 37 Z" fill="#9B4D46"/></svg>""",
        "reliability": """<svg viewBox="0 0 360 190" role="img" aria-label="Human in the loop reliability illustration"><rect x="18" y="28" width="324" height="134" rx="22" fill="#F8F2F5"/><circle cx="72" cy="84" r="25" fill="#D1A978"/><path d="M34 140 C39 110 54 102 72 102 C90 102 105 110 110 140" fill="#75465B"/><rect x="136" y="52" width="91" height="76" rx="12" fill="#FFF"/><circle cx="157" cy="74" r="7" fill="#52705D"/><path d="M153 74 l3 3 l7 -8" fill="none" stroke="#FFF" stroke-width="2"/><rect x="171" y="70" width="38" height="7" rx="3.5" fill="#B8A7AF"/><circle cx="157" cy="94" r="7" fill="#D1A978"/><rect x="171" y="90" width="42" height="7" rx="3.5" fill="#CDBCC4"/><circle cx="157" cy="114" r="7" fill="#9B4D46"/><rect x="171" y="110" width="32" height="7" rx="3.5" fill="#DCCFD5"/><path d="M236 90 H286" stroke="#D1A978" stroke-width="5" stroke-linecap="round"/><path d="M276 78 L290 90 L276 102" fill="none" stroke="#D1A978" stroke-width="5" stroke-linejoin="round"/><circle cx="310" cy="90" r="23" fill="#563247"/><path d="M298 90 L306 98 L322 80" fill="none" stroke="#F1D6AD" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
    }
    return visuals.get(kind, visuals["signal"])


def visual_card(kind, eyebrow, title, copy):
    return f'<div class="visual-card"><div class="visual-card-art">{visual_svg(kind)}</div><div class="visual-card-copy"><div class="eyebrow">{eyebrow}</div><div class="title">{title}</div><p>{copy}</p></div></div>'


def scenario_card(kind, title, copy):
    return f'<div class="scenario-art">{visual_svg(kind)}</div><div class="scenario-label"><b>{title}</b><div>{copy}</div></div>'


def message_profile_html(diagnostics):
    specs = [
        ("Hashtags", diagnostics.get("Hashtags", 0), 4),
        ("Mentions", diagnostics.get("Mentions", 0), 4),
        ("URLs", diagnostics.get("URLs", 0), 3),
        ("Exclamations", diagnostics.get("Exclamations", 0), 6),
        ("Uppercase", diagnostics.get("Uppercase tokens", 0), 6)
    ]
    rows = []
    for label, value, scale in specs:
        pct = max(0, min(100, int((float(value) / scale) * 100)))
        rows.append(
            f'<div class="profile-row"><div class="profile-label">{label}</div><div class="profile-track"><div class="profile-fill" style="width:{pct}%"></div></div><div class="profile-value">{value}</div></div>'
        )
    return '<div class="profile">' + ''.join(rows) + '<div style="font-size:10px;color:#8D7681;margin-top:10px;line-height:1.5">Visualizes message structure only. These bars are not feature-importance or model-explanation scores.</div></div>'


def surface_signal_snapshot(text):
    text_lower = str(text).lower()
    categories = {
        "Flood / Water": ["flood", "flooding", "river", "water", "submerged", "inundation", "overflow"],
        "Fire / Smoke": ["fire", "smoke", "burning", "flames", "wildfire", "blaze"],
        "Storm / Weather": ["storm", "cyclone", "hurricane", "tornado", "lightning", "wind", "rain"],
        "Earth / Structural": ["earthquake", "quake", "collapse", "collapsed", "rubble", "landslide"],
        "Emergency Response": ["emergency", "rescue", "evacuate", "evacuation", "ambulance", "firefighters", "police", "trapped"],
        "Human Impact": ["injured", "injury", "dead", "deaths", "missing", "victims", "casualties", "hospital"]
    }
    found = {}
    for category, words in categories.items():
        matches = [word for word in words if re.search(r"\b" + re.escape(word) + r"\b", text_lower)]
        if matches:
            found[category] = matches
    return found


def signal_snapshot_html(snapshot):
    if not snapshot:
        return '<div class="signal-lens"><div class="lens-head"><div class="lens-title">Surface Signal Lens</div><div class="lens-note">descriptive scan · not a model explanation</div></div><div class="signal-tags"><span class="signal-tag muted">No predefined disaster-topic terms detected</span></div><div style="font-size:9.5px;color:#8A7780;margin-top:10px;line-height:1.5">The model can still classify the message using its full learned representation. This lens only highlights a small transparent keyword set for user orientation.</div></div>'
    groups=[]
    for category, words in snapshot.items():
        tags=''.join(f'<span class="signal-tag">{word}</span>' for word in words)
        groups.append(f'<div class="signal-group"><b>{category}</b><div class="signal-tags">{tags}</div></div>')
    return '<div class="signal-lens"><div class="lens-head"><div class="lens-title">Surface Signal Lens</div><div class="lens-note">descriptive scan · not a model explanation</div></div>' + ''.join(groups) + '<div style="font-size:9.5px;color:#8A7780;margin-top:10px;line-height:1.5">These matches are visible vocabulary cues only. They are not feature weights, SHAP values, causal explanations, or emergency-severity scores.</div></div>'


def performance_bars_html(available_metrics):
    rows=[]
    for name, value, _ in available_metrics:
        try:
            pct=max(0.0,min(100.0,float(value)*100))
        except Exception:
            continue
        rows.append(f'<div class="metric-row"><div class="metric-name">{name}</div><div class="metric-track"><div class="metric-fill" style="width:{pct:.2f}%"></div></div><div class="metric-val">{pct:.2f}%</div></div>')
    return '<div class="metric-bars">' + ''.join(rows) + '</div>'


def confusion_visual_html(tn, fp, fn, tp):
    return f"""<div class="matrix-grid">
    <div class="matrix-cell good"><div class="m-label">True Negative</div><div class="m-value">{tn}</div><div class="m-copy">Correctly identified non-disaster messages.</div></div>
    <div class="matrix-cell bad"><div class="m-label">False Positive</div><div class="m-value">{fp}</div><div class="m-copy">False alerts that can increase review burden.</div></div>
    <div class="matrix-cell bad"><div class="m-label">False Negative</div><div class="m-value">{fn}</div><div class="m-copy">Missed disaster messages that may lose priority.</div></div>
    <div class="matrix-cell good"><div class="m-label">True Positive</div><div class="m-value">{tp}</div><div class="m-copy">Correctly identified disaster-related messages.</div></div>
    </div>"""


def generic_numeric_view(df, key_prefix):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        selected = st.selectbox(
            "Numeric field to visualize",
            numeric_cols,
            key=f"{key_prefix}_numeric"
        )
        chart_df = df[[selected]].dropna().head(100)
        if not chart_df.empty:
            st.bar_chart(chart_df, height=260)


def screenshot_summary():
    summary_path = SCREENSHOT_DIR / "streamlit_screenshot_summary.json"
    if summary_path.exists():
        try:
            return json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def capture_streamlit_screenshots():
    port = int(os.getenv("STREAMLIT_SERVER_PORT", st.get_option("server.port") or 8501))
    capture_time = datetime.now(ZoneInfo("Asia/Kolkata"))
    capture_id = capture_time.strftime("%Y%m%d_%H%M%S_%f")[:-3]
    capture_url = f"http://127.0.0.1:{port}?capture_mode=1"
    latest_path = SCREENSHOT_DIR / "latest_streamlit.png"

    capture_script = r'''
import json, sys, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

url = sys.argv[1]
out_dir = Path(sys.argv[2])
capture_id = sys.argv[3]
latest_path = Path(sys.argv[4])
out_dir.mkdir(parents=True, exist_ok=True)

captures = [
    ("01_analyze", "Analyze Tweet"),
    ("02_explore_compare", "Explore & Compare"),
    ("03_session_history", "Session History"),
    ("04_model_performance", "Model Performance"),
    ("05_reliability", "Reliability & Limitations"),
    ("06_system_diagnostics", "System Diagnostics")
]

created = []
errors = []

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1440, "height": 1100},
        device_scale_factor=1
    )
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=120000)

    try:
        page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=60000)
    except Exception:
        pass

    try:
        page.wait_for_function("document.body.innerText.length > 150", timeout=30000)
    except Exception:
        pass

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    page.wait_for_timeout(3500)

    for index, (slug, tab_name) in enumerate(captures):
        try:
            if index > 0:
                tab = page.get_by_role("tab", name=tab_name)
                if tab.count() == 0:
                    errors.append(f"Tab not found: {tab_name}")
                    continue
                tab.first.click()
                page.wait_for_timeout(900)

            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            page.wait_for_timeout(400)
            page.evaluate("window.scrollTo(0, 0);")
            page.wait_for_timeout(300)

            output = out_dir / f"streamlit_{capture_id}_{slug}.png"
            page.screenshot(path=str(output), full_page=True)
            created.append(str(output))

            latest_tab = out_dir / f"latest_{slug}.png"
            shutil.copy2(output, latest_tab)

            if index == 0:
                shutil.copy2(output, latest_path)

        except Exception as exc:
            errors.append(f"{tab_name}: {exc}")

    context.close()
    browser.close()

print(json.dumps({"created": created, "errors": errors}))
'''

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                capture_script,
                capture_url,
                str(SCREENSHOT_DIR),
                capture_id,
                str(latest_path)
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(BASE_DIR)
        )

        if result.returncode != 0:
            return {
                "success": False,
                "message": result.stderr.strip() or result.stdout.strip() or "Automatic screenshot capture failed.",
                "created": [],
                "errors": []
            }

        try:
            payload = json.loads(result.stdout.strip().splitlines()[-1])
        except Exception:
            payload = {"created": [], "errors": [result.stdout.strip()] if result.stdout.strip() else []}

        created = [Path(x) for x in payload.get("created", []) if Path(x).exists()]
        success = len(created) > 0
        summary = {
            "streamlit_file": str(BASE_DIR / "streamlit_app.py"),
            "streamlit_url": capture_url,
            "captured_at": capture_time.strftime("%d %b %Y · %I:%M:%S %p IST"),
            "capture_id": capture_id,
            "screenshots_created": [str(x) for x in created],
            "latest_screenshot": str(latest_path),
            "errors": payload.get("errors", []),
            "status": "PASS" if success else "REVIEW"
        }
        (SCREENSHOT_DIR / "streamlit_screenshot_summary.json").write_text(
            json.dumps(summary, indent=2, default=str),
            encoding="utf-8"
        )
        return {
            "success": success,
            "message": "Automatic interface evidence captured." if success else "No screenshot files were created.",
            "created": created,
            "latest": latest_path,
            "errors": payload.get("errors", []),
            "captured_at": capture_time
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Automatic screenshot capture timed out after 180 seconds.",
            "created": [],
            "errors": []
        }
    except Exception as exc:
        return {
            "success": False,
            "message": str(exc),
            "created": [],
            "errors": []
        }


for key, value in {
    "tweet_input": "",
    "last_result": None,
    "last_error": None,
    "last_latency": None,
    "history": [],
    "comparison_results": None,
    "batch_results": None,
    "selected_history_row": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

online, health_latency, health_data = health()

health_label = "Online" if online else "Offline"
health_latency_text = f"{health_latency:.1f} ms" if health_latency is not None else "Unavailable"

st.markdown(
    f"""
<div class="hero">
<div class="hero-grid">
<div>
<div style="color:#E7C99F;font-size:10px;font-weight:700;letter-spacing:2px">PRODUCTION NLP · HUMAN-IN-THE-LOOP DECISION SUPPORT</div>
<h1>{CONFIG.get("app_name", "Disaster Tweet Intelligence")}</h1>
<p>Analyze disaster-related social-media messages, compare controlled text variations, review session evidence, inspect validated model performance, and monitor the production system without bypassing the locked Flask inference backend.</p>
<div class="hero-meta">
<span class="hero-pill">Backend · {health_label}</span>
<span class="hero-pill">Model · {health_data.get("model_version", CONFIG.get("model_version", "unknown"))}</span>
<span class="hero-pill">Health latency · {health_latency_text}</span>
<span class="hero-pill">Evaluation · {CONFIG.get("evaluation_dataset", "Protected test set")}</span>
</div>
</div>
<div class="hero-art">{visual_svg("hero")}</div>
</div>
</div>
""",
    unsafe_allow_html=True
)

st.markdown(
    '<div class="visual-strip">'
    + visual_card("signal", "Detect", "Disaster Signals", "Surface disaster-related language for rapid analytical triage while preserving the locked model boundary.")
    + visual_card("language", "Understand", "Social Context", "Inspect hashtags, mentions, URLs, punctuation and message structure without pretending they are model explanations.")
    + visual_card("human", "Review", "Human Oversight", "Use predictions as decision-support signals and keep contextual judgement for consequential emergency decisions.")
    + '</div>',
    unsafe_allow_html=True
)

evidence_image_count = len([p for p in SCREENSHOT_DIR.glob("streamlit_*.png") if p.is_file() and p.name != "latest_streamlit.png"])
command_html = f"""<div class="command-grid">
<div class="command-card"><div class="label">Production API</div><div class="big">{'ONLINE' if online else 'OFFLINE'}</div><div class="small">Live Flask health check · {health_latency_text}</div></div>
<div class="command-card"><div class="label">Governance</div><div class="big">LOCKED</div><div class="small">Protected-test configuration is not tuned from this UI.</div></div>
<div class="command-card"><div class="label">Session Activity</div><div class="big">{len(st.session_state.history)}</div><div class="small">Predictions generated in this active interface session.</div></div>
<div class="command-card"><div class="label">UI Evidence</div><div class="big">{evidence_image_count}</div><div class="small">Saved screenshot evidence images available locally.</div></div>
</div>"""
st.markdown(command_html, unsafe_allow_html=True)

tour_choice = st.radio(
    "Quick visual tour",
    ["1 · Classify", "2 · Stress-test", "3 · Review evidence"],
    horizontal=True,
    label_visibility="collapsed",
    key="quick_visual_tour"
)

tour_content = {
    "1 · Classify": ("01", "Classify one message", "Enter a tweet, review its structure, run the locked production model, and inspect score semantics without converting raw decision scores into confidence percentages."),
    "2 · Stress-test": ("02", "Test robustness", "Use What-if Lab or Batch Analysis to compare controlled variations through the same Flask /predict endpoint. No model parameters or thresholds are changed."),
    "3 · Review evidence": ("03", "Inspect reliability and evidence", "Review protected-test metrics, operational risks, system health, session history and automatically captured UI evidence before handover.")
}

tour_num, tour_title, tour_copy = tour_content[tour_choice]
st.markdown(
    f'<div class="tour-box"><div class="tour-number">{tour_num}</div><div><b>{tour_title}</b><p>{tour_copy}</p></div></div>',
    unsafe_allow_html=True
)

with st.sidebar:
    st.markdown("### System Status")
    if CONFIG.get("config_warning"):
        st.warning(CONFIG["config_warning"])

    if online:
        st.markdown(
            f'<div class="status-panel"><div class="status-line"><span class="status-dot online"></span>Production API online</div><div class="status-detail">Flask health check passed · {health_latency:.1f} ms</div></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="status-panel"><div class="status-line"><span class="status-dot offline"></span>Backend not connected</div><div class="status-detail">The interface is available, but predictions require the Flask service at the configured API URL.</div></div>',
            unsafe_allow_html=True
        )

    if st.button("Refresh system status", width="stretch"):
        health.clear()
        st.rerun()

    st.divider()
    st.markdown("### Locked Model")
    st.caption(CONFIG.get("model_name", "Locked Production Model"))
    st.caption(f"Version: {health_data.get('model_version', CONFIG.get('model_version', 'unknown'))}")
    st.caption(f"Features: {CONFIG.get('feature_id', 'Final locked feature set')}")
    st.caption(f"Evaluation: {CONFIG.get('evaluation_dataset', 'Protected test set')}")

    st.divider()
    st.markdown("### Session")
    st.metric("Predictions", len(st.session_state.history))
    if st.session_state.history:
        disaster_count = sum(1 for x in st.session_state.history if x.get("Prediction Code") == 1)
        st.caption(f"Disaster: {disaster_count} · Non-disaster: {len(st.session_state.history)-disaster_count}")

    st.divider()
    st.caption(CONFIG.get("disclaimer", "This tool is not an official emergency authority."))


tab_analyze, tab_explore, tab_history, tab_performance, tab_reliability, tab_system, tab_evidence = st.tabs(
    [
        "Analyze Tweet",
        "Explore & Compare",
        "Session History",
        "Model Performance",
        "Reliability & Limitations",
        "System Diagnostics",
        "Evidence"
    ]
)


with tab_analyze:
    st.markdown('<div class="section">Analyze a Tweet</div>', unsafe_allow_html=True)
    st.caption("Run one message through the validated Flask backend. Input diagnostics below describe the text only; they are not model explanations.")

    st.markdown('<div class="subsection">How to Use the Intelligence Workspace</div>', unsafe_allow_html=True)
    st.markdown("""<div class="step-flow">
    <div class="step-card"><div class="num">1</div><b>Choose or write a message</b><p>Start with a scenario card or paste your own short social-media post.</p></div>
    <div class="step-card"><div class="num">2</div><b>Inspect the message</b><p>Review transparent text diagnostics and the surface signal lens before prediction.</p></div>
    <div class="step-card"><div class="num">3</div><b>Classify & review</b><p>Send the message to Flask, inspect score semantics, then compare or save evidence.</p></div>
    </div>""", unsafe_allow_html=True)

    examples = [
        ("flood", "Flood warning", "Emergency-response language", "Severe flooding has trapped residents near the river. Emergency crews are responding."),
        ("fire", "Urban fire", "Noisy breaking-news style", "@cityalerts HUGE fire downtown!!! #Breaking https://example.com/update"),
        ("storm", "Severe storm", "Weather-impact report", "Power lines are down after a violent storm damaged homes across the coastal district."),
        ("earthquake", "Earthquake", "Structural-impact report", "Strong earthquake shakes the city; several buildings have collapsed and rescue teams are searching rubble."),
        ("wildfire", "Wildfire", "Evacuation-oriented report", "Wildfire is spreading rapidly through the hills and residents have been told to evacuate immediately."),
        ("accident", "Road accident", "Transport emergency", "Major highway crash has blocked two lanes. Ambulances and rescue crews are at the scene."),
        ("medical", "Medical emergency", "Urgent human-impact language", "Multiple people are injured after the incident and emergency medical teams are responding."),
        ("everyday", "Everyday post", "Ordinary social conversation", "Beautiful weather today. Heading out for lunch with friends.")
    ]

    st.markdown('<div class="subsection">Scenario Gallery</div>', unsafe_allow_html=True)
    st.caption("Choose a visual scenario to load an example, or type your own message below. The illustrations are interface aids, not labels or model evidence.")
    for start in range(0, len(examples), 4):
        cols = st.columns(4)
        for col, (kind, label, copy, text) in zip(cols, examples[start:start+4]):
            with col:
                st.markdown(scenario_card(kind, label, copy), unsafe_allow_html=True)
                if st.button(f"Use {label}", key=f"example_{label}", width="stretch"):
                    st.session_state.tweet_input = text
                    st.session_state.last_result = None
                    st.session_state.last_error = None
                    st.rerun()

    tweet = st.text_area(
        "Tweet text",
        key="tweet_input",
        height=155,
        placeholder="Enter one tweet or short social-media message."
    )

    diagnostics = text_diagnostics(tweet)
    chars = diagnostics["Characters"]
    st.markdown(
        f'<div class="counter {"warn" if chars > MAX_CHARS else ""}">{chars:,} / {MAX_CHARS:,} characters</div>',
        unsafe_allow_html=True
    )

    metric_cols = st.columns(4)
    for col, key in zip(metric_cols, ["Words", "Hashtags", "Mentions", "URLs"]):
        col.metric(key, diagnostics[key])

    st.markdown(signal_snapshot_html(surface_signal_snapshot(tweet)), unsafe_allow_html=True)

    with st.expander("Detailed input diagnostics"):
        detail_df = pd.DataFrame(
            [{"Measure": key, "Value": value} for key, value in diagnostics.items()]
        )
        st.dataframe(detail_df, width="stretch", hide_index=True)
        st.markdown('<div class="subsection">Message Structure Profile</div>', unsafe_allow_html=True)
        st.markdown(message_profile_html(diagnostics), unsafe_allow_html=True)
        st.caption("These are descriptive text properties only. They do not indicate feature importance or causality.")

    c1, c2, c3 = st.columns([1.25, 1, 3])
    with c1:
        analyze = st.button("Analyze Tweet", type="primary", width="stretch")
    with c2:
        st.button("Clear / Reset", on_click=reset_analysis, width="stretch")
    with c3:
        st.caption("Prediction is sent to Flask `/predict`; the Streamlit UI does not load the model directly.")

    if analyze:
        st.session_state.last_error = None
        st.session_state.last_result = None

        if not tweet.strip():
            st.session_state.last_error = "Enter tweet text before requesting a prediction."
        elif len(tweet) > MAX_CHARS:
            st.session_state.last_error = f"Tweet text is too long. Reduce it to {MAX_CHARS:,} characters or fewer."
        elif not online:
            st.session_state.last_error = "Prediction service unavailable. Your text has been preserved."
        else:
            try:
                with st.spinner("Analyzing tweet..."):
                    result, latency = predict(tweet)
                st.session_state.last_result = result
                st.session_state.last_latency = latency
                st.session_state.history.insert(0, history_entry(tweet, result, latency))
                st.session_state.history = st.session_state.history[:100]
            except Exception as exc:
                st.session_state.last_error = str(exc)

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    result = st.session_state.last_result
    if result:
        pred, label = result_label(result)
        css = "disaster" if pred == 1 else "safe"
        model_version = result.get("model_version", health_data.get("model_version", CONFIG.get("model_version", "unknown")))
        latency = st.session_state.last_latency or 0.0

        result_left, result_right = st.columns([1.55, 1])
        with result_left:
            st.markdown(
                f'<div class="result {css}"><div style="font-size:10px;color:#8E7682;letter-spacing:1px;font-weight:700">CLASSIFICATION RESULT</div><div style="font:500 30px Georgia;color:#4B2638;margin:3px 0">{label}</div><div style="color:#71646A;font-size:12px">Model {model_version} · {latency:.1f} ms</div><div style="margin-top:12px;color:#61545A;font-size:12px;line-height:1.6">{"Potential disaster-related signal detected. Review the original message and operational context before escalation." if pred == 1 else "The message was classified as non-disaster by the locked model. This does not prove that the real-world situation is safe."}</div></div>',
                unsafe_allow_html=True
            )
        with result_right:
            st.markdown(
                f'<div class="result-visual">{visual_svg("disaster_result" if pred == 1 else "safe_result")}</div>',
                unsafe_allow_html=True
            )

        prob, score_type = probability_value(result)
        score = result.get("score")

        result_cols = st.columns(3)
        result_cols[0].metric("Prediction", label)
        result_cols[1].metric("Latency", f"{latency:.1f} ms")
        result_cols[2].metric("Score Type", score_type)

        if prob is not None:
            st.metric("Predicted-class probability", f"{prob*100:.1f}%")
            st.progress(max(0.0, min(1.0, prob)))
            if prob < CAUTION:
                st.info("The returned probability is below the configured caution level. Treat this result as relatively uncertain and review the message context.")
            else:
                st.caption("Probability is displayed as returned by the validated backend. It is not an emergency severity score.")
        elif score is not None:
            try:
                st.metric("Decision score", f"{float(score):.4f}")
            except Exception:
                st.metric("Decision score", str(score))
            st.caption("This is a decision score, not a calibrated probability or confidence percentage.")

        st.markdown(
            f'<div class="info"><b>Responsible-use note:</b> {CONFIG.get("disclaimer", "This tool is not an official emergency authority.")}</div>',
            unsafe_allow_html=True
        )

        action_copy = (
            ("Review context", "Check the original wording, source context and any corroborating information before escalation."),
            ("Stress-test wording", "Use Explore & Compare to see whether controlled formatting changes alter the model output."),
            ("Preserve evidence", "Download the result or keep the session record for QA, review or project evidence.")
        )
        st.markdown('<div class="action-strip">' + ''.join(f'<div class="action-card"><b>{title}</b><span>{copy}</span></div>' for title, copy in action_copy) + '</div>', unsafe_allow_html=True)

        detail_tab1, detail_tab2, detail_tab3 = st.tabs(["Backend Output", "Processed Text", "Export"])
        with detail_tab1:
            st.json(result)
        with detail_tab2:
            if result.get("processed_text"):
                st.code(result["processed_text"])
            else:
                st.caption("Processed text is not exposed by the current validated backend response.")
            if result.get("explanation") is not None:
                st.write(result["explanation"])
            else:
                st.caption("No model explanation was supplied by the backend; the UI does not fabricate one.")
        with detail_tab3:
            export = {
                "tweet": tweet,
                **result,
                "latency_ms": latency,
                "input_diagnostics": diagnostics
            }
            st.download_button(
                "Download prediction JSON",
                json.dumps(export, indent=2, default=str),
                "disaster_tweet_prediction.json",
                "application/json",
                width="stretch"
            )


with tab_explore:
    st.markdown('<div class="section">Explore & Compare</div>', unsafe_allow_html=True)
    st.caption("Test robustness without changing the locked model. These tools submit alternate text inputs to the same production `/predict` endpoint.")

    st.markdown(
        f'<div class="feature-story"><div>{visual_svg("compare")}</div><div><h4>Compare wording, not model settings</h4><p>Controlled variants help reveal whether formatting, hashtags, mentions, URLs or punctuation coincide with prediction changes. The model, feature pipeline and deployment threshold remain locked throughout this exploration.</p></div></div>',
        unsafe_allow_html=True
    )

    whatif_tab, batch_tab = st.tabs(["What-if Lab", "Batch Analysis"])

    with whatif_tab:
        base_text = st.text_area(
            "Base message",
            value=st.session_state.tweet_input,
            height=130,
            key="whatif_base",
            placeholder="Enter a message to compare across controlled text variations."
        )

        if base_text.strip():
            variants = variation_set(base_text)
            st.caption(f"{len(variants)} deterministic variations are available. No model or threshold settings are changed.")
            preview_df = pd.DataFrame(
                [{"Variation": name, "Text": text} for name, text in variants.items()]
            )
            st.dataframe(preview_df, width="stretch", hide_index=True)
        else:
            variants = {}

        run_compare = st.button(
            "Run What-if Comparison",
            type="primary",
            width="stretch",
            disabled=(not base_text.strip() or not online)
        )

        if run_compare:
            comparison_rows = []
            with st.spinner("Running controlled variations through the production backend..."):
                for name, text in variants.items():
                    try:
                        result, latency = predict(text)
                        pred, label = result_label(result)
                        comparison_rows.append({
                            "Variation": name,
                            "Text": text,
                            "Prediction": label,
                            "Prediction Code": pred,
                            "Score": result.get("score"),
                            "Score Type": result.get("score_type", "Class Only"),
                            "Latency ms": round(latency, 2),
                            "Status": "PASS"
                        })
                    except Exception as exc:
                        comparison_rows.append({
                            "Variation": name,
                            "Text": text,
                            "Prediction": "Unavailable",
                            "Prediction Code": None,
                            "Score": None,
                            "Score Type": None,
                            "Latency ms": None,
                            "Status": f"ERROR: {exc}"
                        })
            st.session_state.comparison_results = pd.DataFrame(comparison_rows)

        if isinstance(st.session_state.comparison_results, pd.DataFrame) and not st.session_state.comparison_results.empty:
            compare_df = st.session_state.comparison_results
            st.dataframe(compare_df, width="stretch", hide_index=True)

            valid_compare = compare_df[compare_df["Prediction Code"].notna()].copy()
            if not valid_compare.empty:
                unique_predictions = valid_compare["Prediction Code"].nunique()
                agreement = 100 * valid_compare["Prediction Code"].value_counts(normalize=True).max()
                c1, c2, c3 = st.columns(3)
                c1.metric("Variations Tested", len(valid_compare))
                c2.metric("Prediction Agreement", f"{agreement:.1f}%")
                c3.metric("Label Changes", "Yes" if unique_predictions > 1 else "No")
                if unique_predictions > 1:
                    st.warning("The predicted label changes across these controlled text variations. Review this message as a robustness-sensitive case.")
                else:
                    st.success("The predicted label remains stable across the tested deterministic variations.")

            st.download_button(
                "Download comparison CSV",
                compare_df.to_csv(index=False).encode(),
                "what_if_comparison.csv",
                "text/csv",
                width="stretch"
            )

    with batch_tab:
        st.caption("Enter one message per line. Batch size is capped to keep the interface responsive and avoid excessive API requests.")
        batch_text = st.text_area(
            "Batch messages",
            height=190,
            key="batch_text",
            placeholder="Severe storm damage reported near the coast.\nHeading to dinner after work.\nEmergency crews responding to a large fire."
        )
        messages = [line.strip() for line in batch_text.splitlines() if line.strip()]
        max_batch = 20
        st.caption(f"Detected {len(messages)} message(s) · maximum {max_batch}")
        add_to_history = st.checkbox("Add successful batch predictions to session history", value=False)

        run_batch = st.button(
            "Analyze Batch",
            type="primary",
            width="stretch",
            disabled=(not messages or len(messages) > max_batch or not online)
        )

        if messages and len(messages) > max_batch:
            st.warning(f"Reduce the batch to {max_batch} messages or fewer.")

        if run_batch:
            rows = []
            with st.spinner("Analyzing batch..."):
                for index, message in enumerate(messages, start=1):
                    try:
                        result, latency = predict(message)
                        pred, label = result_label(result)
                        row = {
                            "#": index,
                            "Tweet": message,
                            "Prediction": label,
                            "Prediction Code": pred,
                            "Score": result.get("score"),
                            "Score Type": result.get("score_type", "Class Only"),
                            "Latency ms": round(latency, 2),
                            "Status": "PASS"
                        }
                        rows.append(row)
                        if add_to_history:
                            st.session_state.history.insert(0, history_entry(message, result, latency, source="Batch Analysis"))
                    except Exception as exc:
                        rows.append({
                            "#": index,
                            "Tweet": message,
                            "Prediction": "Unavailable",
                            "Prediction Code": None,
                            "Score": None,
                            "Score Type": None,
                            "Latency ms": None,
                            "Status": f"ERROR: {exc}"
                        })
            st.session_state.history = st.session_state.history[:100]
            st.session_state.batch_results = pd.DataFrame(rows)

        if isinstance(st.session_state.batch_results, pd.DataFrame) and not st.session_state.batch_results.empty:
            batch_df = st.session_state.batch_results
            st.dataframe(batch_df, width="stretch", hide_index=True)
            valid_batch = batch_df[batch_df["Prediction Code"].notna()]
            if not valid_batch.empty:
                counts = valid_batch["Prediction"].value_counts()
                c1, c2, c3 = st.columns(3)
                c1.metric("Successful", len(valid_batch))
                c2.metric("Disaster", int((valid_batch["Prediction Code"] == 1).sum()))
                c3.metric("Mean Latency", f"{valid_batch['Latency ms'].mean():.1f} ms")
                st.bar_chart(counts)
            st.download_button(
                "Download batch CSV",
                batch_df.to_csv(index=False).encode(),
                "batch_predictions.csv",
                "text/csv",
                width="stretch"
            )


with tab_history:
    st.markdown('<div class="section">Session History</div>', unsafe_allow_html=True)
    st.caption("Review only predictions generated in this active Streamlit session. No persistent user-identifying store is created by this interface.")

    if not st.session_state.history:
        st.info("No predictions have been generated in this session yet.")
    else:
        history_df = pd.DataFrame(st.session_state.history)
        total = len(history_df)
        disaster_total = int((history_df["Prediction Code"] == 1).sum())
        non_disaster_total = total - disaster_total
        mean_latency = pd.to_numeric(history_df["Latency ms"], errors="coerce").mean()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Predictions", total)
        c2.metric("Disaster", disaster_total)
        c3.metric("Not Disaster", non_disaster_total)
        c4.metric("Mean Latency", f"{mean_latency:.1f} ms" if pd.notna(mean_latency) else "N/A")

        f1, f2, f3 = st.columns([1.2, 2.4, 1])
        with f1:
            pred_filter = st.selectbox("Prediction filter", ["All", "Real Disaster", "Not a Disaster"])
        with f2:
            search_term = st.text_input("Search session text", placeholder="Search tweet content...")
        with f3:
            row_limit = st.selectbox("Rows", [10, 25, 50, 100], index=1)

        filtered = history_df.copy()
        if pred_filter != "All":
            filtered = filtered[filtered["Prediction"] == pred_filter]
        if search_term.strip():
            filtered = filtered[filtered["Tweet"].astype(str).str.contains(search_term, case=False, na=False, regex=False)]
        filtered = filtered.head(row_limit)

        st.dataframe(filtered, width="stretch", hide_index=True)

        history_view1, history_view2 = st.tabs(["Classification Mix", "Latency Trend"])
        with history_view1:
            count_chart = history_df["Prediction"].value_counts()
            st.bar_chart(count_chart, height=260)
            st.caption("Shows the mix of labels returned during this session only; it is not a population prevalence estimate.")
        with history_view2:
            latency_series = pd.to_numeric(history_df["Latency ms"], errors="coerce").dropna()
            if not latency_series.empty:
                latency_plot = pd.DataFrame({"Latency ms": list(reversed(latency_series.tolist()))})
                st.line_chart(latency_plot, height=260)
                st.caption("Tracks API response latency across successful session predictions in chronological order.")
            else:
                st.info("No valid latency values are available in the current session history.")

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Download Session CSV",
                history_df.to_csv(index=False).encode(),
                "prediction_session_history.csv",
                "text/csv",
                width="stretch"
            )
        with d2:
            if st.button("Clear Session History", width="stretch"):
                st.session_state.history = []
                st.rerun()


with tab_performance:
    st.markdown('<div class="section">Validated Model Performance</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info"><b>Evaluation boundary:</b> Metrics shown here should represent the locked model on the configured protected evaluation dataset. This view is diagnostic only and must not be used to tune the locked configuration.</div>',
        unsafe_allow_html=True
    )

    perf = CONFIG.get("performance", {}) or {}
    metric_specs = [
        ("Accuracy", perf.get("accuracy"), "Overall proportion classified correctly."),
        ("Precision", perf.get("precision"), "Among predicted disasters, the proportion that were actual disasters."),
        ("Recall", perf.get("recall"), "Among actual disasters, the proportion identified by the model."),
        ("F1 Score", perf.get("f1"), "Harmonic balance between precision and recall."),
        ("ROC-AUC", perf.get("roc_auc"), "Ranking performance across classification thresholds."),
        ("PR-AUC", perf.get("pr_auc"), "Precision-recall ranking quality, especially useful with class imbalance.")
    ]
    available_metrics = [(name, value, desc) for name, value, desc in metric_specs if value is not None]

    if available_metrics:
        for start in range(0, len(available_metrics), 3):
            row = available_metrics[start:start+3]
            cols = st.columns(len(row))
            for col, (name, value, desc) in zip(cols, row):
                with col:
                    st.metric(name, f"{float(value)*100:.2f}%")
                    st.caption(desc)

        st.markdown('<div class="subsection">Performance Profile</div>', unsafe_allow_html=True)
        st.markdown(performance_bars_html(available_metrics), unsafe_allow_html=True)
        perf_chart = pd.DataFrame(
            {"Metric": [x[0] for x in available_metrics], "Value": [float(x[1]) for x in available_metrics]}
        ).set_index("Metric")
        with st.expander("Open chart view"):
            st.bar_chart(perf_chart, height=300)
    else:
        st.info("Validated metrics were not included in ui_config.json. The interface will not invent performance values.")

    cm = CONFIG.get("confusion_matrix", {}) or {}
    if all(cm.get(key) is not None for key in ["tn", "fp", "fn", "tp"]):
        tn, fp, fn, tp = [int(cm[key]) for key in ["tn", "fp", "fn", "tp"]]
        st.markdown('<div class="subsection">Confusion Matrix & Error Burden</div>', unsafe_allow_html=True)
        matrix = pd.DataFrame(
            [[tn, fp], [fn, tp]],
            index=["Actual: Not Disaster", "Actual: Real Disaster"],
            columns=["Predicted: Not Disaster", "Predicted: Real Disaster"]
        )
        st.markdown(confusion_visual_html(tn, fp, fn, tp), unsafe_allow_html=True)
        with st.expander("Open confusion-matrix table"):
            st.dataframe(matrix, width="stretch")

        false_alert_rate = fp / (fp + tn) if (fp + tn) else None
        miss_rate = fn / (fn + tp) if (fn + tp) else None
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("False Alerts", fp)
        c2.metric("Missed Disasters", fn)
        c3.metric("False-alert Rate", f"{false_alert_rate*100:.2f}%" if false_alert_rate is not None else "N/A")
        c4.metric("Miss Rate", f"{miss_rate*100:.2f}%" if miss_rate is not None else "N/A")

        r1, r2 = st.columns(2)
        with r1:
            st.markdown('<div class="mini-card"><div class="kicker">False Alerts</div><div class="copy">False positives can increase unnecessary review burden and distract analysts from genuinely urgent content.</div></div>', unsafe_allow_html=True)
        with r2:
            st.markdown('<div class="mini-card"><div class="kicker">Missed Emergencies</div><div class="copy">False negatives are operationally important because a genuine emergency-related message may not be prioritised.</div></div>', unsafe_allow_html=True)
    else:
        st.caption("Confusion-matrix counts were not included in ui_config.json.")


with tab_reliability:
    st.markdown('<div class="section">Reliability & Limitations</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="feature-story"><div>{visual_svg("reliability")}</div><div><h4>Human review remains part of the system</h4><p>Model output can support prioritisation, but social-media language is noisy and real emergencies are context-dependent. Reliability therefore depends on model evidence, operational context and appropriate human judgement working together.</p></div></div>',
        unsafe_allow_html=True
    )
    st.caption("Use this section to interpret where model outputs may be less reliable and why human review remains necessary.")

    risk_items = [
        ("Ambiguous language", "Sarcasm, metaphor, incomplete context and rapidly evolving language can change the meaning of a tweet."),
        ("False alerts", "A non-disaster message may be classified as disaster-related, increasing unnecessary review workload."),
        ("Missed emergencies", "A real disaster message may be classified as non-disaster and therefore fail to receive priority."),
        ("Distribution shift", "Future disasters, slang and posting behaviour may differ from the original training distribution."),
        ("Context limits", "Text-only classification may miss location, timing, source credibility and real-world event context."),
        ("Decision support", "The system should support human prioritisation rather than act as an autonomous emergency authority.")
    ]

    for start in range(0, len(risk_items), 3):
        cols = st.columns(3)
        for col, (title, copy) in zip(cols, risk_items[start:start+3]):
            with col:
                st.markdown(
                    f'<div class="risk-card"><b>{title}</b><p>{copy}</p></div>',
                    unsafe_allow_html=True
                )

    st.markdown('<div class="subsection">Interactive Risk Explorer</div>', unsafe_allow_html=True)
    risk_detail_map = {
        "False alerts": ("What can happen", "Ordinary or figurative language may be flagged as disaster-related.", "Operational response", "Use contextual review and avoid treating a single model output as an official alert."),
        "Missed emergencies": ("What can happen", "A genuine emergency-related message may receive a non-disaster label.", "Operational response", "Preserve human escalation paths and monitor recall-sensitive errors during governed evaluation."),
        "Ambiguous language": ("What can happen", "Sarcasm, metaphor, local slang or incomplete context can change meaning.", "Operational response", "Inspect the original text and surrounding context rather than relying on the label alone."),
        "Distribution shift": ("What can happen", "Future language or disaster patterns may differ from the training distribution.", "Operational response", "Track production behaviour and retrain only through a separate governed model-development cycle."),
        "Deployment parity": ("What can happen", "Differences in preprocessing or serving can make production behaviour diverge from validation.", "Operational response", "Keep Flask as the inference boundary and retain parity, health and evidence checks.")
    }
    selected_risk = st.selectbox("Choose a reliability risk to inspect", list(risk_detail_map.keys()))
    h1, c1, h2, c2 = risk_detail_map[selected_risk]
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        st.markdown(f'<div class="mini-card"><div class="kicker">{h1}</div><div class="copy">{c1}</div></div>', unsafe_allow_html=True)
    with rcol2:
        st.markdown(f'<div class="mini-card"><div class="kicker">{h2}</div><div class="copy">{c2}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="subsection">Saved Robustness Evidence</div>', unsafe_allow_html=True)
    evidence_specs = [
        ("Robustness evidence", ASSETS_DIR / "robustness_summary.csv", "robustness"),
        ("Slice analysis", ASSETS_DIR / "slice_summary.csv", "slice")
    ]

    evidence_found = False
    for title, path, key_prefix in evidence_specs:
        if path.exists():
            evidence_found = True
            with st.expander(title, expanded=False):
                try:
                    evidence_df = pd.read_csv(path)
                    st.caption(f"{len(evidence_df):,} row(s) · {len(evidence_df.columns)} column(s)")
                    st.dataframe(evidence_df.head(100), width="stretch", hide_index=True)
                    generic_numeric_view(evidence_df, key_prefix)
                    st.download_button(
                        f"Download {title.lower()} CSV",
                        evidence_df.to_csv(index=False).encode(),
                        path.name,
                        "text/csv",
                        key=f"download_{key_prefix}",
                        width="stretch"
                    )
                except Exception as exc:
                    st.warning(f"Could not read {path.name}: {exc}")

    if not evidence_found:
        st.info("No robustness_summary.csv or slice_summary.csv file was found in ui_assets. The application does not fabricate robustness evidence.")


with tab_system:
    st.markdown('<div class="section">System Diagnostics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="arch-flow">Validated Inference Architecture</div>',
        unsafe_allow_html=True
    )
    st.markdown("""<div class="arch-grid">
    <div class="arch-card"><div class="a-icon">◫</div><b>Streamlit UI</b><p>Collects input, shows diagnostics and renders evidence.</p></div>
    <div class="arch-card"><div class="a-icon">⇢</div><b>Flask API</b><p>Owns the validated /health and /predict inference contract.</p></div>
    <div class="arch-card"><div class="a-icon">◆</div><b>Locked Pipeline</b><p>Applies the production preprocessing and trained classifier.</p></div>
    <div class="arch-card"><div class="a-icon">✓</div><b>Evidence Layer</b><p>Retains QA, parity and interface evidence without tuning the model.</p></div>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Backend", "ONLINE" if online else "OFFLINE")
    c2.metric("Health Latency", health_latency_text)
    c3.metric("API Endpoint", API_URL.replace("http://", "").replace("https://", ""))
    c4.metric("Max Input", f"{MAX_CHARS:,} chars")

    system_tab1, system_tab2, system_tab3 = st.tabs(["Health Response", "Environment", "Smoke Test"])

    with system_tab1:
        if online:
            st.json(health_data)
        else:
            st.warning("The Flask health endpoint is not currently reachable.")
        st.caption("Health information is retrieved from the backend and is not inferred by the UI.")

    with system_tab2:
        environment_df = pd.DataFrame(
            [
                ["Application", CONFIG.get("app_name")],
                ["Streamlit file", str(BASE_DIR / "streamlit_app.py")],
                ["Python", platform.python_version()],
                ["Platform", platform.platform()],
                ["Model", CONFIG.get("model_name")],
                ["Model version", health_data.get("model_version", CONFIG.get("model_version"))],
                ["Feature configuration", CONFIG.get("feature_id")],
                ["Evaluation dataset", CONFIG.get("evaluation_dataset")],
                ["Backend URL", API_URL],
                ["UI config", str(CONFIG_PATH)],
                ["UI assets", str(ASSETS_DIR)]
            ],
            columns=["Item", "Value"]
        )
        st.dataframe(environment_df, width="stretch", hide_index=True)

        asset_rows = []
        for label, path in [
            ("UI config", CONFIG_PATH),
            ("Robustness summary", ASSETS_DIR / "robustness_summary.csv"),
            ("Slice summary", ASSETS_DIR / "slice_summary.csv"),
            ("Screenshot folder", SCREENSHOT_DIR)
        ]:
            asset_rows.append({"Asset": label, "Available": path.exists(), "Path": str(path)})
        st.dataframe(pd.DataFrame(asset_rows), width="stretch", hide_index=True)

    with system_tab3:
        st.caption("A smoke test sends fixed example messages through the same `/predict` endpoint. It does not modify the model and is not added to your session history.")
        if st.button("Run API Smoke Test", width="stretch", disabled=not online):
            smoke_examples = [
                ("Emergency-style", "Emergency crews are responding after severe flooding trapped residents."),
                ("Ordinary-style", "Meeting friends for lunch after work today.")
            ]
            smoke_rows = []
            with st.spinner("Running API smoke test..."):
                for name, text in smoke_examples:
                    try:
                        result, latency = predict(text)
                        _, label = result_label(result)
                        smoke_rows.append({
                            "Case": name,
                            "Prediction": label,
                            "Score": result.get("score"),
                            "Score Type": result.get("score_type", "Class Only"),
                            "Latency ms": round(latency, 2),
                            "Status": "PASS"
                        })
                    except Exception as exc:
                        smoke_rows.append({
                            "Case": name,
                            "Prediction": "Unavailable",
                            "Score": None,
                            "Score Type": None,
                            "Latency ms": None,
                            "Status": f"ERROR: {exc}"
                        })
            st.dataframe(pd.DataFrame(smoke_rows), width="stretch", hide_index=True)


with tab_evidence:
    st.markdown('<div class="section">Automatic UI Evidence</div>', unsafe_allow_html=True)
    st.caption("A fresh normal Streamlit session automatically captures a multi-tab screenshot set through a hidden Playwright browser. The hidden capture session uses `capture_mode=1` to prevent recursive screenshots.")

    if CAPTURE_MODE:
        st.info("Evidence capture mode is active for this hidden rendering session.")
    else:
        if "_automatic_screenshot_done" not in st.session_state:
            st.session_state["_automatic_screenshot_done"] = True
            with st.spinner("Capturing automatic multi-tab UI evidence..."):
                st.session_state["_automatic_screenshot_result"] = capture_streamlit_screenshots()

        screenshot_result = st.session_state.get("_automatic_screenshot_result", {})

        e1, e2, e3, e4 = st.columns(4)
        created = screenshot_result.get("created", []) if screenshot_result else []
        latest_screenshot = SCREENSHOT_DIR / "latest_streamlit.png"
        evidence_files = sorted(
            [
                p for p in SCREENSHOT_DIR.glob("streamlit_*.png")
                if p.name != "latest_streamlit.png"
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        e1.metric("Capture Status", "PASS" if screenshot_result.get("success") else "REVIEW")
        e2.metric("New Screenshots", len(created))
        e3.metric("Evidence Images", len(evidence_files))
        e4.metric("Latest Available", "YES" if latest_screenshot.exists() else "NO")

        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("Recapture Evidence Now", width="stretch"):
                with st.spinner("Recapturing multi-tab UI evidence..."):
                    st.session_state["_automatic_screenshot_result"] = capture_streamlit_screenshots()
                st.rerun()
        with button_col2:
            if latest_screenshot.exists():
                st.download_button(
                    "Download Latest Screenshot",
                    latest_screenshot.read_bytes(),
                    "latest_streamlit.png",
                    "image/png",
                    width="stretch"
                )

        if screenshot_result.get("success") and latest_screenshot.exists():
            st.success("Automatic interface evidence is available.")

            gallery_files = created if created else evidence_files[:6]
            gallery_files = [Path(x) for x in gallery_files if Path(x).exists()]
            if gallery_files:
                selected_file = st.selectbox(
                    "Preview captured view",
                    gallery_files,
                    format_func=lambda p: Path(p).name
                )
                st.image(
                    str(selected_file),
                    caption=Path(selected_file).name,
                    use_container_width=True
                )

            with st.expander("Evidence metadata"):
                summary = screenshot_summary()
                if summary:
                    st.json(summary)
                else:
                    st.caption("Screenshot metadata file is not available yet.")
                if screenshot_result.get("errors"):
                    st.warning("Some optional tab captures reported issues:")
                    for item in screenshot_result["errors"]:
                        st.caption(item)
        else:
            st.warning(screenshot_result.get("message", "Automatic screenshot evidence is not available."))
            st.info("One-time setup: `pip install playwright` then `python -m playwright install chromium`.")

st.markdown(
    f'<div class="info" style="margin-top:26px"><b>Responsible-use statement:</b> {CONFIG.get("disclaimer", "")}</div>',
    unsafe_allow_html=True
)
st.markdown(
    f'<div class="premium-footer"><div><b>{CONFIG.get("app_name", "Disaster Tweet Intelligence")}</b><br><span>Validated NLP decision support · Flask inference · human review · reproducible evidence</span></div><div><span>Model {health_data.get("model_version", CONFIG.get("model_version", "unknown"))} · {"API Online" if online else "API Offline"}</span></div></div>',
    unsafe_allow_html=True
)