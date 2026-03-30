"""Load CSV/Excel cost inputs with tolerant column detection."""
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Optional, Union

import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
_DOWNLOADS = Path.home() / "Downloads"


def _pick_first_existing(*candidates: Path) -> Optional[Path]:
    for p in candidates:
        if p.exists():
            return p
    return None


def default_input_paths() -> tuple[Path, Path, Path]:
    """Prefer bundled data/ for reproducible demos, then ~/Downloads."""
    w = _pick_first_existing(
        DEFAULT_DATA_DIR / "wireless_costs.xlsx",
        DEFAULT_DATA_DIR / "wireless_costs.csv",
        _DOWNLOADS / "wireless_costs.xlsx",
        _DOWNLOADS / "wireless_costs.xls",
    )
    f = _pick_first_existing(
        DEFAULT_DATA_DIR / "fiber_costs.xlsx",
        DEFAULT_DATA_DIR / "fiber_costs.csv",
        _DOWNLOADS / "fiber_costs.xlsx",
        _DOWNLOADS / "fiber_costs.xls",
    )
    b = _pick_first_existing(
        DEFAULT_DATA_DIR / "benchmarks.xlsx",
        DEFAULT_DATA_DIR / "benchmarks.csv",
        _DOWNLOADS / "benchmarks.xlsx",
        _DOWNLOADS / "benchmarks.xls",
    )
    if not all([w, f, b]):
        raise FileNotFoundError(
            "Could not locate wireless, fiber, and benchmark files. "
            f"Place them under {DEFAULT_DATA_DIR} or ~/Downloads."
        )
    return w, f, b


def _read_table(path: Union[str, Path]) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    suf = path.suffix.lower()
    if suf in (".xlsx", ".xlsm"):
        return pd.read_excel(path, engine="openpyxl")
    if suf == ".xls":
        return pd.read_excel(path)
    if suf == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported format: {path}")


def load_workbook(path: Union[str, Path], **kwargs) -> pd.DataFrame:
    """Load a single sheet; forwards kwargs to pandas."""
    df = _read_table(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_wireless(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    p = Path(path) if path else DEFAULT_DATA_DIR / "wireless_costs.xlsx"
    if not p.exists():
        alt = DEFAULT_DATA_DIR / "wireless_costs.csv"
        if alt.exists():
            p = alt
    return load_workbook(p)


def load_fiber(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    p = Path(path) if path else DEFAULT_DATA_DIR / "fiber_costs.xlsx"
    if not p.exists():
        alt = DEFAULT_DATA_DIR / "fiber_costs.csv"
        if alt.exists():
            p = alt
    return load_workbook(p)


def load_benchmarks(path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    p = Path(path) if path else DEFAULT_DATA_DIR / "benchmarks.xlsx"
    if not p.exists():
        alt = DEFAULT_DATA_DIR / "benchmarks.csv"
        if alt.exists():
            p = alt
    return load_workbook(p)


def load_uploaded_file(
    uploaded: BinaryIO, name: str, default_name: str = "upload"
) -> pd.DataFrame:
    """Streamlit UploadedFile-compatible loader."""
    import io

    raw_name = name or default_name
    suf = Path(raw_name).suffix.lower()
    bio = io.BytesIO(uploaded.read())
    if suf == ".csv":
        df = pd.read_csv(bio)
    else:
        df = pd.read_excel(bio, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def resolve_default_paths(
    wireless: Optional[str] = None,
    fiber: Optional[str] = None,
    benchmarks: Optional[str] = None,
) -> tuple[Path, Path, Path]:
    """Return paths: explicit args override; else Downloads then bundled data/."""
    if wireless and fiber and benchmarks:
        w, f, b = Path(wireless), Path(fiber), Path(benchmarks)
    else:
        w, f, b = default_input_paths()
        if wireless:
            w = Path(wireless)
        if fiber:
            f = Path(fiber)
        if benchmarks:
            b = Path(benchmarks)
    for label, p in ("wireless", w), ("fiber", f), ("benchmarks", b):
        if not p.exists():
            raise FileNotFoundError(f"Missing {label} data file: {p}")
    return w, f, b


def load_default_dataframes() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Bundled or Downloads paths → three dataframes for the guided app."""
    w_path, f_path, b_path = resolve_default_paths()
    return load_workbook(w_path), load_workbook(f_path), load_benchmarks(b_path)
