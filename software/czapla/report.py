"""Incident report generator — Polish, one page, for a site's protection file.

Does:
    Renders a detection incident as a Polish-language report a security officer can
    read and file: what was detected, when, where, with what confidence, what the
    operator did, and what the system did NOT do.

Does NOT do:
    Draw any legal conclusion. The report states facts and records decisions taken
    by people. It must never suggest the system authorised a countermeasure.
"""

from __future__ import annotations

from datetime import datetime, timezone

DISCLAIMER_PL = (
    "System CZAPLA prowadzi wyłącznie pasywną detekcję i rejestrację zdarzeń. "
    "Nie transmituje, nie zakłóca i nie neutralizuje żadnych obiektów. "
    "Decyzję o jakichkolwiek działaniach wobec bezzałogowego statku powietrznego "
    "podejmuje człowiek, na podstawie obowiązujących przepisów "
    "(w szczególności art. 156ze Prawa lotniczego)."
)

LIMITATIONS_PL = (
    "Ograniczenia pomiaru: detekcja radiowa widzi wyłącznie drony posiadające "
    "aktywne łącze radiowe. Drony sterowane światłowodem nie emitują sygnału "
    "radiowego i nie są wykrywane. Namiar wskazuje kierunek, a nie dokładną "
    "pozycję; pozycja wymaga jednoczesnej detekcji z co najmniej dwóch węzłów."
)


def _fmt_ts(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return value


def _fmt(value, unit: str = "", digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}{unit}"
    return f"{value}{unit}"


def render_report_html(event: dict, position: dict | None = None) -> str:
    """One-page Polish incident report as standalone HTML (printable to PDF)."""
    freq_mhz = event.get("freq_hz", 0) / 1e6
    classification = {
        "drone_like": "dronopodobny",
        "unknown": "nierozpoznany",
        "other": "inne źródło",
    }.get(event.get("classification", ""), str(event.get("classification")))

    position_row = ""
    if position:
        position_row = f"""
        <tr><th>Pozycja (triangulacja)</th>
            <td>{_fmt(position.get('lat'), '', 6)}, {_fmt(position.get('lon'), '', 6)}
            &nbsp;±&nbsp;{_fmt(position.get('cep_m'), ' m', 0)} (szacunek)</td></tr>
        <tr><th>Węzły potwierdzające</th>
            <td>{', '.join(position.get('sources', [])) or '—'}</td></tr>
        <tr><th>Pewność pozycji</th>
            <td>{_fmt(position.get('confidence'))}</td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>Raport incydentu — {event.get('event_id', '')}</title>
<style>
  body {{ font-family: system-ui, "Segoe UI", Arial, sans-serif; margin: 32px; color: #111; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ color: #555; font-size: 13px; margin-bottom: 20px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
  th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid #ddd; vertical-align: top; }}
  th {{ width: 34%; font-weight: 600; background: #f7f7f7; }}
  .note {{ margin-top: 22px; padding: 12px 14px; background: #fff8e1; border-left: 4px solid #e0a800; font-size: 13px; }}
  .lim {{ margin-top: 12px; padding: 12px 14px; background: #eef4fb; border-left: 4px solid #4a7fb5; font-size: 13px; }}
  .sig {{ margin-top: 34px; font-size: 13px; color: #333; }}
  .line {{ border-bottom: 1px solid #333; display: inline-block; width: 260px; }}
</style>
</head>
<body>
  <h1>Raport incydentu — naruszenie przestrzeni powietrznej</h1>
  <div class="sub">Wygenerowano automatycznie przez system CZAPLA. Dokument do akt ochrony obiektu.</div>

  <table>
    <tr><th>Identyfikator zdarzenia</th><td>{event.get('event_id', '—')}</td></tr>
    <tr><th>Data i godzina (UTC)</th><td>{_fmt_ts(event.get('ts_utc'))}</td></tr>
    <tr><th>Węzeł wykrywający</th><td>{event.get('node_id', '—')}</td></tr>
    <tr><th>Częstotliwość</th><td>{_fmt(freq_mhz, ' MHz', 2)}</td></tr>
    <tr><th>Szerokość zajęta</th><td>{_fmt((event.get('width_hz') or 0) / 1e6, ' MHz', 2)}</td></tr>
    <tr><th>Poziom sygnału (SNR)</th><td>{_fmt(event.get('snr_db'), ' dB', 1)}</td></tr>
    <tr><th>Klasyfikacja</th><td>{classification}</td></tr>
    <tr><th>Pewność klasyfikacji</th><td>{_fmt(event.get('confidence'))} (szacunek)</td></tr>
    <tr><th>Namiar</th><td>{_fmt(event.get('bearing_deg'), '°', 1)}
        &nbsp;±&nbsp;{_fmt(event.get('bearing_sigma_deg'), '°', 1)} (szacunek)</td></tr>
    {position_row}
    <tr><th>Materiał dowodowy</th><td>{', '.join((event.get('evidence') or {}).values()) or 'brak'}</td></tr>
    <tr><th>Operator / potwierdzenie</th><td>{'potwierdzone' if (position or {}).get('acknowledged') else 'niepotwierdzone'}</td></tr>
  </table>

  <div class="note"><strong>Uwaga prawna.</strong> {DISCLAIMER_PL}</div>
  <div class="lim"><strong>Ograniczenia pomiaru.</strong> {LIMITATIONS_PL}</div>

  <div class="sig">
    Zdarzenie zgłosił (imię, nazwisko, stanowisko):<br><br>
    <span class="line"></span><br><br>
    Data i podpis: <span class="line"></span>
  </div>
</body>
</html>"""


def render_report_text(event: dict, position: dict | None = None) -> str:
    """Plain-text version of the same report, for logs and email."""
    freq_mhz = event.get("freq_hz", 0) / 1e6
    lines = [
        "RAPORT INCYDENTU — naruszenie przestrzeni powietrznej",
        f"Identyfikator zdarzenia: {event.get('event_id', '—')}",
        f"Data i godzina (UTC):     {_fmt_ts(event.get('ts_utc'))}",
        f"Węzeł:                    {event.get('node_id', '—')}",
        f"Częstotliwość:            {_fmt(freq_mhz, ' MHz', 2)}",
        f"SNR:                      {_fmt(event.get('snr_db'), ' dB', 1)}",
        f"Klasyfikacja:             {event.get('classification', '—')}",
        f"Pewność:                  {_fmt(event.get('confidence'))} (szacunek)",
        f"Namiar:                   {_fmt(event.get('bearing_deg'), '°', 1)}"
        f" ± {_fmt(event.get('bearing_sigma_deg'), '°', 1)}",
    ]
    if position:
        lines.append(
            f"Pozycja:                  {position.get('lat')}, {position.get('lon')}"
            f" ± {position.get('cep_m')} m (szacunek)"
        )
        lines.append(f"Węzły:                    {', '.join(position.get('sources', []))}")
    lines += ["", f"UWAGA PRAWNA: {DISCLAIMER_PL}", "", f"OGRANICZENIA: {LIMITATIONS_PL}"]
    return "\n".join(lines)


def report_filename(event: dict) -> str:
    ts = (event.get("ts_utc") or "").replace(":", "").replace("-", "")[:15]
    return f"raport-{ts}-{event.get('node_id', 'node')}.html"
