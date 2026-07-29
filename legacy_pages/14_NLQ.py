"""
14_NLQ.py — Natural Language Query for ArchiShield
─────────────────────────────────────────────────────────────────────────────
Ask plain-English questions about your uploaded IFC model.
Groq (Llama 3.3 70B) reads a structured summary of the model + the user's
question and answers directly — grounded in the actual scanned data, not guesses.
"""
import streamlit as st
import ifcopenshell
import json
import os

from theme import apply_theme, get_theme
def _get_groq_key() -> str:
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        return key
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return ""

st.set_page_config(page_title="ArchiShield — Ask Your Model", page_icon="💬", layout="wide")
_t = apply_theme()

# ── Auth / data guards ──────────────────────────────────────────────────────────
if not st.session_state.get("logged_in"):
    st.warning("Please log in from the Home page first.")
    st.stop()

an = st.session_state.get("analysis", {})
if not an:
    st.warning("No analysis data. Please upload an IFC file on the Home page first.")
    st.stop()

try:
    model = ifcopenshell.open("temp.ifc")
except Exception:
    st.warning("No IFC file found. Please upload on the Home page first.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("💬 Ask Your Model")
st.caption(
    "Type a question in plain English — ArchiShield reads your uploaded IFC file "
    "and answers using the actual scanned data."
)

with st.expander("💡 Example questions you can ask"):
    st.markdown("""
- *How many proxy elements are on floor 2?*
- *Which walls are missing fire rating?*
- *What is the overall quality score and why?*
- *List all doors that have no Pset_DoorCommon.*
- *Which floor has the most issues?*
- *Is this model ready for NBC 2016 compliance?*
- *Summarise the biggest problems in this model.*
""")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# BUILD A COMPACT, ACCURATE MODEL SUMMARY FOR CLAUDE
# This re-scans the live IFC file so answers are grounded in real data,
# not just the cached analysis dict (which may be summarised/capped).
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def build_model_context(_cache_key: str) -> dict:
    SKIP_TYPES = {
        "IfcSpace", "IfcOpeningElement", "IfcVirtualElement", "IfcAnnotation",
        "IfcGrid", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcProject",
        "IfcRelAggregates", "IfcZone", "IfcSpatialZone",
    }
    PSET_MAP = {
        "IfcWall": "Pset_WallCommon", "IfcWallStandardCase": "Pset_WallCommon",
        "IfcDoor": "Pset_DoorCommon", "IfcWindow": "Pset_WindowCommon",
        "IfcSlab": "Pset_SlabCommon", "IfcColumn": "Pset_ColumnCommon",
        "IfcBeam": "Pset_BeamCommon", "IfcRoof": "Pset_RoofCommon",
        "IfcStair": "Pset_StairCommon", "IfcRailing": "Pset_RailingCommon",
    }

    m = ifcopenshell.open("temp.ifc")

    # ── Per-storey breakdown ────────────────────────────────────────────────────
    storeys = []
    for storey in m.by_type("IfcBuildingStorey"):
        sname = storey.Name or "Unnamed Storey"
        elems_in = []
        for rel in getattr(storey, "ContainsElements", []):
            if rel.is_a("IfcRelContainedInSpatialStructure"):
                elems_in.extend(rel.RelatedElements)
        s_total = len(elems_in)
        s_proxies = sum(1 for e in elems_in if e.is_a("IfcBuildingElementProxy"))
        storeys.append({
            "name": sname,
            "total_elements": s_total,
            "proxy_elements": s_proxies,
        })

    # ── Element type counts ─────────────────────────────────────────────────────
    type_counts = {}
    elements_detail = []
    for elem in m.by_type("IfcProduct"):
        etype = elem.is_a()
        if etype in SKIP_TYPES:
            continue
        type_counts[etype] = type_counts.get(etype, 0) + 1

        # Check Pset for elements that have a required one
        req_pset = PSET_MAP.get(etype)
        has_pset = None
        if req_pset:
            has_pset = False
            for d in getattr(elem, "IsDefinedBy", []):
                if d.is_a("IfcRelDefinesByProperties"):
                    ps = d.RelatingPropertyDefinition
                    if ps and ps.is_a("IfcPropertySet") and ps.Name == req_pset:
                        has_pset = True
                        break

        # Check FireRating specifically for walls (common compliance question)
        fire_rating = None
        if etype in ("IfcWall", "IfcWallStandardCase"):
            fire_rating = False
            for d in getattr(elem, "IsDefinedBy", []):
                if d.is_a("IfcRelDefinesByProperties"):
                    ps = d.RelatingPropertyDefinition
                    if ps and ps.is_a("IfcPropertySet") and ps.Name == "Pset_WallCommon":
                        for p in getattr(ps, "HasProperties", []):
                            if p.Name == "FireRating":
                                fire_rating = True
                                break

        # Find which storey this element belongs to
        storey_name = None
        for rel in getattr(elem, "ContainedInStructure", []):
            if rel.is_a("IfcRelContainedInSpatialStructure"):
                rs = getattr(rel, "RelatingStructure", None)
                if rs and rs.is_a("IfcBuildingStorey"):
                    storey_name = rs.Name or "Unnamed Storey"

        elements_detail.append({
            k: v for k, v in {
                "name": elem.Name or "Unnamed",
                "type": etype,
                "storey": storey_name,
                "missing_pset": (has_pset is False) or None,
                "missing_fire_rating": (fire_rating is False) or None,
            }.items() if v is not None
        })

    # Prioritise elements with issues (missing pset / fire rating / proxy type)
    # over arbitrary ordering — gives Groq the most relevant data within budget.
    flagged    = [e for e in elements_detail if e.get("missing_pset") or e.get("missing_fire_rating") or e["type"] == "IfcBuildingElementProxy"]
    unflagged  = [e for e in elements_detail if e not in flagged]
    prioritised = (flagged + unflagged)[:40]

    return {
        "total_elements": an.get("total_elements", 0),
        "proxy_elements": an.get("proxy_elements", 0),
        "proxy_pct": an.get("proxy_pct", 0),
        "semantic_elements": an.get("semantic_elements", 0),
        "quality_score": an.get("quality_score", 0),
        "severity": an.get("severity", "LOW"),
        "type_loss_pct": an.get("type_loss_pct", an.get("proxy_pct", 0)),
        "prop_loss_pct": an.get("prop_loss_pct", 0),
        "qty_loss_pct": an.get("qty_loss_pct", 0),
        "rel_loss_pct": an.get("rel_loss_pct", 0),
        "geo_loss_pct": an.get("geo_loss_pct", 0),
        "missing_pset_count": an.get("missing_pset_count", 0),
        "storeys": storeys,
        "type_counts": type_counts,
        "elements_detail": prioritised,  # small, issue-prioritised cap — fits free-tier TPM limit
        "elements_detail_total": len(elements_detail),
    }


_cache_key = st.session_state.get("last_file_id", "default")
with st.spinner("Reading model data..."):
    context = build_model_context(_cache_key)

# ══════════════════════════════════════════════════════════════════════════════
# QUERY INPUT
# ══════════════════════════════════════════════════════════════════════════════
if "nlq_history" not in st.session_state:
    st.session_state.nlq_history = []

query = st.text_input(
    "Your question",
    placeholder="e.g. How many proxy elements are on floor 2?",
    label_visibility="collapsed",
    key="nlq_query_input",
)

col1, col2, col3 = st.columns([1, 1, 4])
ask_clicked = col1.button("🔍 Ask", use_container_width=True, type="primary")

with col2:
    import streamlit.components.v1 as components
    components.html(
        """
<div style="display:flex;align-items:center;justify-content:center;height:38px;">
  <button id="voice-btn" style="
      background:#161b22; border:1px solid #58a6ff60; border-radius:6px;
      color:#e6edf3; width:100%; height:38px; cursor:pointer;
      font-size:16px; transition:all 0.2s ease;">
    🎤
  </button>
</div>
<script>
(function() {
  const btn = document.getElementById('voice-btn');
  let recognizing = false;
  let recognition = null;

  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    btn.innerHTML = '🎤 N/A';
    btn.disabled = true;
    btn.title = 'Voice input not supported in this browser — try Chrome or Edge';
    btn.style.opacity = '0.5';
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onstart = function() {
    recognizing = true;
    btn.style.background = '#da3633';
    btn.style.borderColor = '#da3633';
    btn.innerHTML = '🔴';
  };

  recognition.onend = function() {
    recognizing = false;
    btn.style.background = '#161b22';
    btn.style.borderColor = '#58a6ff60';
    btn.innerHTML = '🎤';
  };

  recognition.onerror = function(event) {
    recognizing = false;
    btn.style.background = '#161b22';
    btn.style.borderColor = '#58a6ff60';
    btn.innerHTML = '🎤';
    console.error('Speech recognition error:', event.error);
  };

  recognition.onresult = function(event) {
    const transcript = event.results[0][0].transcript;
    // Find the Streamlit text input in the PARENT document (outside this iframe)
    const parentDoc = window.parent.document;
    const inputs = parentDoc.querySelectorAll('input[type="text"]');
    for (const inp of inputs) {
      if (inp.placeholder && inp.placeholder.includes('proxy elements')) {
        inp.value = transcript;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        // React-controlled inputs need this to register the change
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
          window.parent.HTMLInputElement.prototype, 'value'
        ).set;
        nativeInputValueSetter.call(inp, transcript);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.focus();
        break;
      }
    }
  };

  btn.addEventListener('click', function() {
    if (recognizing) {
      recognition.stop();
    } else {
      recognition.start();
    }
  });
})();
</script>
""",
        height=44,
    )

with col3:
    st.caption("🎤 Click the mic to speak your question (Chrome/Edge only)")



# ══════════════════════════════════════════════════════════════════════════════
# CLAUDE API CALL
# ══════════════════════════════════════════════════════════════════════════════
def ask_groq(question: str, model_context: dict) -> str:
    """Send the question + model context to Groq and return the answer text."""
    try:
        from groq import Groq
    except ImportError:
        return ("⚠️ The `groq` package is not installed. "
                "Run `pip install groq` in your environment.")

    api_key = _get_groq_key()
    if not api_key:
        return ("⚠️ No GROQ_API_KEY found in environment variables. "
                "Set it before using this page — see the setup note below.")

    client = Groq(api_key=api_key)

    # Build a compact JSON context — trimmed to keep token usage reasonable
    compact_context = {
        "total_elements": model_context["total_elements"],
        "proxy_elements": model_context["proxy_elements"],
        "proxy_pct": model_context["proxy_pct"],
        "semantic_elements": model_context["semantic_elements"],
        "quality_score": model_context["quality_score"],
        "severity": model_context["severity"],
        "data_loss_breakdown": {
            "L1_semantic_loss_pct":      model_context["type_loss_pct"],
            "L2_property_loss_pct":      model_context["prop_loss_pct"],
            "L3_quantity_loss_pct":      model_context["qty_loss_pct"],
            "L4_relationship_loss_pct":  model_context["rel_loss_pct"],
            "L5_geometry_loss_pct":      model_context["geo_loss_pct"],
        },
        "missing_pset_count": model_context["missing_pset_count"],
        "storeys": model_context["storeys"][:20],            # cap — large models can have many storeys
        "element_type_counts": dict(list(model_context["type_counts"].items())[:25]),  # cap distinct types
        "sample_elements": model_context["elements_detail"],
        "note": f"showing {len(model_context['elements_detail'])}/{model_context['elements_detail_total']} elements, issues first",
    }

    system_prompt = (
        "You are ArchiShield's model assistant. Answer using ONLY the JSON data below. "
        "Use real numbers from it. If data is insufficient, say so. "
        "Keep answers to 2-5 sentences plus bullets if helpful. "
        "Never invent names, counts, or properties not in the data.\n\n"
        f"DATA:\n{json.dumps(compact_context, ensure_ascii=False, separators=(',', ':'))}"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        err_str = str(e)
        if "413" in err_str or "too large" in err_str.lower() or "rate_limit" in err_str.lower():
            return ("⚠️ The model is too large for the free Groq tier's per-minute token limit. "
                     "Try asking a more specific question (e.g. about one floor or one element type) "
                     "rather than a broad summary request.")
        return f"⚠️ Groq API error: {e}"


if ask_clicked and query.strip():
    with st.spinner("Thinking..."):
        answer = ask_groq(query.strip(), context)
    st.session_state.nlq_history.insert(0, {"q": query.strip(), "a": answer})

# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY CONVERSATION HISTORY
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.nlq_history:
    st.markdown("---")
    for i, turn in enumerate(st.session_state.nlq_history):
        st.markdown(f"""
<div style="background:{_t['bg2']};border:1px solid {_t['primary_muted']};
border-radius:10px;padding:12px 16px;margin-bottom:8px;">
  <div style="font-size:11px;color:{_t['text_muted']};margin-bottom:4px;">YOU ASKED</div>
  <div style="font-size:14px;color:{_t['text']};font-weight:600;">{turn['q']}</div>
</div>
""", unsafe_allow_html=True)
        st.markdown(f"""
<div style="background:{_t['primary_dim']};border:1px solid {_t['primary_muted']};
border-radius:10px;padding:14px 18px;margin-bottom:20px;">
  <div style="font-size:11px;color:{_t['primary']};margin-bottom:6px;">💬 ARCHISHIELD</div>
  <div style="font-size:14px;color:{_t['text']};line-height:1.6;">{turn['a']}</div>
</div>
""", unsafe_allow_html=True)

    if st.button("🗑️ Clear conversation"):
        st.session_state.nlq_history = []
        st.rerun()
else:
    st.info("Ask your first question above to get started.")

# ══════════════════════════════════════════════════════════════════════════════
# SETUP NOTE (only shown if no API key detected)
# ══════════════════════════════════════════════════════════════════════════════
if not _get_groq_key():
    st.markdown("---")
    with st.expander("⚙️ Setup required — Groq API key"):
        st.markdown("""
To enable this page, set your Groq API key as an environment variable
before running Streamlit. Get a **free** API key at
[console.groq.com/keys](https://console.groq.com/keys) — no credit card needed.

**Windows (PowerShell):**
```
$env:GROQ_API_KEY = "your-key-here"
streamlit run Home.py
```

**Mac/Linux:**
```
export GROQ_API_KEY="your-key-here"
streamlit run Home.py
```

Or create a `.env` file and load it with `python-dotenv` at the top of `Home.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

Install the required package if you haven't already:
```
pip install groq
```
""")
