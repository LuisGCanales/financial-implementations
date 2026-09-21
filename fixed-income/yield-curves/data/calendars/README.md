# Calendar Data

## MXMC — Mexico City Calendar

The canonical MXN F-TIIE OIS specification references the:

> **Mexico City (MXMC)**

calendar.

CME identifies MXMC as the market-standard holiday calendar for
spot-starting MXN F-TIIE OIS.

However, the public market-standard-attributes document does not provide
the complete underlying holiday-date dataset inside the specification.

For reproducibility, this project maintains explicit frozen calendar data.

---

## 2026 Dataset

File:

```text
mxmc_2026.csv
```

The 2026 holiday set is based primarily on the official Mexican
financial-sector closure calendar published by the Comisión Nacional
Bancaria y de Valores (CNBV).

The dates were cross-checked against the 2026 Grupo BMV holiday calendar.

Both sources identify the same relevant 2026 financial-market closure
dates.

### Classification

```text
PROJECT DATA MAPPING
```

This means:

> The project uses the official Mexican financial-sector holiday calendar
> as its explicit implementation of MXMC for the covered year.

It does **not** mean:

> This CSV is claimed to be a copy of CME Clearing's internal MXMC
> calendar dataset.

The distinction is intentional.

---

## CME Cross-Check

CME published examples explicitly treat:

```text
2026-09-16
```

as an MXMC holiday, with:

```text
2026-09-15
```

as the previous business day and:

```text
2026-09-17
```

as the following business day.

This behavior is consistent with the project calendar dataset.

---

## Data Schema

```text
date
    ISO-8601 holiday date.

name
    Human-readable description.

source
    Identifier for the source used to establish the holiday.
```

Weekends are not required in the CSV because Saturday and Sunday are
handled structurally by `BusinessCalendar`.

A holiday that happens to fall on a weekend may remain in the source file
when the official source explicitly identifies it as a holiday.

---

## Coverage Policy

Calendar coverage must be explicit.

A calendar dataset covering 2026 must not silently be assumed to provide
correct holiday information for:

```text
2027
2030
2050
```

Future long-dated calibration requires either:

1. additional verified yearly calendar data; or
2. a separately specified rule-based calendar with explicit year-specific
   overrides and limitations.

The project should fail rather than silently assume that an incomplete
holiday dataset represents the full MXMC calendar.

---

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
