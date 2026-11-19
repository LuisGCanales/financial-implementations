# MXMC Calendar Data and Coverage

The F-TIIE OIS contract uses the **Mexico City (MXMC)** business-day calendar for effective dates, coupon boundaries, fixing observations, and payment lags. Calendar accuracy matters because adjustments can change accrual fractions, compounded coupons, cash-flow dates, and the resulting calibration pillars.

CME identifies MXMC as the market-standard calendar family for spot-starting F-TIIE OIS [S2-equivalent source below], but its published instrument-attribute document does not itself supply a complete, date-by-date copy of the underlying CME holiday dataset.

## Sourced 2026 holiday mapping

[`mxmc_2026.csv`](mxmc_2026.csv) is the project's explicit **2026 financial-sector holiday mapping**. Its closure dates are based on the Comisión Nacional Bancaria y de Valores (CNBV) financial-sector calendar and were cross-checked against the 2026 Grupo BMV holiday calendar.

This means the project can reproduce date calculations from a frozen, inspectable file. It **does not** mean the file is certified as an exact copy of CME Clearing's internal MXMC data.

A published CME example also treats **16 September 2026** as an MXMC holiday, with **15 September** and **17 September** as the surrounding business days. This agrees with the project's 2026 mapping.

## File structure and loading

The sourced CSV has three columns:

| Column | Meaning |
|---|---|
| `date` | ISO `YYYY-MM-DD` holiday date |
| `name` | Human-readable description |
| `source` | Source identifier, e.g. `CNBV_2026` |

For example:

```csv
date,name,source
2026-01-01,New Year's Day,CNBV_2026
2026-02-02,Constitution Day Observance,CNBV_2026
2026-09-16,Independence Day,CNBV_2026
```

The loader requires the `date` column; `name` and `source` are descriptive. Saturday and Sunday are handled by the calendar's weekend-day definition, so they need not be listed as holiday rows.

To construct the calendar from the provided file:

```python
from datetime import date
from yield_curves.calendar_io import build_mxmc_calendar_from_csv

calendar = build_mxmc_calendar_from_csv(
    "data/calendars/mxmc_2026.csv",
    coverage_start=date(2026, 1, 1),
    coverage_end=date(2026, 12, 31),
    source="CNBV/BMV-based project holiday mapping for 2026",
)
```

The calendar records a `PROVIDED` source declaration and file fingerprint. The declaration is **not** source certification; users remain responsible for the suitability of supplied holidays.

## Long-horizon research calendar

OIS maturities spanning decades require holiday information well beyond the verified 2026 file. For **controlled synthetic experiments**, the project provides a deterministic rule-based projection of recurring Mexican financial-sector holidays:

```python
from yield_curves.research.calendars import build_projected_mxmc_calendar

calendar = build_projected_mxmc_calendar(
    start_year=2026,
    end_year=2057,
)
```

This model carries `PROJECTED` provenance and a declared full-year range. Its future-year dates are **project assumptions**, not official CNBV, BMV, or CME holiday observations. It should not be silently substituted for a verified market calendar when calibrating observed market quotations.

## Coverage and financial consequences

Coverage boundaries are **inclusive and explicitly declared**. The first and last holiday rows do not define those boundaries: many covered dates are ordinary business days.

A calendar used by the standard baseline must cover all required schedule operations, including adjustments, overnight observation dates, and **payment lags past contractual maturities**. The project raises `CalendarCoverageError` for uncovered dates rather than using implicit extrapolation or assuming that future holidays are known.

This distinction matters particularly for long-dated OIS: a curve may have a supported calibration maturity while the supplied calendar lacks the dates necessary to determine its last cash flows.

[Input contract](../../docs/input_contract.md) · [Financial conventions](../../docs/conventions.md) · [Calendar and projected-holiday implementations](../../src/yield_curves/calendars.py)

## Sources

### CNBV — Financial-sector holidays for 2026

Official CNBV / Diario Oficial de la Federación publication:

[https://www.cnbv.gob.mx/Normatividad/Disposiciones%20de%20car%C3%A1cter%20general%20que%20se%C3%B1alan%20los%20d%C3%ADas%20del%20a%C3%B1o%202026%20en%20que%20las%20entidades%20financieras%20sujetas%20a%20la%20supervisi%C3%B3n%20de%20la%20Comisi%C3%B3n%20Nacional%20Bancaria%20y%20de%20Valores%20deber%C3%A1n%20cerrar%20sus%20puertas%20y%20suspender%20operaciones.pdf](https://www.cnbv.gob.mx/Normatividad/Disposiciones%20de%20car%C3%A1cter%20general%20que%20se%C3%B1alan%20los%20d%C3%ADas%20del%20a%C3%B1o%202026%20en%20que%20las%20entidades%20financieras%20sujetas%20a%20la%20supervisi%C3%B3n%20de%20la%20Comisi%C3%B3n%20Nacional%20Bancaria%20y%20de%20Valores%20deber%C3%A1n%20cerrar%20sus%20puertas%20y%20suspender%20operaciones.pdf)

### Grupo BMV — Calendario de días festivos

[https://www.bmv.com.mx/es/Grupo_BMV/Calendario_de_dias_festivos/_rid/662/_mod/TAB_DIAS_FEST](https://www.bmv.com.mx/es/Grupo_BMV/Calendario_de_dias_festivos/_rid/662/_mod/TAB_DIAS_FEST)

### CME — MXN F-TIIE OIS Market Standard Attributes

[https://www.cmegroup.com/articles/files/2024/f-tiie-ois-market-standard-attributes.pdf](https://www.cmegroup.com/articles/files/2024/f-tiie-ois-market-standard-attributes.pdf)

### CME — Conversion Pricing for Cleared MXN 28D TIIE Swaps

[https://www.cmegroup.com/articles/files/2024/mxn-pricing.pdf](https://www.cmegroup.com/articles/files/2024/mxn-pricing.pdf)
