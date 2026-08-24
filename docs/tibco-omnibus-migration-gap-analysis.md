# TIBCO Monitoring Migration: Omnibus → Dynatrace
## File System Monitoring — KPI Coverage & Gap Analysis

**Prepared by:** Dynatrace  
**Audience:** TIBCO Migration Team  
**Status:** In Progress

---

## Executive Summary

Dynatrace **can satisfy all six file system KPIs** listed in scope. Coverage is split across three mechanisms depending on the KPI type: the built-in `com.dynatrace.filesystem` OneAgent Extension, a custom Extension Framework 2.0 (EF2) Python extension for richer metadata, and native OneAgent host monitoring. No gaps exist for file system monitoring — only a choice of implementation path.

The broader monitoring categories in the Excel (SNMP, Process Monitor, Disk Space) are addressed in the [Additional Coverage](#additional-coverage-snmp-process-disk-space) section below.

---

## File System KPI Mapping

### Specific KPIs Requested

| KPI | Supported? | Dynatrace Feature | Metric / Dimension | Notes |
|---|---|---|---|---|
| `filechangetime` | **Yes** | Custom EF2 Extension | `custom.file.change_age_seconds` (metric) | Seconds since `ctime` changed. On Linux = metadata change time; on Windows = creation time. Alertable via anomaly detection or Davis. |
| `filemode` | **Yes** | Custom EF2 Extension | `custom.file.mode` (metric) + `file_mode_octal` (dimension) | Reports numeric permission bits (e.g. `420` = `0o644`). Alert when mode drifts from expected value — ideal for detecting unauthorized chmod. |
| `fileowner` | **Yes** | `com.dynatrace.filesystem` Extension OR Custom EF2 | `file_owner` dimension | Surfaced as a string dimension on all file metrics when `extra_dimensions: true`. Filter and split dashboards by owner. |
| `filegroup` | **Yes** | `com.dynatrace.filesystem` Extension OR Custom EF2 | `file_group` dimension | Same as owner — string dimension when `extra_dimensions` is enabled. |
| `mountpoint` | **Yes** | Native OneAgent + Extensions | `dt.entity.disk` entity / `file_mountpoint` dimension | Native OneAgent discovers and monitors every mount point automatically. Extensions surface it as a dimension on file-level metrics. |

> **Note:** `fileowner` appears twice in the original scope — treated as one requirement above.

---

## Which Dynatrace Feature to Use

### Decision Guide

```
Do you need file-level metadata (owner, group, mode, ctime)?
│
├─ Yes, on a specific set of files/paths
│   └─► Custom EF2 Extension (this repo: custom:file-monitor)
│       • Full control over which files and what metadata to collect
│       • All 6 KPIs covered in a single extension
│       • Requires: Python 3.8+, OneAgent 1.239+, dt-cli for build/sign
│
├─ Yes, using a pattern/wildcard across directories
│   └─► com.dynatrace.filesystem (built-in, already deployed)
│       • Covers modification_time, count, and string dimensions (owner, group, mountpoint)
│       • Enable extra_dimensions: true in the monitoring config
│       • Does NOT natively expose filemode or ctime — needs custom EF2 for those
│
└─ I just need disk space / mount point availability
    └─► Native OneAgent (zero config required)
        • Monitors all mount points automatically
        • Reports free space, used space, inode usage, I/O
```

### Feature Comparison

| Capability | Native OneAgent | `com.dynatrace.filesystem` | Custom EF2 Extension |
|---|:---:|:---:|:---:|
| Mount point discovery | ✅ Auto | ✅ via dimension | ✅ via dimension |
| Disk free/used space | ✅ | — | — |
| File modification time | — | ✅ (`modification_time`) | ✅ (`custom.file.age_seconds`) |
| File metadata change time (ctime) | — | — | ✅ (`custom.file.change_age_seconds`) |
| File count by pattern | — | ✅ (`count`) | ✅ (`custom.file.line_count`) |
| File owner (string) | — | ✅ with `extra_dimensions` | ✅ |
| File group (string) | — | ✅ with `extra_dimensions` | ✅ |
| File mode / permissions | — | — | ✅ (`custom.file.mode`) |
| File size | — | — | ✅ (`custom.file.size_bytes`) |
| File existence (binary) | — | — | ✅ (`custom.file.exists`) |
| Alerting support | ✅ | ✅ | ✅ |
| Davis AI anomaly detection | ✅ | ✅ | ✅ |

---

## Current State (What's Already Deployed)

The `com.dynatrace.filesystem` extension (v2.1.0) is installed and active on the target host. The monitoring configuration has been updated to:

- Monitor `/var/log/*` and `/tmp/*`
- Run `modification_time` and `count` checks on both paths
- Enable `extra_dimensions: true` — this surfaces `file_owner`, `file_group`, and `file_mountpoint` as dimensions on every metric

**What this satisfies today (without further work):**

| KPI | Status |
|---|---|
| `filechangetime` | Partial — `modification_time` covers mtime; ctime requires custom EF2 |
| `filemode` | Not yet — requires custom EF2 extension |
| `fileowner` | ✅ Active via `extra_dimensions` |
| `filegroup` | ✅ Active via `extra_dimensions` |
| `mountpoint` | ✅ Active via `extra_dimensions` + Native OA |

---

## Recommended Next Steps

### Phase 1 — Complete with built-in extension (immediate, no dev work)
1. Expand the `com.dynatrace.filesystem` monitoring config with additional paths that matter to TIBCO (e.g. TIBCO log directories, config file locations)
2. Verify `extra_dimensions` data is flowing in Dynatrace Metrics Explorer — filter by `file_owner` and `file_group`
3. Create alerting rules for `modification_time` (stale files) and `count` (missing files)

### Phase 2 — Deploy custom EF2 extension (closes remaining gaps)
1. Build and sign the `custom:file-monitor` extension from this repo using `dt extension build`
2. Upload to the tenant and activate on the target host
3. Configure monitored paths with `count_lines: true` for text log files
4. This closes the `filemode` and `filechangetime` (ctime) gaps

### Phase 3 — Alerting and Davis integration
1. Define anomaly detection rules for each KPI threshold (see Excel thresholds)
2. Link alerts to the relevant TIBCO service entities in the topology
3. Configure notification integrations (ServiceNow, PagerDuty, email) to replace Omnibus alert routing

---

## Additional Coverage: SNMP, Process, Disk Space

The Excel shared covers four monitoring categories. Below is the Dynatrace coverage assessment for each based on common Omnibus probe KPIs. Once the full Excel is reviewed, this section will be updated with specific gap findings.

### SNMP Monitoring

| Common KPI | Dynatrace Coverage | Feature |
|---|---|---|
| `sysUpTime` | ✅ | Native host monitoring (uptime metric) |
| Interface operational status (`ifOperStatus`) | ✅ | Network monitoring / SNMP extension |
| Interface admin status (`ifAdminStatus`) | ✅ | SNMP extension |
| Interface errors / discards | ✅ | Network monitoring |
| Interface utilization (in/out bps) | ✅ | Network monitoring |
| Custom OIDs / vendor-specific MIBs | Partial | Requires SNMP generic extension or custom EF2 — **flag specific OIDs for review** |

**Potential gap:** Proprietary TIBCO MIBs or custom OIDs not in the standard SNMP extension will need a custom EF2 data source. Share the MIB list for assessment.

### Process Monitor

| Common KPI | Dynatrace Coverage | Feature |
|---|---|---|
| Process running / not running | ✅ | Native OneAgent — auto-discovered |
| Process CPU usage | ✅ | Native OneAgent |
| Process memory (RSS, VSZ) | ✅ | Native OneAgent |
| Process count (instances) | ✅ | Native OneAgent |
| Process restart / crash detection | ✅ | Davis AI problem detection |
| Specific process args / command line | ✅ | Process group rules in OneAgent config |
| Process availability SLO | ✅ | Dynatrace SLO with process entity |

**No gaps expected.** OneAgent's process monitoring is a strong 1:1 replacement for Omnibus process probes. Process group rules let you target TIBCO-specific process names and alert on count thresholds.

### Disk Space

| Common KPI | Dynatrace Coverage | Feature |
|---|---|---|
| Used space (bytes / %) | ✅ | Native OneAgent (`dt.host.disk.used.percent`) |
| Free space (bytes / %) | ✅ | Native OneAgent (`dt.host.disk.avail`) |
| Total capacity | ✅ | Native OneAgent |
| Inode usage | ✅ | Native OneAgent (`dt.host.disk.inodes.used.percent`) |
| Mount point availability | ✅ | Native OneAgent — per mount point entity |
| I/O throughput (read/write MB/s) | ✅ | Native OneAgent |
| I/O latency | ✅ | Native OneAgent |

**No gaps.** Native OneAgent covers all standard disk space KPIs with no additional configuration. Alerting thresholds from the Excel can be mapped directly to Dynatrace anomaly detection rules on `dt.host.disk.*` metrics.

### File System (from Excel tab)

| Common KPI | Dynatrace Coverage | Feature |
|---|---|---|
| File modification time | ✅ | `com.dynatrace.filesystem` |
| File count by pattern | ✅ | `com.dynatrace.filesystem` |
| File owner | ✅ | `com.dynatrace.filesystem` with `extra_dimensions` |
| File group | ✅ | `com.dynatrace.filesystem` with `extra_dimensions` |
| File mode / permissions | ✅ | Custom EF2 (`custom:file-monitor`) |
| File metadata change time | ✅ | Custom EF2 (`custom:file-monitor`) |
| File size | ✅ | Custom EF2 (`custom:file-monitor`) |
| File exists | ✅ | Custom EF2 (`custom:file-monitor`) |

---

## Threshold Mapping (Pending Excel Review)

Once the full Excel is shared and accessible, each threshold in Column C will be mapped to a Dynatrace alerting rule. The general pattern is:

| Omnibus Threshold Type | Dynatrace Equivalent |
|---|---|
| Static threshold (warn/critical) | Fixed threshold anomaly detection on metric |
| Baseline / seasonal | Davis AI automatic baseline — no manual threshold needed |
| Pattern match (file missing) | `count` check → alert on value = 0 |
| Age / staleness | `modification_time` check → alert on value > threshold |
| Binary state (up/down) | Davis problem card (process or host entity) |

---

## Questions / Items to Resolve

1. **Excel access** — please share the Excel file or paste Column C values per tab so specific threshold mapping can be completed.
2. **TIBCO process names** — provide the list of TIBCO process names to configure process group rules in OneAgent.
3. **Custom SNMP OIDs** — if any TIBCO components expose custom MIBs, share the OID list for assessment.
4. **Target paths** — confirm the exact file/directory paths TIBCO uses for logs, configs, and data files so the extension monitoring config can be finalized.
5. **Alert routing** — confirm the notification channel (ServiceNow ticket? PagerDuty? Email?) to replace Omnibus alert forwarding.

---

*This document will be updated as the Excel is reviewed and additional paths/thresholds are confirmed.*
