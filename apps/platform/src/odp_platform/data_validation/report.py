import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .registry import CheckResult, CheckSeverity
from .snapshot import DatasetSnapshot


@dataclass
class ValidationReport:
    run_id: str
    yaml_path: Path
    snapshot: DatasetSnapshot
    results: List[CheckResult]
    duration_seconds: float
    started_at_iso: str
    run_dir: Optional[Path] = None

    @property
    def overall_severity(self) -> str:
        max_rank = -1
        worst = CheckSeverity.PASS
        for r in self.results:
            rank = CheckSeverity.rank(r.severity)
            if rank > max_rank:
                max_rank = rank
                worst = r.severity
        return worst

    @property
    def counts_by_severity(self) -> Dict[str, int]:
        counts: Dict[str, int] = {
            CheckSeverity.ERROR: 0,
            CheckSeverity.WARNING: 0,
            CheckSeverity.INFO: 0,
            CheckSeverity.PASS: 0,
        }
        for r in self.results:
            counts[r.severity] = counts.get(r.severity, 0) + 1
        return counts

    @property
    def exit_code(self) -> int:
        sev = self.overall_severity
        if sev == CheckSeverity.ERROR:
            return 2
        if sev == CheckSeverity.WARNING:
            return 1
        return 0

    @property
    def failed_results(self) -> List[CheckResult]:
        return [r for r in self.results if not r.passed]

    @property
    def report_path(self) -> Optional[Path]:
        if self.run_dir is None:
            return None
        return self.run_dir / "report.json"

    def to_dict(self) -> Dict[str, Any]:
        def _serialize(obj: Any) -> Any:
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, (datetime,)):
                return obj.isoformat()
            if isinstance(obj, (tuple, list)):
                return [_serialize(x) for x in obj]
            if isinstance(obj, dict):
                return {str(k): _serialize(v) for k, v in obj.items()}
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            return obj

        return {
            "run_id": self.run_id,
            "yaml_path": str(self.yaml_path),
            "started_at_iso": self.started_at_iso,
            "duration_seconds": self.duration_seconds,
            "overall_severity": self.overall_severity,
            "exit_code": self.exit_code,
            "counts_by_severity": self.counts_by_severity,
            "results": [
                {
                    "name": r.name,
                    "severity": r.severity,
                    "summary": r.summary,
                    "details": _serialize(r.details),
                }
                for r in self.results
            ],
            "snapshot": {
                "yaml_path": str(self.snapshot.yaml_path),
                "nc": self.snapshot.nc,
                "class_names": list(self.snapshot.class_names),
                "task_type": self.snapshot.task_type,
                "total_images": self.snapshot.total_images,
                "splits": list(self.snapshot.splits),
                "scan_warnings": list(self.snapshot.scan_warnings),
                "yaml_load_error": self.snapshot.yaml_load_error,
                "stats_per_split": {
                    s: {
                        "image_count": st.image_count,
                        "annotated_count": st.annotated_count,
                        "total_instances": st.total_instances,
                    }
                    for s, st in self.snapshot.stats_per_split.items()
                },
            },
        }
